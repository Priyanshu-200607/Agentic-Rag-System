import os
from sentence_transformers import SentenceTransformer
from ollama import chat
from pypdf import PdfReader
from docx import Document
import chromadb

class MultiDeptRAG:
    def __init__(self, db_path="./chroma_db_multi", embed_model_name="BAAI/bge-small-en-v1.5", llm_model_name="gemma2:2b"):
        print("Loading embedding model...")
        self.embed_model = SentenceTransformer(embed_model_name)
        self.client = chromadb.PersistentClient(path=db_path)
        self.llm_model_name = llm_model_name
        print("System initialized.")

    def _process_file(self, path):
        ext = os.path.splitext(path)[1].lower()
        if ext == ".txt":
            with open(path, "r", encoding="utf-8") as f:
                return f.read()
        elif ext == ".pdf":
            reader = PdfReader(path)
            return "\n".join(page.extract_text() or "" for page in reader.pages)
        elif ext == ".docx":
            doc = Document(path)
            return "\n".join(para.text for para in doc.paragraphs)
        else:
            print(f"Unsupported file: {path}")
            return ""

    def admin_upload_to_department(self, department_name, file_paths, chunk_size=500, overlap=100):
        safe_name = f"dept_{department_name}" if len(department_name) < 3 else department_name
        collection = self.client.get_or_create_collection(name=safe_name)
        
        documents = []
        metadatas = []
        step = chunk_size - overlap
        
        for path in file_paths:
            path = path.strip()
            text = self._process_file(path)
            if not text:
                continue
            for i in range(0, len(text), step):
                chunk = text[i:i + chunk_size]
                if chunk.strip():
                    documents.append(chunk)
                    metadatas.append({"source": path, "department": department_name})
                    
        if not documents:
            return
        embeddings = self.embed_model.encode(documents, show_progress_bar=True).tolist()
        existing_count = collection.count()
        ids = [str(existing_count + i) for i in range(len(documents))]
        
        collection.add(
            ids=ids,
            documents=documents,
            embeddings=embeddings,
            metadatas=metadatas
        )

    def admin_delete_file(self, department_name, file_path):
        safe_name = f"dept_{department_name}" if len(department_name) < 3 else department_name
        try:
            collection = self.client.get_collection(name=safe_name)
            collection.delete(where={"source": file_path})
            print(f"Deleted chunks for {file_path} from department '{department_name}'")
        except Exception:
            print(f"Collection {safe_name} does not exist.")

    def query(self, query, target_departments, n_results=3, distance_threshold=1.2):
        query_embedding = self.embed_model.encode(query).tolist()
        all_retrieved = []
        for dept in target_departments:
            safe_name = f"dept_{dept}" if len(dept) < 3 else dept
            try:
                collection = self.client.get_collection(name=safe_name)
                results = collection.query(
                    query_embeddings=[query_embedding],
                    n_results=n_results,
                    include=["documents", "distances"]
                )
                if results["documents"] and len(results["documents"]) > 0:
                    docs = results["documents"][0]
                    distances = results["distances"][0]
                    for doc, dist in zip(docs, distances):
                        if dist <= distance_threshold:
                            all_retrieved.append((dist, doc, dept))
            except Exception:
                pass
                
        all_retrieved.sort(key=lambda x: x[0])
        top_matches = all_retrieved[:n_results]
        
        if not top_matches:
            return "No relevant information found in the specified departments."

        context = "\n\n".join([doc for dist, doc, dept in top_matches])
        prompt = f"""
Answer ONLY from the context.
If the answer cannot be found in the context, reply exactly with:
I don't know that.

Context:
{context}

Question:
{query}

Answer:
"""
        response = chat(
            model=self.llm_model_name,
            messages=[{"role": "user", "content": prompt}]
        )
        return response.message.content

    def department_query(self, question, department):
        return self.query(
            query=question,
            target_departments=[department]
        )
