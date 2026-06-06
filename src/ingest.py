"""
Step 2 — PDF Ingestion & FAISS Vector Store
============================================
Loads PDF files from a directory, splits them into chunks,
embeds them using Ollama's nomic-embed-text model, and saves
the FAISS index to disk for later retrieval.

Usage (standalone test):
    python -m src.ingest
"""

import os
from pathlib import Path
from dotenv import load_dotenv

from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_ollama import OllamaEmbeddings
from langchain_community.vectorstores import FAISS

# ── Load env vars ───────────────────────────────────────────────────────────
load_dotenv()

BASE_URL        = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
EMBED_MODEL     = os.getenv("OLLAMA_EMBED_MODEL", "nomic-embed-text")
PDF_DIR         = Path("data/pdfs")
VECTOR_STORE_DIR = Path("vector_store")

# ── Chunking config ─────────────────────────────────────────────────────────
CHUNK_SIZE    = 800   # characters per chunk
CHUNK_OVERLAP = 150   # overlap to preserve context across chunk boundaries


def load_pdfs(pdf_dir: Path) -> list:
    """Walk a directory and load every PDF found."""
    docs = []
    pdf_files = list(pdf_dir.glob("**/*.pdf"))

    if not pdf_files:
        raise FileNotFoundError(
            f"No PDF files found in '{pdf_dir}'. "
            "Please drop at least one PDF into data/pdfs/ before indexing."
        )

    print(f"📄 Found {len(pdf_files)} PDF(s):")
    for pdf_path in pdf_files:
        print(f"   • {pdf_path.name}")
        loader = PyPDFLoader(str(pdf_path))
        docs.extend(loader.load())

    print(f"   → Loaded {len(docs)} page(s) total.\n")
    return docs


def split_documents(docs: list) -> list:
    """Split documents into smaller overlapping chunks for retrieval."""
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n\n", "\n", ". ", " ", ""],
    )
    chunks = splitter.split_documents(docs)
    print(f"✂️  Split into {len(chunks)} chunks "
          f"(size={CHUNK_SIZE}, overlap={CHUNK_OVERLAP}).\n")
    return chunks


def build_vector_store(chunks: list) -> FAISS:
    """Embed chunks and build a FAISS vector store."""
    print(f"🔢 Embedding with '{EMBED_MODEL}' via Ollama ({BASE_URL}) ...")
    embeddings = OllamaEmbeddings(
        model=EMBED_MODEL,
        base_url=BASE_URL,
    )
    vector_store = FAISS.from_documents(chunks, embeddings)
    print("   → Embeddings complete.\n")
    return vector_store


def save_vector_store(vector_store: FAISS, path: Path = VECTOR_STORE_DIR) -> None:
    """Persist the FAISS index to disk."""
    path.mkdir(parents=True, exist_ok=True)
    vector_store.save_local(str(path))
    print(f"💾 Vector store saved to '{path}/'.\n")


def load_vector_store(path: Path = VECTOR_STORE_DIR) -> FAISS:
    """Load a previously saved FAISS index from disk."""
    embeddings = OllamaEmbeddings(model=EMBED_MODEL, base_url=BASE_URL)
    vector_store = FAISS.load_local(
        str(path),
        embeddings,
        allow_dangerous_deserialization=True,   # safe — files are ours
    )
    print(f"📂 Vector store loaded from '{path}/'.\n")
    return vector_store


def vector_store_exists(path: Path = VECTOR_STORE_DIR) -> bool:
    """Return True if a saved FAISS index already exists on disk."""
    return (path / "index.faiss").exists()


def ingest(pdf_dir: Path = PDF_DIR) -> FAISS:
    """
    Full pipeline: load PDFs → split → embed → save → return vector store.
    Called by the agent on startup or when the user uploads new PDFs.
    """
    print("=" * 55)
    print("  ResearchPilot — PDF Ingestion Pipeline")
    print("=" * 55 + "\n")

    docs   = load_pdfs(pdf_dir)
    chunks = split_documents(docs)
    vs     = build_vector_store(chunks)
    save_vector_store(vs)

    print("✅ Ingestion complete! Vector store is ready.\n")
    return vs


# ── Standalone test ─────────────────────────────────────────────────────────
if __name__ == "__main__":
    ingest()
