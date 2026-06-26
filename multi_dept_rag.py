import os
from sentence_transformers import SentenceTransformer
from ollama import chat
from pypdf import PdfReader
from docx import Document
import chromadb

class MultiDeptRAG:
    def __init__(self, db_path="./chroma_db_multi", embed_model_name="BAAI/bge-small-en-v1.5", llm_model_name="gemma2:2b"):
        
        # Initializes the Multi-Department RAG System.
       
        print("Loading embedding model...")
        self.embed_model = SentenceTransformer(embed_model_name)
        
        # Use a persistent ChromaDB client
        self.client = chromadb.PersistentClient(path=db_path)
        self.llm_model_name = llm_model_name
        print("System initialized.")

    def _process_file(self, path):
        
        # Helper method to parse text from .txt, .pdf, or .docx files.
        
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
        
        # Admin functionality: Upload files into a specific department's vector database (ChromaDB collection).
        
        # Enforce ChromaDB collection name rules (min 3 chars)
        safe_name = f"dept_{department_name}" if len(department_name) < 3 else department_name
        # Get or create a dedicated collection for this department
        collection = self.client.get_or_create_collection(name=safe_name)
        
        documents = []
        metadatas = []
        
        step = chunk_size - overlap
        
        for path in file_paths:
            path = path.strip()
            text = self._process_file(path)
            if not text:
                continue
                
            print(f"Loaded: {path} (Characters: {len(text)})")
            
            # Chunking process
            for i in range(0, len(text), step):
                chunk = text[i:i + chunk_size]
                if chunk.strip():
                    documents.append(chunk)
                    metadatas.append({"source": path, "department": department_name})
                    
        if not documents:
            print("No valid content to upload.")
            return

        # Create embeddings for the chunks
        print(f"Creating embeddings for {len(documents)} chunks...")
        embeddings = self.embed_model.encode(documents, show_progress_bar=True).tolist()
        
        # Indexing: add to the department-specific collection
        existing_count = collection.count()
        ids = [str(existing_count + i) for i in range(len(documents))]
        
        collection.add(
            ids=ids,
            documents=documents,
            embeddings=embeddings,
            metadatas=metadatas
        )
        print(f"Successfully uploaded to department '{department_name}'. Total chunks in DB: {collection.count()}")

    def admin_delete_file(self, department_name, file_path):
        safe_name = f"dept_{department_name}" if len(department_name) < 3 else department_name
        try:
            collection = self.client.get_collection(name=safe_name)
            collection.delete(where={"source": file_path})
            print(f"Deleted chunks for {file_path} from department '{department_name}'")
        except ValueError:
            print(f"Collection {safe_name} does not exist.")

    def query(self, query, target_departments, n_results=3, distance_threshold=1.2):
        
        # User functionality: Query one or more departments. 
        # Fetches information only from the targeted department databases to reduce computational cost.
        # Applies a threshold to reject irrelevant chunks and ensures only the absolute top `n_results` are used.
        
        print(f"\nSearching in departments: {', '.join(target_departments)}")
        
        # Create embedding for the query
        query_embedding = self.embed_model.encode(query).tolist()
        
        # Store tuples of (distance, document, department)
        all_retrieved = []
        
        # Fetch relevant chunks from each targeted department
        for dept in target_departments:
            safe_name = f"dept_{dept}" if len(dept) < 3 else dept
            try:
                collection = self.client.get_collection(name=safe_name)
                # Request both documents and their distance scores
                results = collection.query(
                    query_embeddings=[query_embedding],
                    n_results=n_results,
                    include=["documents", "distances"]
                )
                
                if results["documents"] and len(results["documents"]) > 0:
                    docs = results["documents"][0]
                    distances = results["distances"][0]
                    
                    for doc, dist in zip(docs, distances):
                        # Filter out irrelevant chunks (Chroma default is L2 distance, lower is better)
                        if dist <= distance_threshold:
                            all_retrieved.append((dist, doc, dept))
                        else:
                            print(f"Rejected chunk from '{dept}' (distance {dist:.2f} > threshold {distance_threshold})")
                            
            except ValueError:
                print(f"Warning: Department '{dept}' vector database does not exist.")
                
        # Sort all retrieved chunks globally by distance (lowest distance = highest similarity)
        all_retrieved.sort(key=lambda x: x[0])
        
        # Keep ONLY the absolute top `n_results` matches across all queried departments
        top_matches = all_retrieved[:n_results]
        
        if not top_matches:
            return "No relevant information found in the specified departments."

        # Create combined context
        context = "\n\n".join([doc for dist, doc, dept in top_matches])
        
        # Build the prompt with strict anti-hallucination instructions
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
        # Synthesize answer using the lightweight LLM
        response = chat(
            model=self.llm_model_name,
            messages=[{"role": "user", "content": prompt}]
        )
        
        return response.message.content


# Interactive Flow Example

if __name__ == "__main__":
    system = MultiDeptRAG()
    
    while True:
        print("\n=== Main Menu ===")
        print("1. Admin: Upload Document to Department")
        print("2. User: Ask a Question")
        print("3. Exit")
        choice = input("Select an option (1/2/3): ").strip()
        
        if choice == '1':
            dept = input("Enter department name (e.g., hr, it, finance): ").strip().lower()
            paths = input("Enter file paths separated by commas: ").split(",")
            system.admin_upload_to_department(dept, paths)
            
        elif choice == '2':
            query = input("Ask your question: ").strip()
            depts = input("Enter departments to search (comma-separated, e.g., hr,it): ").split(",")
            depts = [d.strip().lower() for d in depts if d.strip()]
            
            answer = system.query(query, target_departments=depts)
            print("\nAnswer:")
            print(answer)
            
        elif choice == '3':
            print("Exiting...")
            break
        else:
            print("Invalid choice.")
