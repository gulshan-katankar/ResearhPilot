# ResearchPilot — PDF Chatbot with Tool Calling

A local AI research assistant that answers questions from your PDFs and can call live tools.

## Tech Stack
- **LLM**: Ollama `llama3.1` (fully local)
- **Embeddings**: `nomic-embed-text` via Ollama
- **Framework**: LangChain v0.3
- **Vector DB**: FAISS (local)
- **UI**: Streamlit

## Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Pull the embedding model (one-time)
ollama pull nomic-embed-text

# 3. Drop your PDFs into data/pdfs/

# 4. Run the app
https://researchpilot9827.streamlit.app/
```

## Project Structure

```
ResearchPilot/
├── .env                  # Ollama config
├── requirements.txt
├── app.py                # Streamlit UI
├── src/
│   ├── ingest.py         # PDF loading & FAISS indexing
│   ├── rag_chain.py      # Retrieval chain
│   ├── tools.py          # Tool definitions
│   └── agent.py          # ReAct agent
├── data/pdfs/            # Put PDFs here
└── vector_store/         # FAISS index (auto-created)
```
