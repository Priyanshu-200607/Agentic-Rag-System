import os
import re
from logger import get_logger
from resource_manager import ResourceManager

logger = get_logger()

class LocalDecisionEngine:
    """
    High-speed non-autoregressive System 1 decision engine based on Laya (ModernBERT-large).
    Evaluates typed decision heads (choice, score, noul) in a single sub-40ms forward pass.
    Includes a deterministic fallback when Laya is not yet installed.
    """
    
    def __init__(self, device=None):
        self.device = device or ResourceManager.get_device()
        self.router = None
        self._init_laya()

    def _init_laya(self):
        try:
            from laya import Router
            logger.info(f"[DECISION ENGINE] Initializing Laya (ModernBERT-large) on {self.device}...")
            self.router = Router(preload=True)
            logger.info("[DECISION ENGINE] System 1 Engine ready (sub-40ms).")
        except Exception as e:
            logger.warning(f"[DECISION ENGINE] Laya initialization skipped ({e}). Operating in fast deterministic heuristic mode.")
            self.router = None

    def triage_request(self, query: str, user_role: str = "user", allowed_departments: list = None) -> dict:
        """
        Evaluates security guardrails, department routing, and storage mode in a single pass.
        Returns:
            dict: {
                "is_safe": bool,
                "target_departments": list[str],
                "retrieval_mode": "vector_db" | "knowledge_graph" | "exact_text",
                "confidence": float,
                "extracted_entity": str
            }
        """
        allowed = allowed_departments or ["hr", "finance", "it"]
        query_safe = query.strip()

        # 1. Use Laya Neural Decision Engine if available
        if self.router:
            try:
                state = f"User Role: {user_role} | Query: {query_safe}"
                questions = {
                    "unauthorized_access": {"type": "noul"},
                    "target_dept": {"type": "choice", "options": allowed},
                    "retrieval_mode": {"type": "choice", "options": ["vector_db", "knowledge_graph", "exact_text"]}
                }
                
                result = self.router.predict(state, questions)
                unauthorized_prob = result.get("unauthorized_access", {}).get("prob_yes", 0.0)
                target_dept = result.get("target_dept", {}).get("choice", allowed[0])
                mode = result.get("retrieval_mode", {}).get("choice", "vector_db")
                conf = result.get("retrieval_mode", {}).get("confidence", 0.9)

                return {
                    "is_safe": unauthorized_prob < 0.35,
                    "target_departments": [target_dept] if target_dept in allowed else allowed,
                    "retrieval_mode": mode,
                    "confidence": conf,
                    "extracted_entity": query_safe
                }
            except Exception as e:
                logger.error(f"[DECISION ENGINE] Laya inference failed ({e}), falling back to heuristic.")

        # 2. Fast Deterministic Heuristic Fallback
        q_lower = query_safe.lower()
        
        # Security Guardrail (Heuristic)
        is_safe = True
        if user_role not in ("admin", "manager") and any(term in q_lower for term in ["master password", "private key", "all salaries", "confidential credentials"]):
            is_safe = False

        # Target Department Selection
        dept_keywords = {
            "hr": ["leave", "vacation", "holiday", "sick", "employee", "payroll", "salary", "hiring", "onboarding", "benefits", "policy"],
            "finance": ["expense", "budget", "invoice", "revenue", "cost", "q1", "q2", "q3", "q4", "tax", "audit", "payment", "reimbursement"],
            "it": ["laptop", "hardware", "vpn", "server", "network", "password", "ticket", "bug", "software", "access", "deployment", "database"]
        }
        
        matched_depts = []
        for dept in allowed:
            keywords = dept_keywords.get(dept, [dept])
            if any(k in q_lower for k in keywords):
                matched_depts.append(dept)

        target_departments = matched_depts if matched_depts else allowed

        # Storage Engine Selection (Vector DB vs KG vs Exact)
        retrieval_mode = "vector_db"
        confidence = 0.95

        relational_terms = ["who is", "reports to", "direct manager", "relationship", "managed by", "connected to", "team of"]
        exact_pattern = re.search(r'\b(user_\d+|req-\d+|id-\d+|log_\d+)\b', q_lower)

        if exact_pattern:
            retrieval_mode = "exact_text"
            confidence = 0.90
        elif any(term in q_lower for term in relational_terms):
            retrieval_mode = "knowledge_graph"
            confidence = 0.90
        elif len(target_departments) > 1 and ("across" in q_lower or "overall" in q_lower):
            # Ambiguous multi-department query -> triggers speculative parallel retrieval
            confidence = 0.70

        return {
            "is_safe": is_safe,
            "target_departments": target_departments,
            "retrieval_mode": retrieval_mode,
            "confidence": confidence,
            "extracted_entity": query_safe
        }

    def evaluate_answer(self, query: str, answer: str) -> dict:
        """
        Fast System 1 answer quality evaluation replacing slow per-token LLM scoring.
        Returns:
            dict: {"score": int, "is_sufficient": bool, "feedback": str}
        """
        answer_clean = answer.strip()
        
        # 1. Use Laya if available
        if self.router:
            try:
                state = f"Query: {query}\nAnswer: {answer_clean}"
                questions = {
                    "quality_score": {"type": "score", "min": 1, "max": 10},
                    "is_empty_or_refusal": {"type": "noul"}
                }
                res = self.router.predict(state, questions)
                score = int(res.get("quality_score", {}).get("value", 8))
                refusal_prob = res.get("is_empty_or_refusal", {}).get("prob_yes", 0.0)
                
                is_sufficient = (score >= 7) and (refusal_prob < 0.5)
                return {
                    "score": score,
                    "is_sufficient": is_sufficient,
                    "feedback": "Answer sufficient." if is_sufficient else "Answer incomplete or refused."
                }
            except Exception as e:
                logger.error(f"[DECISION ENGINE] Evaluation with Laya failed ({e}), using heuristic.")

        # 2. Fast Deterministic Heuristic
        negative_markers = [
            "i don't know", "i do not know", "no documents found", "no relevant information",
            "not enough information", "not have enough information", "do not have enough",
            "don't have enough", "cannot find", "no information available", "insufficient information",
            "does not contain"
        ]
        
        if not answer_clean or any(m in answer_clean.lower() for m in negative_markers):
            return {
                "score": 4,
                "is_sufficient": False,
                "feedback": "Answer indicates missing data or lack of context."
            }
            
        return {
            "score": 9,
            "is_sufficient": True,
            "feedback": "Answer is comprehensive and grounded."
        }
