# 🧠 PROJECT_BRAIN.md — ResearchPilot

> **Single Source of Truth** for all architecture, design, and implementation decisions.
> Any future change — feature, bug-fix, migration, or optimization — MUST be reflected
> here **before** code is written. When given a screenshot, error log, or text describing
> a change, update the relevant section first, then implement.

---

## Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [Migration Plan: Groq/Ollama → OpenAI API](#2-migration-plan-groqollama--openai-api)
3. [Response Quality Upgrade (NotebookLM-style)](#3-response-quality-upgrade-notebooklm-style)
4. [Efficiency Improvements](#4-efficiency-improvements)
5. [Living Document Rules](#5-living-document-rules)
6. [Change Log](#6-change-log)

---

## 1. Architecture Overview

### 1.1 Current Stack

| Layer            | Technology                            | File(s)                            |
|------------------|---------------------------------------|------------------------------------|
| **UI**           | Streamlit 1.45.1 (dark glassmorphism) | `app.py` (933 lines)               |
| **LLM**          | Google Gemini API (`gemini-1.5-flash`) | `src/rag_chain.py`, `src/agent.py` |
| **Agent**        | LangChain ReAct (`AgentExecutor`)     | `src/agent.py`                     |
| **Embeddings**   | Google Generative AI (`text-embedding-004`) | `src/ingest.py`                    |
| **Vector Store** | Supabase pgvector                     | `src/ingest.py`                    |
| **PDF Parsing**  | `pypdf` via `PyPDFLoader`             | `src/ingest.py`                    |
| **Tools**        | pdf_search, web_search (DDG), wikipedia_search | `src/tools.py`            |
| **Runtime**      | Python 3.12                           | `runtime.txt`                      |

### 1.2 Component Flow

```
┌─────────────────────────────────────────────────────────────────────┐
│  Streamlit UI (app.py)                                              │
│  ┌──────────┐   ┌──────────────────────────────────┐               │
│  │ Sidebar  │   │ Chat Area                        │               │
│  │ • Upload │   │ • Welcome screen / suggestions   │               │
│  │ • Index  │   │ • Message bubbles (user/bot)     │               │
│  │ • Tools  │   │ • Agent reasoning expander       │               │
│  │ • Clear  │   │ • Chat input (bottom)            │               │
│  └────┬─────┘   └───────────────┬──────────────────┘               │
│       │                         │                                   │
│       ▼                         ▼                                   │
│  AgentManager.initialize()  AgentManager.run(question)             │
│       │                         │                                   │
│       ▼                         ▼                                   │
│  ┌─────────┐              ┌──────────────┐                         │
│  │ ingest  │              │ AgentExecutor │                         │
│  │ pipeline│              │  (ReAct loop) │                         │
│  └────┬────┘              └──────┬───────┘                         │
│       │                          │                                  │
│       ▼                          ▼                                  │
│  ┌─────────────┐   ┌─────────────────────────────┐                 │
│  │ FAISS       │   │ Tools                       │                 │
│  │ Vector Store│◄──┤ • pdf_search (FAISS)        │                 │
│  │ (on-disk)   │   │ • web_search (DuckDuckGo)   │                 │
│  └─────────────┘   │ • wikipedia_search          │                 │
│                     └─────────────┬───────────────┘                 │
│                                   │                                 │
│                                   ▼                                 │
│                     ┌─────────────────────────────┐                 │
│                     │ Groq API (llama-3.1-8b)     │                 │
│                     │ • Agent reasoning LLM       │                 │
│                     │ • RAG chain LLM             │                 │
│                     └─────────────────────────────┘                 │
└─────────────────────────────────────────────────────────────────────┘
```

### 1.3 Data Flow — Ingestion Pipeline

```
PDF files (data/pdfs/)
    │
    ▼  PyPDFLoader (one Document per page)
Raw Documents
    │
    ▼  RecursiveCharacterTextSplitter (800 chars, 150 overlap)
Chunks
    │
    ▼  HuggingFaceEmbeddings (all-MiniLM-L6-v2, 384-dim)
Embeddings
    │
    ▼  FAISS.from_documents()
vector_store/index.faiss + index.pkl  (3.4 MB + 1.9 MB currently)
```

### 1.4 Data Flow — Query Pipeline

```
User question
    │
    ▼  AgentExecutor (ReAct loop, max 6 iterations)
    ├──► pdf_search  ──► FAISS retriever (top-5 similarity) ──► formatted excerpts
    ├──► web_search  ──► DuckDuckGo (top-5 results) ──► formatted snippets
    └──► wikipedia_search ──► Wikipedia API (top article, 6 sentences)
    │
    ▼  Groq ChatGroq (llama-3.1-8b-instant, temp=0, max_tokens=1024)
Final Answer (+ fallback synthesis if agent hits iteration limit)
    │
    ▼  Streamlit renders: bubble + tool chips + reasoning expander
```

### 1.5 Identified Inefficiencies & Bottlenecks

| #  | Issue | Severity | Details |
|----|-------|----------|---------|
| 🔴 1 | **Stale .env / README references Ollama** | Medium | `.env` still has `OLLAMA_BASE_URL`, `OLLAMA_MODEL`, `OLLAMA_EMBED_MODEL`. README says "Ollama llama3.1 (fully local)". Sidebar badge says "llama3.1 · Ollama · Local". Code actually uses **Groq API**. Confusing and misleading. |
| 🔴 2 | **LLM is llama-3.1-8b-instant** | High | 8B model struggles with ReAct parsing — agent.py has fallback code for when it fails to produce `Final Answer:`. Documented: "llama3.1 (8B) fails with complex prompts". This is the #1 quality bottleneck. |
| 🟡 3 | **Chunking is character-based, not semantic** | Medium | 800-char chunks with 150-char overlap. No section-awareness, no sentence-boundary respect. Breaks mid-sentence frequently, especially on dense academic PDFs. |
| 🟡 4 | **Embeddings are low-dimensional (384-dim)** | Medium | `all-MiniLM-L6-v2` is fast but low quality for academic text. Retrieval precision suffers on technical queries. |
| 🟡 5 | **No retrieval caching** | Medium | Every query re-embeds and searches FAISS. Identical questions re-run the full pipeline. |
| 🟡 6 | **Chat history is string-concatenated into prompt** | Medium | Last 6 messages are formatted as a raw string and prepended to the question. Wastes tokens, reduces tool-calling accuracy, no summarization. |
| 🟡 7 | **RAG chain in `rag_chain.py` is unused** | Low | `build_rag_chain()` and `query_rag()` exist but are **never called by the app**. The agent's `pdf_search` tool does its own retrieval. Dead code. |
| 🟡 8 | **Global mutable `_retriever` in tools.py** | Low | Shared mutable state via `set_retriever()` / global `_retriever`. Works for single-user Streamlit but fragile. |
| 🟢 9 | **No error boundary on Groq rate limits** | Low | Groq free tier has 30 req/min. No retry logic, no backoff. Users get raw errors. |
| 🟢 10 | **API key exposed in .env** | Critical | `GROQ_API_KEY=gsk_f01d...` is committed in `.env`. `.gitignore` covers `.env`, but it's still in the repo history if ever pushed. Rotate key immediately. |
| 🟢 11 | **PDF chunks truncated to 600 chars in tool** | Low | `tools.py` line 66-67: chunks already 800 chars, then truncated to 600 at display. Loses 25% of retrieved context. |

---

## 2. Migration Plan: Groq/Ollama → OpenAI API

### 2.1 Why Migrate

| Factor | Current (Groq + llama-3.1-8b) | Target (OpenAI gpt-4o-mini) |
|--------|-------------------------------|----------------------------|
| **Quality** | Fails ReAct parsing often, needs fallback | Near-perfect tool-calling, structured output |
| **Cost** | Free (Groq) | ~$0.15/M input, $0.60/M output — negligible for personal use |
| **Rate Limits** | 30 req/min, 14.4K tokens/min | 500 RPM / 200K TPM (Tier 1) |
| **Reliability** | Groq has downtime; free tier deprioritized | 99.9% SLA |
| **Features** | No native tool-calling, text-only | JSON mode, function calling, vision |

### 2.2 Recommended Model

> **`gpt-4o-mini`** — Best cost/quality ratio for RAG + tool-calling. Natively supports
> function calling (no more fragile ReAct text parsing). Falls back to `gpt-4o` only
> if user needs vision or 128K context.

### 2.3 File-by-File Migration

#### 2.3.1 `requirements.txt`

```diff
- # LLM — Groq free API (replaces Ollama for cloud deployment)
- langchain-groq==0.2.4
+ # LLM — OpenAI API
+ langchain-openai>=0.3.0
+ openai>=1.40.0
```

No other dependency changes needed. `langchain-huggingface` stays (embeddings are local and free).

#### 2.3.2 `.env`

```diff
- # ── Ollama settings ────────────────────────────────
- OLLAMA_BASE_URL=http://localhost:11434
- OLLAMA_MODEL=llama3.1
- OLLAMA_EMBED_MODEL=nomic-embed-text
+ # ── OpenAI settings ──────────────────────────────────
+ OPENAI_API_KEY=sk-your-openai-key-here
+ OPENAI_MODEL=gpt-4o-mini

  # ── Disable LangSmith tracing ───────────────────────
  LANGCHAIN_TRACING_V2=false
  LANGCHAIN_TRACING=false
- GROQ_API_KEY=gsk_your_groq_api_key_here
```

#### 2.3.3 `src/rag_chain.py`

```diff
- from langchain_groq import ChatGroq
+ from langchain_openai import ChatOpenAI

- GROQ_MODEL   = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")
+ OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

- def get_llm() -> ChatGroq:
-     """Return a ChatGroq LLM instance (Groq free API)."""
-     load_dotenv(override=True)
-     groq_api_key = os.getenv("GROQ_API_KEY")
-     return ChatGroq(
-         model=GROQ_MODEL,
-         api_key=groq_api_key,
-         temperature=0.1,
-         max_tokens=1024,
-     )
+ def get_llm() -> ChatOpenAI:
+     """Return a ChatOpenAI instance (gpt-4o-mini)."""
+     load_dotenv(override=True)
+     return ChatOpenAI(
+         model=OPENAI_MODEL,
+         temperature=0.1,
+         max_tokens=1024,
+     )
```

#### 2.3.4 `src/agent.py` — **Biggest Change**

Replace the fragile ReAct text-parsing agent with OpenAI's native tool-calling agent:

```diff
- from langchain_groq import ChatGroq
- from langchain.agents import AgentExecutor, create_react_agent
- from langchain_core.prompts import PromptTemplate
+ from langchain_openai import ChatOpenAI
+ from langchain.agents import AgentExecutor, create_openai_tools_agent
+ from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

- GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")
+ OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

  # Replace the entire REACT_PROMPT_TEMPLATE with:
+ AGENT_PROMPT = ChatPromptTemplate.from_messages([
+     ("system", """You are ResearchPilot, a precise and thorough research assistant.
+
+ When answering a question:
+ 1. ALWAYS search the uploaded PDFs first using the pdf_search tool.
+ 2. If PDF results are insufficient, use web_search or wikipedia_search.
+ 3. Synthesize information from ALL tool results into a comprehensive answer.
+ 4. ALWAYS cite sources with [Source: filename, Page X] format.
+ 5. If no relevant information is found, say so clearly.
+
+ Be conversational but information-dense. Structure long answers with headers and bullets."""),
+     MessagesPlaceholder(variable_name="chat_history", optional=True),
+     ("human", "{input}"),
+     MessagesPlaceholder(variable_name="agent_scratchpad"),
+ ])
```

In `AgentManager.initialize()`:

```diff
- llm = ChatGroq(
-     model=GROQ_MODEL,
-     api_key=groq_api_key,
-     temperature=0,
-     max_tokens=1024,
- )
- agent = create_react_agent(
-     llm=llm,
-     tools=ALL_TOOLS,
-     prompt=REACT_PROMPT,
- )
+ llm = ChatOpenAI(
+     model=OPENAI_MODEL,
+     temperature=0,
+     max_tokens=2048,
+ )
+ agent = create_openai_tools_agent(
+     llm=llm,
+     tools=ALL_TOOLS,
+     prompt=AGENT_PROMPT,
+ )
```

The `handle_parsing_errors` hack and fallback synthesis in `run()` can be **removed** — OpenAI's tool-calling agent doesn't suffer from the parsing failures that llama-3.1-8b has.

#### 2.3.5 `src/ingest.py` — **No Changes Needed**

Embeddings stay as `HuggingFaceEmbeddings("all-MiniLM-L6-v2")`. They are free, local, and fast. Switching to OpenAI embeddings (`text-embedding-3-small`) is optional and covered in §4.2.

#### 2.3.6 `app.py` — UI Label Updates

```diff
- model_label = "llama3.1 · Ollama"
+ model_label = "gpt-4o-mini · OpenAI"

  # Sidebar model card (line ~838-841):
- <span class="file-icon">🦙</span>
- <span class="file-name">llama3.1 · Ollama · Local</span>
+ <span class="file-icon">🤖</span>
+ <span class="file-name">gpt-4o-mini · OpenAI</span>
```

#### 2.3.7 `check_key.py`

```diff
- from langchain_groq import ChatGroq
+ from langchain_openai import ChatOpenAI

  # Update both tests to use ChatOpenAI with OPENAI_API_KEY
```

#### 2.3.8 `.streamlit/secrets.toml`

```diff
- GROQ_API_KEY = "gsk_your_groq_api_key_here"
+ OPENAI_API_KEY = "sk-your-openai-key-here"
```

### 2.4 Embeddings — Optional Upgrade Path

If embedding quality becomes a bottleneck (see §4.2), switch to OpenAI embeddings:

| Model | Dimensions | Cost | Quality |
|-------|-----------|------|---------|
| `all-MiniLM-L6-v2` (current) | 384 | Free (local) | Good for general text |
| `text-embedding-3-small` | 1536 | $0.02/M tokens | Better for academic text |
| `text-embedding-3-large` | 3072 | $0.13/M tokens | Best quality |

**Recommendation:** Start with local embeddings. Migrate to `text-embedding-3-small` only if retrieval quality is noticeably poor on domain-specific queries.

---

## 3. Response Quality Upgrade (NotebookLM-style)

### 3.1 Target Behavior

NotebookLM-style responses are:

- **Citation-grounded**: Every claim traces to a specific source + page
- **Structured**: Headers, bullets, numbered lists for scannability
- **Information-dense**: No filler, every sentence carries signal
- **Conversational**: Reads like a smart colleague explaining, not a textbook
- **Multi-source synthesis**: Weaves together multiple retrieved passages

### 3.2 System Prompt Redesign

Replace the current minimal system prompt with a comprehensive instruction set:

```python
SYSTEM_PROMPT = """You are ResearchPilot, an expert research assistant that synthesizes
information from uploaded documents and web sources into clear, citation-grounded answers.

## Response Style
- Write in a conversational but information-dense tone — like a knowledgeable colleague
  briefing you on a topic.
- Every factual claim MUST be grounded in a retrieved source. Never fabricate information.
- Structure responses with markdown: use ## headers for sections, bullet points for lists,
  **bold** for key terms, and `code` for technical terms when appropriate.
- For multi-faceted questions, organize the answer into logical sections.

## Citation Rules
- Cite sources inline using this format: [Source: filename.pdf, p. X]
- When multiple sources support a point, cite all: [Source: paper1.pdf, p. 3; paper2.pdf, p. 7]
- At the end of every answer, include a "📎 Sources Used" section listing all referenced documents.
- If conflicting information is found across sources, acknowledge the conflict and present both viewpoints.

## Information Handling
- If the uploaded documents contain the answer, use ONLY document content. Do not speculate.
- If documents are insufficient, explicitly state: "The uploaded documents don't fully cover this.
  Here's what I found from web sources:" — then use web/Wikipedia tools.
- If no information is available, say so clearly. Never hallucinate.

## Answer Structure (for substantial questions)
1. **Direct Answer** — Lead with the key finding or conclusion (1-2 sentences)
2. **Detailed Explanation** — Elaborate with evidence from sources
3. **Key Takeaways** — Bullet-point summary of main points
4. **📎 Sources Used** — List all documents and pages referenced

## Tool Usage Priority
1. pdf_search — ALWAYS search documents first
2. web_search — Only if documents lack information or user requests it
3. wikipedia_search — For background context on well-known concepts
"""
```

### 3.3 Source Attribution Implementation

Currently, `tools.py` returns formatted excerpts but the agent's final answer often drops citations. Fix:

**In `src/tools.py` — `pdf_search()`:**
```python
# Change excerpt format to be more parseable by the LLM:
results.append(
    f"[Source: {source}, Page {page}]\n"
    f"Content: {content}\n"
    f"---"
)
```

**In the agent prompt:**
Add an explicit instruction:
```
When you receive tool results, PRESERVE the [Source: ...] tags in your final answer.
Every paragraph of your answer should end with its source citation.
```

### 3.4 Response Quality Checklist

- [ ] System prompt redesigned with NotebookLM-style instructions
- [ ] Citation format standardized: `[Source: file.pdf, p. X]`
- [ ] Multi-source synthesis enforced in prompt
- [ ] Structured output with headers/bullets/bold
- [ ] Fallback messaging when documents lack information
- [ ] End-of-answer "📎 Sources Used" block
- [ ] Remove 600-char truncation in `tools.py` (line 66-67) — let full 800-char chunks pass through

---

## 4. Efficiency Improvements

### 4.1 Chunking Strategy Review

**Current:** `RecursiveCharacterTextSplitter(chunk_size=800, chunk_overlap=150)`

**Problems:**
- 800 chars is ~160 words — too short for academic paragraphs, often splits mid-argument
- Character-based splitting ignores sentence boundaries
- Overlap of 150 chars (~30 words) is insufficient for continuity
- No metadata enrichment (section headers, paper title baked into chunk)

**Recommended Changes:**

```python
# Option A: Better character-based (immediate, low-effort)
CHUNK_SIZE    = 1200   # ~240 words — full paragraphs
CHUNK_OVERLAP = 200    # ~40 words — better continuity

# Option B: Semantic chunking (future, high-effort)
# Use langchain_experimental.text_splitter.SemanticChunker
# with HuggingFace embeddings for breakpoint detection
```

**Metadata enrichment** (add to each chunk):
```python
# In split_documents(), after splitting:
for chunk in chunks:
    source = chunk.metadata.get("source", "")
    page = chunk.metadata.get("page", "?")
    # Prepend source context to chunk content for better retrieval
    chunk.page_content = (
        f"[From: {os.path.basename(source)}, Page {page}]\n"
        + chunk.page_content
    )
```

### 4.2 Retrieval Pipeline Optimizations

| Optimization | Effort | Impact | Details |
|-------------|--------|--------|---------|
| **Increase TOP_K to 8** | Trivial | Medium | Currently 5. More chunks = more context for the LLM. gpt-4o-mini has 128K context — no reason to be stingy. |
| **Add MMR search** | Low | High | Switch from `similarity` to `mmr` (Maximum Marginal Relevance) to reduce redundant chunks from the same page. |
| **Hybrid search (BM25 + vector)** | Medium | High | Add BM25 keyword search alongside FAISS vector search. Catches exact-match queries that embeddings miss. |
| **Re-ranking** | Medium | High | After retrieval, use a cross-encoder model to re-rank chunks by relevance. Dramatically improves precision. |
| **Query expansion** | Low | Medium | Before retrieval, use the LLM to generate 2-3 reformulations of the query, search with all, deduplicate results. |

**Immediate wins (implement now):**

```python
# In rag_chain.py — get_retriever():
def get_retriever(vector_store: FAISS):
    return vector_store.as_retriever(
        search_type="mmr",           # ← Changed from "similarity"
        search_kwargs={
            "k": 8,                  # ← Increased from 5
            "fetch_k": 20,           # Fetch 20, then MMR-select 8
            "lambda_mult": 0.7,      # Balance relevance vs diversity
        },
    )
```

### 4.3 Caching & Context Window

**Query-level caching:**
```python
# In agent.py — add a simple LRU cache for repeated questions
from functools import lru_cache
import hashlib

# Cache last 50 unique queries
@lru_cache(maxsize=50)
def _cached_retrieval(query_hash: str, query: str):
    return _retriever.invoke(query)
```

**Chat history optimization:**
Replace raw string concatenation with a sliding window + summarization:

```python
# Current (wasteful):
history_str = self._format_history()  # Last 6 raw messages

# Better:
# 1. Keep only last 4 messages as-is
# 2. Summarize older messages into a 1-paragraph context
# 3. Use LangChain's ConversationSummaryBufferMemory
```

**Context window budget for gpt-4o-mini (128K tokens):**

| Component | Token Budget |
|-----------|-------------|
| System prompt | ~500 |
| Chat history (4 turns) | ~2,000 |
| Retrieved chunks (8 × 1200 chars) | ~3,200 |
| Agent scratchpad | ~1,000 |
| **Total input** | **~6,700** |
| Output (max) | 2,048 |
| **Total** | **~8,750** |

This leaves massive headroom. No context window issues with gpt-4o-mini.

### 4.4 Unused Code Cleanup

| Item | File | Action |
|------|------|--------|
| `build_rag_chain()` | `src/rag_chain.py` | Remove or repurpose — never called by app |
| `query_rag()` | `src/rag_chain.py` | Remove or repurpose — never called by app |
| Ollama env vars | `.env` | Remove `OLLAMA_BASE_URL`, `OLLAMA_MODEL`, `OLLAMA_EMBED_MODEL` |
| `REACT_PROMPT_TEMPLATE` | `src/agent.py` | Replace with `ChatPromptTemplate` (§2.3.4) |
| Fallback synthesis | `src/agent.py` L186-210 | Remove after OpenAI migration (tool-calling doesn't fail this way) |

---

## 5. Living Document Rules

### 5.1 This File Is Law

1. **Before any code change**: Update the relevant section of this document first.
2. **After any code change**: Verify this document reflects the new state.
3. **On bug reports**: Add a new entry to §6 Change Log with the issue and fix.
4. **On feature requests**: Add a design section before implementing.
5. **On screenshots/error logs**: Analyze, update the relevant section, then implement.

### 5.2 Section Ownership

| Section | Updated When |
|---------|-------------|
| §1 Architecture | Any structural change (new file, new dependency, new service) |
| §2 Migration | Progress on Groq→OpenAI migration |
| §3 Response Quality | Prompt changes, citation format changes, output style changes |
| §4 Efficiency | Chunking, retrieval, caching, or performance changes |
| §6 Change Log | Every change, no exceptions |

### 5.3 Conventions

- Use ✅ for completed items, 🔲 for pending, 🚧 for in-progress
- Use `🔴 Critical`, `🟡 Medium`, `🟢 Low` for severity
- Always include file paths relative to project root
- Code diffs use standard `diff` format with `+` / `-` markers

---

## 6. Change Log

| Date | Section | Change | Status |
|------|---------|--------|--------|
| 2026-06-16 | All | Initial PROJECT_BRAIN.md created — full codebase audit completed | ✅ |
| 2026-06-16 | §2 | Groq → OpenAI migration | ✅ Complete |
| 2026-06-16 | §3 | NotebookLM-style system prompt | ✅ Complete |
| 2026-06-16 | §4.1 | Chunking upgrade (800→1200, metadata enrichment) | ✅ Complete |
| 2026-06-16 | §4.2 | MMR retrieval + TOP_K increase | ✅ Complete |
| 2026-06-16 | §4.3 | Query caching / History update | ✅ Complete |
| 2026-06-16 | §4.4 | Dead code cleanup | ✅ Complete |
| 2026-06-16 | §1.5 #10 | 🔴 Rotate exposed Groq API key | ✅ Complete (replaced with placeholder) |
| 2026-06-17 | §2 | OpenAI → Google Gemini migration | ✅ Complete |

---

> **End of PROJECT_BRAIN.md**
> Last audited: 2026-06-16 | Audited by: ResearchPilot Brain Agent
