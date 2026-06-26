# Multi-Department RAG System

A Retrieval-Augmented Generation (RAG) system designed for enterprise use. It allows different departments (HR, IT, Finance, etc.) to securely maintain their own knowledge bases and enables users to query across these isolated data stores.

##  Current Stage & Roadmap

**Status:** Transitioning from MVP to an Agentic Orchestrator Architecture.

Currently, the system uses a basic FastAPI backend with hard-coded endpoints (`/chat/{department}`) and synchronous document ingestion. 

We are actively migrating to a robust **Agentic Orchestrator System** which will feature:
*   **Master Orchestrator Agent**: A central agent to handle query intent, dynamic routing, and data synthesis.
*   **Role-Based Access Control (RBAC)**: Strict data isolation based on user metadata.
*   **Intelligent Ingestion Pipeline**: Asynchronous batch processing with semantic chunking and enterprise-grade format parsers (e.g., Unstructured.io).
*   **Dual-Track Retrieval**: Integrating Knowledge Graphs (e.g., Neo4j) alongside our current Vector DB (ChromaDB) to manage complex entity relationships.
*   **LangGraph Workflows**: Moving away from static code paths to graph-based agent decision making.

For full details on the planned architecture, please read the [Architecture Report](report.md).

##  Key Features (Current)
*   **Multi-Department Vector Stores**: Separate ChromaDB collections for each department.
*   **Access Control**: Basic login simulating user roles.
*   **File Uploads**: Admin endpoints to ingest PDF, DOCX, and TXT files.
*   **Local LLM Integration**: Uses `ollama` for fast, localized question answering.

##  Tech Stack
*   **Backend**: FastAPI, Python
*   **AI/ML**: SentenceTransformers, Ollama (Local LLMs)
*   **Database**: ChromaDB (Persistent Vector DB)
*   **Frontend**: Vanilla HTML/JS (Static files served via FastAPI)

##  Getting Started

### Prerequisites
* Python 3.9+
* [Ollama](https://ollama.com/) installed and running locally with your chosen model.

### Installation
1. Install Python dependencies:
   ```bash
   cd backend
   python -m venv env
   source env/bin/avtivate
   pip install -r requirements.txt
   ```
2. Start the FastAPI server:
   ```bash
   source env/bin/activate
   uvicorn api:app --reload
   ```
3. Open your browser and navigate to: `http://localhost:8000`
