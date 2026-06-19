import os
import sys
import io

# Force UTF-8 encoding for Windows consoles to avoid emoji crash
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

import shutil
from pathlib import Path
from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from src.agent import AgentManager
from src.ingest import vector_store_exists

app = FastAPI(title="ResearchPilot API")

# Setup CORS
allowed_origins = os.environ.get("ALLOWED_ORIGINS", "http://localhost:3000,http://localhost:3001").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global agent manager (single session prototype)
manager = AgentManager()

@app.on_event("startup")
async def startup_event():
    # Initialize the agent if vector store exists
    if vector_store_exists():
        print("Initializing existing vector store on startup...")
        manager.initialize()

class ChatRequest(BaseModel):
    message: str

@app.post("/api/chat")
async def chat(request: ChatRequest):
    if not manager.is_ready:
        if vector_store_exists():
            manager.initialize()
        else:
            return {"answer": "Agent not initialized. Please upload documents first.", "tools_used": []}
            
    result = manager.run(request.message)
    return {
        "answer": result["answer"],
        "tools_used": result["tools_used"]
    }

@app.post("/api/upload")
async def upload_file(file: UploadFile = File(...)):
    # Save file to data/pdfs
    pdf_dir = Path("data/pdfs")
    pdf_dir.mkdir(parents=True, exist_ok=True)
    
    file_path = pdf_dir / file.filename
    with file_path.open("wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    # Reindex the documents
    manager.initialize(force_reindex=True)
    
    return {"message": f"Successfully uploaded and indexed {file.filename}"}

@app.get("/api/sources")
async def get_sources():
    pdf_dir = Path("data/pdfs")
    if not pdf_dir.exists():
        return {"sources": []}
        
    files = [f.name for f in pdf_dir.glob("*") if f.suffix.lower() == ".pdf"]
    return {"sources": [{"name": f} for f in files]}

@app.delete("/api/sources/{filename}")
async def delete_source(filename: str):
    pdf_dir = Path("data/pdfs")
    file_path = pdf_dir / filename
    
    if file_path.exists():
        file_path.unlink()
        
        # Check if there are any PDFs left before re-indexing
        remaining_pdfs = [p for p in pdf_dir.glob("*") if p.suffix.lower() == ".pdf"]
        if remaining_pdfs:
            manager.initialize(force_reindex=True)
        else:
            # No files left. Clear the vector store from memory.
            manager.vector_store = None
            manager.is_ready = False
            # Clear Supabase documents table
            try:
                from src.ingest import get_supabase_client
                supabase = get_supabase_client()
                supabase.table("documents").delete().neq("id", "00000000-0000-0000-0000-000000000000").execute()
                print("🗑️ Cleared all documents from Supabase vector store.")
            except Exception as e:
                print(f"Warning: could not clear Supabase table: {e}")
                
        return {"message": f"Deleted {filename}"}
    return {"message": "File not found"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
