import networkx as nx
import sqlite3
import re
from tqdm import tqdm
import threading
import json
from collections import defaultdict
from ollama import chat

import config
from logger import get_logger
logger = get_logger()

KG_DB_FILE = config.KG_DB_PATH

# Load and compile patterns dynamically
PATTERNS = {}
try:
    with open(config.ENTITIES_CONFIG_PATH, "r") as f:
        _raw_patterns = json.load(f)
        for k, v in _raw_patterns.items():
            PATTERNS[k] = re.compile(v, re.I)
except Exception as e:
    print(f"Failed to load entities.json: {e}")

# Fix #6: Module-level cache dict replaces @lru_cache on instance method.
_entity_cache: dict = {}
_entity_cache_lock = threading.Lock()

from resource_manager import ResourceManager

# --- REBEL PIPELINE INTEGRATION ---
_rebel_model = None
_rebel_tokenizer = None

def get_rebel():
    global _rebel_model, _rebel_tokenizer
    if _rebel_model is None:
        from transformers import AutoModelForSeq2SeqLM, AutoTokenizer
        import torch
        logger.info("\nLoading REBEL model for Knowledge Graph extraction (this may take a moment)...")
        device = ResourceManager.get_device()
        quantize = ResourceManager.should_quantize_8bit()
        
        _rebel_tokenizer = AutoTokenizer.from_pretrained(config.KG_MODEL_NAME)
        
        if quantize:
            logger.info(f"[SYSTEM] Loading REBEL in 8-bit mode to save VRAM...")
            from transformers import BitsAndBytesConfig
            quantization_config = BitsAndBytesConfig(load_in_8bit=True)
            _rebel_model = AutoModelForSeq2SeqLM.from_pretrained(
                config.KG_MODEL_NAME, 
                quantization_config=quantization_config,
                device_map="auto"
            )
        else:
            _rebel_model = AutoModelForSeq2SeqLM.from_pretrained(config.KG_MODEL_NAME)
            if device != "cpu":
                _rebel_model = _rebel_model.to(device)
                
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
        self.conn.execute("PRAGMA journal_mode=WAL;")
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS edges (
                source TEXT, relation TEXT, target TEXT, department TEXT, source_file TEXT,
                PRIMARY KEY (source, relation, target)
            )
        """)
        
        # Schema migration: add source_file if it doesn't exist (for existing DBs)
        try:
            self.conn.execute("ALTER TABLE edges ADD COLUMN source_file TEXT")
        except sqlite3.OperationalError:
            pass # Column already exists
            
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_source ON edges(source)")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_target ON edges(target)")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_source_file ON edges(source_file)")
        self.conn.commit()

    def admin_delete_file(self, file_path):
        """Delete all KG edges that were extracted from the given file_path."""
        with self._write_lock:
            self.conn.execute("DELETE FROM edges WHERE source_file = ?", (file_path,))
            self.conn.commit()
            self.load() # Rebuild in-memory graph
        self.invalidate_cache()

    def load(self):
        self.graph = nx.DiGraph()
        self.token_index.clear()
        for row in self.conn.execute("SELECT source, relation, target, department FROM edges"):
            source, relation, target, department = row
            self.graph.add_edge(source, target, label=relation, dept=department)
            self._index_node(source)
            self._index_node(target)

    def prune_duplicates(self, similarity_threshold=0.98):
        """
        Phase 4: Calculates cosine similarity between all node names using fast embeddings.
        If two nodes cross the similarity_threshold, merge their edges into a single canonical node.
        """
        print("[KG] Starting automated Knowledge Graph pruning...")
        
        with self._write_lock:
            nodes_cursor = self.conn.execute("SELECT DISTINCT source FROM edges UNION SELECT DISTINCT target FROM edges")
            all_nodes = [row[0] for row in nodes_cursor.fetchall()]
        
        if not all_nodes:
            print("[KG] Pruning complete: 0 nodes found.")
            return

        try:
            from sentence_transformers import SentenceTransformer
            from sentence_transformers.util import cos_sim
        except ImportError:
            print("[KG] Cannot prune: sentence_transformers missing.")
            return
            
        print(f"[KG] Embedding {len(all_nodes)} nodes for similarity matching...")
        # Using a fast, lightweight embedding model specifically for deduplication
        model = SentenceTransformer('all-MiniLM-L6-v2', device=ResourceManager.get_device())
        
        embeddings = model.encode(all_nodes, convert_to_tensor=True)
        similarity_matrix = cos_sim(embeddings, embeddings)
        
        merges = []
        visited = set()
        
        for i in range(len(all_nodes)):
            if i in visited:
                continue
            for j in range(i + 1, len(all_nodes)):
                if j in visited:
                    continue
                if similarity_matrix[i][j] >= similarity_threshold:
                    if len(all_nodes[i]) >= len(all_nodes[j]):
                        canonical, duplicate = all_nodes[i], all_nodes[j]
                    else:
                        canonical, duplicate = all_nodes[j], all_nodes[i]
                        
                    merges.append((canonical, duplicate))
                    visited.add(j)
                    
        if merges:
            print(f"[KG] Found {len(merges)} duplicate pairs. Executing healing SQL...")
            with self._write_lock:
                for canonical, duplicate in merges:
                    self.conn.execute("UPDATE edges SET target = ? WHERE target = ?", (canonical, duplicate))
                    self.conn.execute("UPDATE edges SET source = ? WHERE source = ?", (canonical, duplicate))
                self.conn.commit()
                self.load() # Rebuild in-memory nx graph
            print(f"[KG] Successfully pruned and merged {len(merges)} nodes.")
        else:
            print("[KG] Pruning complete: No duplicates found.")

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
        with _entity_cache_lock:
            _entity_cache.clear()

    def get_cache_size(self):
        with _entity_cache_lock:
            return len(_entity_cache)

    def add_relationship(self, source, relation, target, department="global", source_file=None):
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
                    "INSERT OR IGNORE INTO edges VALUES (?,?,?,?,?)",
                    (source, relation, target, department, source_file)
                )
                self.graph.add_edge(source, target, label=relation, dept=department)
                self._index_node(source)
                self._index_node(target)
            return f"{source} | {relation} | {target}"
        return None

    def extract_from_texts(self, texts, department_name="global", source_files=None):
        if not texts:
            return []
            
        extracted_facts = []
        
        device = ResourceManager.get_device()
        vram_gb = 0
        if device == "cuda":
            try:
                import torch
                vram_gb = torch.cuda.get_device_properties(0).total_memory / (1024**3)
            except Exception:
                pass
                
        # Only use slow LLM extraction if ADAPTIVE is True AND we have massive VRAM (>20GB)
        # Or if we are on a Mac (mps) because REBEL is extremely slow on Apple Silicon
        if config.ADAPTIVE_KG_EXTRACTION and (vram_gb >= 20 or device == "mps"):
            print("[BACKGROUND TASK] Using LLM (llama3) for High-Quality KG Extraction...")
            extracted_facts = self._extract_with_llm(texts, department_name, source_files)
        else:
            print(f"[BACKGROUND TASK] Detected {vram_gb:.1f}GB VRAM. Using REBEL for Fast KG Extraction...")
            extracted_facts = self._extract_with_rebel(texts, department_name, source_files)
            
        with self._write_lock:
            self.conn.commit()
            
        return extracted_facts
        
    def _extract_with_llm(self, texts, department_name="global", source_files=None):
        extracted_facts = []
        for i, text in enumerate(tqdm(texts, desc="Extracting KG Facts (LLM)")):
            src_file = source_files[i] if source_files else None
            prompt = f"""
            Extract knowledge graph triples from the following text.
            Format exactly as:
            source_entity | relationship | target_entity
            
            Text: {text}
            """
            try:
                response = chat(
                    model=config.LLM_MODEL_NAME,
                    messages=[{"role": "user", "content": prompt}],
                    options={"temperature": 0.0}
                )
                for line in response.message.content.split('\n'):
                    parts = [p.strip() for p in line.split('|')]
                    if len(parts) == 3:
                        fact = self.add_relationship(parts[0], parts[1], parts[2], department_name, src_file)
                        if fact: extracted_facts.append({"fact": fact, "source_file": src_file})
            except Exception as e:
                print(f"KG Extraction Error (LLM): {e}")
        return extracted_facts

    def _extract_with_rebel(self, texts, department_name="global", source_files=None):
        extracted_facts = []
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
            for i, decoded_text in enumerate(tqdm(decoded_texts, desc="Parsing REBEL Triples", leave=False)):
                src_file = source_files[i] if source_files else None
                relations = parse_rebel_output(decoded_text)
                for rel in relations:
                    fact = self.add_relationship(rel['head'], rel['type'], rel['tail'], department_name, src_file)
                    if fact: extracted_facts.append({"fact": fact, "source_file": src_file})
        except Exception as e:
            # Raise the exception so the master agent knows to abort the loop
            raise RuntimeError(f"REBEL extraction failed: {e}") from e
            
        return extracted_facts

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
            content = response.message.content
            # Regex fallback to clean conversational clutter
            if ":" in content and "," in content:
                content = content.split(":")[-1]
            
            # Remove brackets or quotes if present
            content = content.replace("[", "").replace("]", "").replace('"', "").replace("'", "")
            entities = tuple(e.strip().lower() for e in content.split(',') if len(e.strip()) > 1)
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
