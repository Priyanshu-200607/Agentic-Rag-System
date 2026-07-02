import networkx as nx
import sqlite3
import re
import threading
from collections import defaultdict
from ollama import chat

KG_DB_FILE = "knowledge_graph.db"

# Fix #6: Module-level cache dict replaces @lru_cache on instance method.
# lru_cache on 'self' prevents garbage collection (memory leak).
# A module-level dict holds results keyed by (query_text, model) with no reference to self.
_entity_cache: dict = {}
_entity_cache_lock = threading.Lock()

PATTERNS = {
    "employee": re.compile(r"employee[\s_:]?(?:id[\s_:]?)?(\d+)", re.I),
    "user":     re.compile(r"user[\s_:](\d+)", re.I),
    "policy":   re.compile(r"(?:hr[\s_])?policy[\s_:](\d+)", re.I),
    "quarter":  re.compile(r"q([1-4])(?:\s+quarter)?", re.I),
}

# --- REBEL PIPELINE INTEGRATION ---
_rebel_model = None
_rebel_tokenizer = None

def get_rebel():
    global _rebel_model, _rebel_tokenizer
    if _rebel_model is None:
        from transformers import AutoModelForSeq2SeqLM, AutoTokenizer
        import torch
        print("\nLoading REBEL model for Knowledge Graph extraction (this may take a moment)...")
        device = "cuda" if torch.cuda.is_available() else "cpu"
        _rebel_tokenizer = AutoTokenizer.from_pretrained("Babelscape/rebel-large")
        _rebel_model = AutoModelForSeq2SeqLM.from_pretrained("Babelscape/rebel-large").to(device)
    return _rebel_tokenizer, _rebel_model

def parse_rebel_output(text):
    relations = []
    relation, subject, object_ = '', '', ''
    text = text.strip()
    current = 'x'
    text_replaced = text.replace("<s>", "").replace("<pad>", "").replace("</s>", "")
    for token in text_replaced.split():
        if token == "<triplet>":
            current = 't'
            if relation != '':
                relations.append({'head': subject.strip(), 'type': relation.strip(), 'tail': object_.strip()})
                relation = ''
            subject = ''
        elif token == "<subj>":
            current = 's'
            if relation != '':
                relations.append({'head': subject.strip(), 'type': relation.strip(), 'tail': object_.strip()})
            object_ = ''
        elif token == "<obj>":
            current = 'o'
            relation = ''
        else:
            if current == 't':
                subject += ' ' + token
            elif current == 's':
                object_ += ' ' + token
            elif current == 'o':
                relation += ' ' + token
    if subject != '' and relation != '' and object_ != '':
        relations.append({'head': subject.strip(), 'type': relation.strip(), 'tail': object_.strip()})
    return relations

def unload_rebel():
    global _rebel_model, _rebel_tokenizer
    if _rebel_model is not None:
        del _rebel_model
        del _rebel_tokenizer
        _rebel_model = None
        _rebel_tokenizer = None
        import torch
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            print("[BACKGROUND TASK] PyTorch VRAM cache cleared.")
# ----------------------------------

class KnowledgeGraph:
    def __init__(self):
        self.graph = nx.DiGraph()
        self.token_index = defaultdict(set)
        # Fix #2: Lock for thread-safe concurrent writes to the graph
        self._write_lock = threading.Lock()
        self._init_db()
        self.load()

    def _init_db(self):
        self.conn = sqlite3.connect(KG_DB_FILE, check_same_thread=False)
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS edges (
                source TEXT, relation TEXT, target TEXT, department TEXT,
                PRIMARY KEY (source, relation, target)
            )
        """)
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_source ON edges(source)")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_target ON edges(target)")
        self.conn.commit()

    def load(self):
        self.graph = nx.DiGraph()
        self.token_index.clear()
        for row in self.conn.execute("SELECT source, relation, target, department FROM edges"):
            source, relation, target, department = row
            self.graph.add_edge(source, target, label=relation, dept=department)
            self._index_node(source)
            self._index_node(target)

    def canonicalize(self, raw: str) -> str:
        raw = raw.strip().lower()
        for entity_type, pattern in PATTERNS.items():
            m = pattern.search(raw)
            if m:
                return f"{entity_type}:{m.group(1)}"
        return raw

    def _index_node(self, node_id: str):
        for token in node_id.split():
            self.token_index[token].add(node_id)

    def fuzzy_find_nodes(self, query_token: str) -> set:
        matches = set()
        for token, nodes in self.token_index.items():
            if query_token in token or token in query_token:
                matches |= nodes
        return matches

    def invalidate_cache(self):
        """Fix #6: Clear the module-level entity cache after new data is ingested."""
        global _entity_cache
        with _entity_cache_lock:
            _entity_cache.clear()

    def add_relationship(self, source, relation, target, department="global"):
        source = self.canonicalize(source)
        target = self.canonicalize(target)
        relation = relation.strip().lower()

        if len(source) < 3 or len(target) < 3:
            return
        if source in ("sourceentity", "targetentity", "relationship"):
            return

        if source and target and relation:
            # Fix #2: Acquire write lock before touching the graph or DB
            with self._write_lock:
                self.conn.execute(
                    "INSERT OR IGNORE INTO edges VALUES (?,?,?,?)",
                    (source, relation, target, department)
                )
                self.conn.commit()
                self.graph.add_edge(source, target, label=relation, dept=department)
                self._index_node(source)
                self._index_node(target)

    def extract_from_texts(self, texts, department_name="global"):
        if not texts:
            return
        try:
            tokenizer, model = get_rebel()
            # Tokenize batch of input texts (truncating at 512 max length)
            inputs = tokenizer(texts, max_length=512, padding=True, truncation=True, return_tensors="pt")
            device = next(model.parameters()).device
            inputs = {k: v.to(device) for k, v in inputs.items()}
            
            # Generate raw triplet strings in parallel
            gen_kwargs = {
                "max_length": 256,
                "length_penalty": 0,
                "num_beams": 1,  # Switched to Greedy Search: 3x less VRAM and 3x faster
                "num_return_sequences": 1,
            }
            generated_tokens = model.generate(
                **inputs,
                **gen_kwargs,
            )
            
            # Decode batch keeping special tokens needed for parsing
            decoded_texts = tokenizer.batch_decode(generated_tokens, skip_special_tokens=False)
            
            # Parse the text into clean dictionaries and store
            for decoded_text in decoded_texts:
                relations = parse_rebel_output(decoded_text)
                for rel in relations:
                    self.add_relationship(rel['head'], rel['type'], rel['tail'], department_name)
        except Exception as e:
            print(f"KG Extraction Error (REBEL Batch): {e}")

    def _extract_entities_cached(self, query_text: str, llm_model_name: str) -> tuple:
        """Fix #6: Module-level dict cache — no reference to self, no memory leak."""
        cache_key = (query_text, llm_model_name)
        with _entity_cache_lock:
            if cache_key in _entity_cache:
                return _entity_cache[cache_key]

        prompt = f"""
        Extract the key entities (people, places, concepts, departments) from this query.
        Return them as a comma-separated list. Do not output anything else.
        Query: {query_text}
        """
        try:
            response = chat(
                model=llm_model_name,
                messages=[{"role": "user", "content": prompt}]
            )
            entities = tuple(e.strip().lower() for e in response.message.content.split(','))
        except Exception as e:
            print(f"KG Retrieval Error: {e}")
            entities = tuple()

        with _entity_cache_lock:
            # Cap cache size at 256 entries to prevent unbounded growth
            if len(_entity_cache) >= 256:
                # Evict oldest entry (first key in dict — Python 3.7+ preserves insertion order)
                oldest = next(iter(_entity_cache))
                del _entity_cache[oldest]
            _entity_cache[cache_key] = entities

        return entities

    def get_context_for_entities(self, query_text, llm_model_name, department_name="global", max_hops=2, max_facts=30):
        # Fix #4: Truncate query to 2000 chars to stay within LLM context window
        query_text = query_text[:2000]
        raw_entities = self._extract_entities_cached(query_text, llm_model_name)

        resolved_entities = set()
        for raw in raw_entities:
            canonical = self.canonicalize(raw)
            if canonical in self.graph.nodes:
                resolved_entities.add(canonical)
            else:
                for token in canonical.split():
                    if len(token) > 3:
                        fuzzy_matches = self.fuzzy_find_nodes(token)
                        if len(fuzzy_matches) <= 10:
                            resolved_entities |= fuzzy_matches

        visited_edges = set()
        frontier = resolved_entities & set(self.graph.nodes)
        facts = []

        for hop in range(max_hops):
            next_frontier = set()
            for node in frontier:
                for neighbor in self.graph.successors(node):
                    edge_data = self.graph.get_edge_data(node, neighbor)
                    edge_dept = edge_data.get('dept', 'global')
                    if department_name == "global" or edge_dept in (department_name, "global"):
                        edge_key = (node, neighbor)
                        if edge_key not in visited_edges:
                            visited_edges.add(edge_key)
                            label = edge_data.get('label', 'related to')
                            facts.append(f"KG FACT: [{node}] --({label})--> [{neighbor}]")
                            next_frontier.add(neighbor)

                for neighbor in self.graph.predecessors(node):
                    edge_data = self.graph.get_edge_data(neighbor, node)
                    edge_dept = edge_data.get('dept', 'global')
                    if department_name == "global" or edge_dept in (department_name, "global"):
                        edge_key = (neighbor, node)
                        if edge_key not in visited_edges:
                            visited_edges.add(edge_key)
                            label = edge_data.get('label', 'related to')
                            facts.append(f"KG FACT: [{neighbor}] --({label})--> [{node}]")
                            next_frontier.add(neighbor)

            frontier = next_frontier
            if not frontier:
                break

        return facts[:max_facts]
