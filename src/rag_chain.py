"""
Step 3 — RAG Chain (Retrieval-Augmented Generation)
====================================================
Builds a LangChain retrieval chain that:
  1. Takes a user question
  2. Retrieves the top-k most relevant chunks from the FAISS vector store
  3. Sends the chunks + question to llama3.1 via Ollama
  4. Returns a grounded answer with source citations

This module exposes:
  - build_rag_chain(vector_store) → a callable chain
  - get_retriever(vector_store)   → standalone retriever (used by the agent tool)
"""

import os
from dotenv import load_dotenv

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_community.vectorstores import SupabaseVectorStore

load_dotenv()

GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")



def get_llm() -> ChatGoogleGenerativeAI:
    """Return a ChatGoogleGenerativeAI instance (gemini-2.5-flash)."""
    load_dotenv(override=True)
    return ChatGoogleGenerativeAI(
        model=GEMINI_MODEL,
        google_api_key=os.getenv("GEMINI_API_KEY"),
        temperature=0.1,
        max_tokens=1024,
    )


def get_retriever(vector_store: SupabaseVectorStore):
    """
    Return a Supabase retriever configured for similarity search.
    Used directly by the agent's PDF tool.
    """
    return vector_store.as_retriever(
        search_type="similarity",
        search_kwargs={
            "k": 8,
        },
    )


# ── Standalone test ──────────────────────────────────────────────────────────
if __name__ == "__main__":
    from src.ingest import load_vector_store, vector_store_exists

    if not vector_store_exists():
        print("❌ No vector store found. Run `python -m src.ingest` first.")
        raise SystemExit(1)

    vs    = load_vector_store()
    retriever = get_retriever(vs)

    question = input("Ask a question about your PDFs: ")
    docs = retriever.invoke(question)

    print("\n📖 Retrieved chunks:")
    for i, doc in enumerate(docs):
        print(f"\nChunk {i+1}:")
        print(doc.page_content[:200] + "...")

