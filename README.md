# ResearchPilot 🚀

ResearchPilot is an advanced AI-powered research assistant designed to ingest, analyze, and synthesize information from complex documents (PDFs), live web sources, and Wikipedia. 

It uses a powerful **Retrieval-Augmented Generation (RAG)** pipeline to ground its answers in real citations, completely bypassing hallucinations. 

## ✨ Key Features
- **Intelligent Document Search (RAG)**: Upload PDFs and chat with them. ResearchPilot converts them into embeddings and stores them in Supabase `pgvector` for instant similarity search.
- **Live Web Search**: Automatically queries DuckDuckGo for live context if your documents don't have the answer.
- **Wikipedia Lookups**: Seamlessly retrieves encyclopedic background information for complex topics.
- **Source Citations**: Every claim the AI makes is explicitly backed by a citation to the specific page of the uploaded document or web link.
- **State-of-the-Art AI**: Powered by Google's newest `gemini-2.5-flash` model and `gemini-embedding-2` for incredibly fast and accurate text synthesis.

## 🏗️ Architecture & Tech Stack
- **Frontend**: Next.js 15, React, Tailwind CSS
- **Backend**: FastAPI (Python), Uvicorn
- **AI / LLM**: LangChain, Google Gemini API
- **Database & Vector Store**: Supabase (PostgreSQL with `pgvector` extension)
- **Deployment**: Vercel (Frontend), Render (Backend)

## 🚀 Getting Started

### 1. Supabase Setup
Run the `supabase_setup.sql` script in your Supabase SQL Editor to enable the `vector` extension, create the `documents` table with 3072 dimensions, and create the similarity search RPC function.

### 2. Backend Setup
```bash
# Install dependencies
pip install -r requirements.txt

# Create a .env file with your credentials
GEMINI_API_KEY=your_google_api_key
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_anon_key
```

### 3. Frontend Setup
```bash
cd frontend

# Install dependencies
npm install

# Create a .env.local file
NEXT_PUBLIC_BACKEND_URL=your_backend_url
```

### 4. Run Locally
Start the FastAPI backend:
```bash
uvicorn main:app --reload --port 10000
```
Start the Next.js frontend:
```bash
cd frontend
npm run dev
```
