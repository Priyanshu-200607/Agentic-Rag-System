# Multi-Department RAG System

A Retrieval-Augmented Generation (RAG) system designed for enterprise use. It allows different departments (HR, IT, Finance, etc.) to securely maintain their own knowledge bases, while an intelligent agent dynamically routes user queries to the correct departments based on their access level.

## System Architecture: The Agentic Orchestrator

The system operates using a lightweight, modular **Agentic Orchestrator** architecture written in pure Python (no heavy frameworks required):

1. **Master Agent (Orchestrator)**: 
   - Acts as the central traffic controller.
   - **Access Control (RBAC)**: Checks the user's role to ensure they are allowed to access the requested data.
   - **Intelligent Routing**: Uses an LLM to analyze the user's query and automatically determines which departments hold the relevant information.
   - **Synthesis**: Collects answers from multiple departments and merges them into a single, cohesive response.
   
2. **Department Agents**:
   - Each department (e.g., HR, IT) is represented by its own autonomous agent.
   - Operates on a fully isolated Vector Database (ChromaDB collection).
   - Only searches its own secure data and summarizes the findings independently before reporting back to the Master Agent.

*Note: For the original architectural proposal, see [report.md](report.md).*

## Key Features
* **ReAct Agentic Orchestrator**: The system handles queries using a ReAct-style agentic pattern. Agents are equipped with function tools (`search_vector_db`, `search_knowledge_graph`, and `search_exact_text`) to autonomously explore semantic context, traverse graph relationships, and locate highly specific metrics via exact substring matches. The hallucination-prone Text-to-SQL engine has been completely removed in favor of this robust tool-use paradigm.
* **Hardware-Aware Auto-Scaling & Adaptive Extraction**: A built-in Resource Manager auto-detects hardware to apply active backpressure and dynamic batching. It also evaluates system VRAM to actively toggle between ultra-fast `REBEL` graph ingestion (for consumer GPUs <20GB) and high-quality `llama3` extraction (for enterprise GPUs).
* **Centralized Configuration**: All models, limits, paths, and security settings are centralized in `config.py`. Domain-specific Knowledge Graph patterns are securely stored in `entities.json`.
* **Zero Hard-Coded Routing**: You don't need to manually tell the system where to search. The Master Agent figures out if a question belongs to HR, IT, or multiple departments at once.
* **Granular Security**: Built-in Role-Based Access Control (RBAC) ensures users (like interns) cannot access sensitive data (like Finance) even if they ask for it.
* **Modular Backend**: Clean, separated code structure (`rag_system.py`, `department_agent.py`, `resource_manager.py`) for easy debugging and upgrading.
* **Local Privacy**: Runs entirely locally using `ollama` and `ChromaDB`.

## Tech Stack
* **Backend**: FastAPI, Python
* **AI/ML**: SentenceTransformers (Embeddings), Ollama (Local LLMs)
* **Database**: ChromaDB (Persistent Local Vector DB)
* **Frontend**: Vanilla HTML/JS (Static files served via FastAPI)

## Getting Started

### Prerequisites
* Python 3.9+
* [Ollama](https://ollama.com/) installed and running locally with your chosen model (default is `llama3`).

### Installation
1. Clone the repository and navigate into it:
   ```bash
   git clone <your-repo-url>
   cd department_rag
   ```
2. Run the interactive Unified Auto-Installer:
   ```bash
   python install.py
   ```
   *The installer will ask for your target Operating System (Windows, Mac, Linux, Server) and automatically provision a virtual environment with strict, conflict-free package versions and the correct hardware-accelerated PyTorch binaries (CUDA/MPS).*

3. Start the FastAPI server (as instructed by the installer at the end of its run):
   ```bash
   # Make sure you navigate to backend and activate the generated virtual environment
   cd backend
   
   # For Linux/Mac:
   source env/bin/activate
   
   # For Windows:
   env\Scripts\activate
   
   # Start the server
   uvicorn api:app --reload
   ```
4. Open your browser and navigate to: `http://localhost:8000`

### Testing the App
1. Log in as `admin` (password: `123`) to get upload permissions.
2. Use the left sidebar to upload `.txt`, `.pdf`, or `.docx` files to specific departments (HR, Finance, IT).
3. Log out and log back in as different roles (e.g., `intern` or `hr_guy`) to test the Master Agent's security and intelligent routing!
