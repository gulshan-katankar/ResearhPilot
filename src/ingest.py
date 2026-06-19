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
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_community.vectorstores import SupabaseVectorStore
from supabase.client import Client, create_client

# ── Load env vars ───────────────────────────────────────────────
load_dotenv()

# Gemini Embeddings API (Requires GEMINI_API_KEY)
EMBED_MODEL_NAME  = "models/embedding-001"
PDF_DIR           = Path("data/pdfs")

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

def get_supabase_client() -> Client:
    if not SUPABASE_URL or not SUPABASE_KEY:
        raise ValueError("SUPABASE_URL or SUPABASE_KEY is missing from environment variables.")
    return create_client(SUPABASE_URL, SUPABASE_KEY)

# ── Chunking config ─────────────────────────────────────────────────────────
CHUNK_SIZE    = 1200  # characters per chunk
CHUNK_OVERLAP = 200   # overlap to preserve context across chunk boundaries


def load_pdfs(pdf_dir: Path) -> list:
    """Walk a directory and load every PDF found."""
    docs = []
    pdf_files = [p for p in pdf_dir.glob("**/*") if p.suffix.lower() == ".pdf"]

    if not pdf_files:
        raise FileNotFoundError(
            f"No PDF files found in '{pdf_dir}'. "
            "Please drop at least one PDF into data/pdfs/ before indexing."
        )

    print(f"📄 Found {len(pdf_files)} PDF(s):")
    for pdf_path in pdf_files:
        print(f"   • {pdf_path.name}")
        loader = PyPDFLoader(str(pdf_path))
        docs.extend(loader.load()) #reads all pages and each page becomes a langchain doc

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
    
    # Metadata enrichment
    for chunk in chunks:
        source = chunk.metadata.get("source", "")
        page = chunk.metadata.get("page", "?")
        # Prepend source context to chunk content for better retrieval
        chunk.page_content = (
            f"[From: {os.path.basename(source)}, Page {page}]\n"
            + chunk.page_content
        )
        
    print(f"✂️  Split into {len(chunks)} chunks "
          f"(size={CHUNK_SIZE}, overlap={CHUNK_OVERLAP}).\n")
    return chunks


def get_embeddings():
    return GoogleGenerativeAIEmbeddings(
        model=EMBED_MODEL_NAME,
        google_api_key=os.environ.get("GEMINI_API_KEY")
    )


def build_vector_store(chunks: list) -> SupabaseVectorStore:
    """Embed chunks and upload them to Supabase pgvector."""
    print(f"🔢 Embedding with '{EMBED_MODEL_NAME}' (Gemini) ...")
    supabase = get_supabase_client()
    embeddings = get_embeddings()
    vector_store = SupabaseVectorStore.from_documents(
        chunks,
        embeddings,
        client=supabase,
        table_name="documents",
        query_name="match_documents"
    )
    print("   → Embeddings and upload complete.\n")
    return vector_store


def load_vector_store() -> SupabaseVectorStore:
    """Initialize a Supabase Vector Store client for querying."""
    supabase = get_supabase_client()
    embeddings = get_embeddings()
    vector_store = SupabaseVectorStore(
        client=supabase,
        embedding=embeddings,
        table_name="documents",
        query_name="match_documents"
    )
    print(f"📂 Supabase vector store client loaded.\n")
    return vector_store


def vector_store_exists() -> bool:
    """Check if the Supabase documents table has rows."""
    try:
        supabase = get_supabase_client()
        res = supabase.table("documents").select("id").limit(1).execute()
        return len(res.data) > 0
    except Exception:
        return False


def ingest(pdf_dir: Path = PDF_DIR) -> SupabaseVectorStore:
    """
    Full pipeline: load PDFs → split → embed → upload to Supabase.
    Called by the agent on startup or when the user uploads new PDFs.
    """
    print("=" * 55)
    print("  ResearchPilot — PDF Ingestion Pipeline (Supabase)")
    print("=" * 55 + "\n")

    docs   = load_pdfs(pdf_dir)
    chunks = split_documents(docs)
    
    # First, clear the existing table if we are re-indexing
    supabase = get_supabase_client()
    try:
        # Supabase doesn't easily support DELETE without conditions that match everything nicely,
        # so we delete where id is not null (which deletes all rows)
        supabase.table("documents").delete().neq("id", "00000000-0000-0000-0000-000000000000").execute()
    except Exception as e:
        print(f"Warning: could not clear old documents: {e}")

    vs = build_vector_store(chunks)

    print("✅ Ingestion complete! Vector store is ready.\n")
    return vs


# ── Standalone test ─────────────────────────────────────────────────────────
if __name__ == "__main__":
    ingest()
