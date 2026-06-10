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

from langchain_groq import ChatGroq
from langchain_community.vectorstores import FAISS
from langchain.chains import create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_core.prompts import ChatPromptTemplate

load_dotenv()

GROQ_MODEL   = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")
TOP_K        = 5   # number of chunks to retrieve per query

# ── System prompt ────────────────────────────────────────────────────────────
# Instructs the LLM to stay grounded in the retrieved context
SYSTEM_PROMPT = """You are ResearchPilot, a precise and helpful research assistant.

Use ONLY the following retrieved context to answer the user's question.
If the context does not contain enough information, say:
"I couldn't find a clear answer in the uploaded documents."

Always cite the source document and page number at the end of your answer
in this format: [Source: <filename>, Page <page>]

Context:
{context}"""

RAG_PROMPT = ChatPromptTemplate.from_messages(
    [
        ("system", SYSTEM_PROMPT),
        ("human", "{input}"),
    ]
)


def get_llm() -> ChatGroq:
    """Return a ChatGroq LLM instance (Groq free API)."""
    load_dotenv(override=True)   # ensure .env always wins
    groq_api_key = os.getenv("GROQ_API_KEY")
    return ChatGroq(
        model=GROQ_MODEL,
        api_key=groq_api_key,
        temperature=0.1,
        max_tokens=1024,
    )


def get_retriever(vector_store: FAISS):
    """
    Return a FAISS retriever configured for similarity search.
    Used directly by the agent's PDF tool.
    """
    return vector_store.as_retriever(
        search_type="similarity",
        search_kwargs={"k": TOP_K},
    )


def build_rag_chain(vector_store: FAISS):
    """
    Build and return the full RAG chain.

    Chain flow:
        question
          └─► retriever  (FAISS similarity search → top-k chunks)
                └─► stuff_documents_chain  (inject chunks into prompt)
                      └─► ChatOllama (llama3.1)
                            └─► answer + source_documents
    """
    llm       = get_llm()
    retriever = get_retriever(vector_store)

    # Combines retrieved docs by "stuffing" them into the prompt context
    combine_docs_chain = create_stuff_documents_chain(llm, RAG_PROMPT)

    # Full chain: retriever + LLM
    rag_chain = create_retrieval_chain(retriever, combine_docs_chain)
    return rag_chain


def query_rag(chain, question: str) -> dict:
    """
    Run a question through the RAG chain and return a structured result.

    Returns:
        {
            "answer":   str,              # LLM's grounded answer
            "sources":  list[str],        # unique source filenames + pages
            "context":  list[Document],   # raw retrieved chunks
        }
    """
    result = chain.invoke({"input": question})

    # Extract unique sources from metadata
    sources = []
    for doc in result.get("context", []):
        meta   = doc.metadata
        source = meta.get("source", "unknown")
        page   = meta.get("page", "?")
        entry  = f"{source} (page {page})"
        if entry not in sources:
            sources.append(entry)

    return {
        "answer":  result["answer"],
        "sources": sources,
        "context": result.get("context", []),
    }


# ── Standalone test ──────────────────────────────────────────────────────────
if __name__ == "__main__":
    from src.ingest import load_vector_store, vector_store_exists

    if not vector_store_exists():
        print("❌ No vector store found. Run `python -m src.ingest` first.")
        raise SystemExit(1)

    vs    = load_vector_store()
    chain = build_rag_chain(vs)

    question = input("Ask a question about your PDFs: ")
    result   = query_rag(chain, question)

    print("\n📖 Answer:\n", result["answer"])
    print("\n📎 Sources:")
    for s in result["sources"]:
        print("   •", s)
