import networkx as nx
import json
import os
from ollama import chat

KG_FILE = "knowledge_graph.json"

class KnowledgeGraph:
    def __init__(self):
        self.graph = nx.DiGraph()
        self.load()

    def load(self):
        if os.path.exists(KG_FILE):
            try:
                with open(KG_FILE, 'r') as f:
                    data = json.load(f)
                    self.graph = nx.node_link_graph(data)
            except Exception as e:
                print(f"Error loading KG: {e}")
                self.graph = nx.DiGraph()

    def save(self):
        data = nx.node_link_data(self.graph)
        with open(KG_FILE, 'w') as f:
            json.dump(data, f)

    def add_relationship(self, source, relation, target):
        source = source.strip().lower()
        target = target.strip().lower()
        relation = relation.strip().lower()
        if source and target and relation:
            self.graph.add_node(source)
            self.graph.add_node(target)
            self.graph.add_edge(source, target, label=relation)

    def extract_from_text(self, text, llm_model_name):
        """Uses LLM to extract entity relationships from a chunk of text."""
        prompt = f"""
        Extract relationships from the following text in the exact format: 
        SourceEntity | Relationship | TargetEntity
        Do not output anything else. If there are no relationships, output nothing.
        
        Text:
        {text}
        """
        try:
            response = chat(
                model=llm_model_name,
                messages=[{"role": "user", "content": prompt}]
            )
            content = response.message.content.strip()
            
            added = False
            for line in content.split('\n'):
                parts = [p.strip() for p in line.split('|')]
                if len(parts) == 3:
                    self.add_relationship(parts[0], parts[1], parts[2])
                    added = True
            
            if added:
                self.save()
        except Exception as e:
            print(f"KG Extraction Error: {e}")

    def get_context_for_entities(self, query_text, llm_model_name):
        """Given a query, find relevant nodes and return their 1-hop relationships."""
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
            entities = [e.strip().lower() for e in response.message.content.split(',')]
            
            context_lines = []
            for entity in entities:
                if entity in self.graph:
                    # outgoing edges
                    for neighbor in self.graph.successors(entity):
                        edge_data = self.graph.get_edge_data(entity, neighbor)
                        label = edge_data.get('label', 'related to')
                        context_lines.append(f"KG FACT: [{entity}] --({label})--> [{neighbor}]")
                    # incoming edges
                    for neighbor in self.graph.predecessors(entity):
                        edge_data = self.graph.get_edge_data(neighbor, entity)
                        label = edge_data.get('label', 'related to')
                        context_lines.append(f"KG FACT: [{neighbor}] --({label})--> [{entity}]")
                        
            return list(set(context_lines))
        except Exception as e:
            print(f"KG Retrieval Error: {e}")
            return []
