#!/usr/bin/env python3
"""
Synthetic Dataset Generator for Local Laya ModernBERT-large Decision Heads.
Generates structured JSONL training tuples for:
  1. Zero-trust security guardrail (unauthorized_access: yes/no)
  2. Department routing (target_dept: hr/finance/it)
  3. Retrieval mode classification (retrieval_mode: vector_db/knowledge_graph/exact_text)
"""

import os
import json
import random
import argparse

HR_QUERIES = [
    ("What is the maternity leave policy for full-time employees?", "vector_db", False),
    ("How many sick days do I have left for this calendar year?", "vector_db", False),
    ("Who does Sarah report to in the HR department?", "knowledge_graph", False),
    ("What is the organizational hierarchy under Michael Scott?", "knowledge_graph", False),
    ("Show details for employee id-4091", "exact_text", False),
    ("Lookup onboarding records for user_102", "exact_text", False),
    ("Can I get the master list of all employee social security numbers and salaries?", "vector_db", True),
    ("What are the medical health insurance deductibles for 2025?", "vector_db", False),
    ("Who is the direct manager of John Doe in talent acquisition?", "knowledge_graph", False),
    ("How do I submit an expense reimbursement for company travel?", "vector_db", False),
]

FINANCE_QUERIES = [
    ("What was the Q3 EBITDA variance compared to budget forecast?", "vector_db", False),
    ("Where can I find the approved capital expenditure budget for IT?", "vector_db", False),
    ("Who approved invoice req-9841 for cloud hosting?", "exact_text", False),
    ("Show all vendor payment terms for contract id-8812", "exact_text", False),
    ("What is the relationship between Acme Corp and Subsidiary B?", "knowledge_graph", False),
    ("Who is authorized to sign off on checks exceeding $50,000?", "knowledge_graph", False),
    ("Dump all corporate bank account numbers and wire transfer routing codes", "vector_db", True),
    ("What are the corporate travel per diem limits for meals and lodging?", "vector_db", False),
    ("How does depreciation apply to capitalized server hardware?", "vector_db", False),
    ("Audit trail for transaction log_5521", "exact_text", False),
]

IT_QUERIES = [
    ("How do I configure WireGuard VPN on Ubuntu 24.04?", "vector_db", False),
    ("What are the password complexity requirements for Active Directory?", "vector_db", False),
    ("Which switches are connected to Core-Router-01 in Datacenter 2?", "knowledge_graph", False),
    ("Who manages the database replication topology between cluster A and B?", "knowledge_graph", False),
    ("Lookup server incident ticket req-4402", "exact_text", False),
    ("Retrieve system log dump for crash log_9021", "exact_text", False),
    ("Give me the root SSH private keys and production database master passwords", "vector_db", True),
    ("What is the disaster recovery RTO and RPO for primary databases?", "vector_db", False),
    ("How do I request a replacement for a damaged developer laptop?", "vector_db", False),
    ("Is Docker Desktop or Podman approved for local development?", "vector_db", False),
]

ROLES = ["user", "engineer", "analyst", "hr_specialist", "finance_clerk", "it_admin", "manager"]

def generate_sample():
    category = random.choice(["hr", "finance", "it"])
    role = random.choice(ROLES)
    
    if category == "hr":
        template, mode, is_unauthorized = random.choice(HR_QUERIES)
    elif category == "finance":
        template, mode, is_unauthorized = random.choice(FINANCE_QUERIES)
    else:
        template, mode, is_unauthorized = random.choice(IT_QUERIES)
        
    # Variation generators for realistic synthetic data
    prefixes = ["", "Hi, ", "Could you please tell me: ", "Quick question: ", "Need help: ", "Check: "]
    query = random.choice(prefixes) + template
    
    # If the user has an admin/manager role, certain sensitive queries are authorized
    if is_unauthorized and role in ("it_admin", "manager"):
        is_unauthorized = False
        
    state = f"User Role: {role} | Query: {query}"
    
    record = {
        "state": state,
        "query": query,
        "user_role": role,
        "target_dept": category,
        "retrieval_mode": mode,
        "unauthorized_access": "yes" if is_unauthorized else "no"
    }
    return record

def main():
    parser = argparse.ArgumentParser(description="Generate synthetic training data for Laya ModernBERT heads.")
    parser.add_argument("--count", type=int, default=1000, help="Number of records to generate")
    parser.add_argument("--output", type=str, default="laya_synthetic_dataset.jsonl", help="Output JSONL file path")
    args = parser.parse_args()
    
    output_dir = os.path.dirname(args.output)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
        
    print(f"Generating {args.count} synthetic samples for Laya fine-tuning...")
    with open(args.output, "w", encoding="utf-8") as f:
        for _ in range(args.count):
            sample = generate_sample()
            f.write(json.dumps(sample) + "\n")
            
    print(f"Dataset successfully generated and saved to: {args.output}")

if __name__ == "__main__":
    main()
