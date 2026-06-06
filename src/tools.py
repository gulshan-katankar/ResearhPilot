"""
Step 4 — Tool Definitions
==========================
Defines the tools available to the LangChain ReAct agent:

  1. pdf_search      — Search the FAISS vector store (RAG over your PDFs)
  2. web_search      — Live DuckDuckGo web search
  3. wikipedia_search — Wikipedia article lookup

Each tool is a plain Python function decorated with @tool.
The agent decides which tool to use based on the question.
"""

import os
import textwrap
from dotenv import load_dotenv

from langchain_core.tools import tool
from langchain_community.vectorstores import FAISS

load_dotenv()

# ── Shared state (set once by the agent at startup) ──────────────────────────
# The retriever is injected here so the pdf_search tool can access it
# without it being a parameter (LangChain tools must have a single str input).
_retriever = None

def set_retriever(retriever) -> None:
    """Called by agent.py after loading the vector store."""
    global _retriever
    _retriever = retriever


# ────────────────────────────────────────────────────────────────────────────
# Tool 1 — PDF Search (RAG)
# ────────────────────────────────────────────────────────────────────────────
@tool
def pdf_search(query: str) -> str:
    """
    Search the uploaded PDF documents for information relevant to the query.
    Use this tool FIRST for any question that might be answered by the research papers,
    reports, or documents the user has uploaded.
    Returns the most relevant passages with source citations.
    """
    if _retriever is None:
        return (
            "⚠️ No documents have been indexed yet. "
            "Please upload PDFs and click 'Index Documents' first."
        )

    try:
        docs = _retriever.invoke(query)
    except Exception as e:
        return f"❌ Error searching documents: {e}"

    if not docs:
        return "No relevant content found in the uploaded documents for this query."

    results = []
    for i, doc in enumerate(docs, 1):
        meta    = doc.metadata
        source  = os.path.basename(meta.get("source", "unknown"))
        page    = meta.get("page", "?")
        content = doc.page_content.strip()
        # Truncate very long chunks for readability
        if len(content) > 600:
            content = content[:600] + "…"
        results.append(
            f"[Excerpt {i}] Source: {source}, Page {page}\n{content}"
        )

    return "\n\n---\n\n".join(results)


# ────────────────────────────────────────────────────────────────────────────
# Tool 2 — DuckDuckGo Web Search
# ────────────────────────────────────────────────────────────────────────────
@tool
def web_search(query: str) -> str:
    """
    Search the web using DuckDuckGo for live, up-to-date information.
    Use this tool when:
    - The question requires recent news or current events
    - The uploaded PDFs don't contain sufficient information
    - The user explicitly asks to search the web
    Returns a summary of the top search results with links.
    """
    try:
        from duckduckgo_search import DDGS
    except ImportError:
        return "❌ duckduckgo-search is not installed. Run: pip install duckduckgo-search"

    try:
        results = []
        with DDGS() as ddgs:
            for r in ddgs.text(query, max_results=5):
                title = r.get("title", "No title")
                href  = r.get("href", "")
                body  = r.get("body", "")
                # Trim body to 250 chars
                body  = textwrap.shorten(body, width=250, placeholder="…")
                results.append(f"**{title}**\n{body}\n🔗 {href}")

        if not results:
            return "No web results found for this query."

        return "\n\n---\n\n".join(results)

    except Exception as e:
        return f"❌ Web search failed: {e}"


# ────────────────────────────────────────────────────────────────────────────
# Tool 3 — Wikipedia Search
# ────────────────────────────────────────────────────────────────────────────
@tool
def wikipedia_search(query: str) -> str:
    """
    Look up a topic on Wikipedia for encyclopedic background information.
    Use this tool when:
    - The user asks about a well-known concept, person, event, or technology
    - You need a concise factual overview of a topic
    - The PDFs and web search haven't provided enough context
    Returns a summary from the most relevant Wikipedia article.
    """
    try:
        import wikipedia as wiki
    except ImportError:
        return "❌ wikipedia is not installed. Run: pip install wikipedia"

    try:
        wiki.set_lang("en")
        # Try an exact search first
        search_results = wiki.search(query, results=3)
        if not search_results:
            return f"No Wikipedia article found for: '{query}'"

        # Use the top result
        page    = wiki.page(search_results[0], auto_suggest=False)
        summary = wiki.summary(search_results[0], sentences=6, auto_suggest=False)

        return (
            f"📖 **{page.title}**\n\n"
            f"{summary}\n\n"
            f"🔗 {page.url}"
        )

    except wiki.exceptions.DisambiguationError as e:
        # Multiple matches — try the first option
        try:
            page    = wiki.page(e.options[0], auto_suggest=False)
            summary = wiki.summary(e.options[0], sentences=6, auto_suggest=False)
            return (
                f"📖 **{page.title}** (disambiguation resolved)\n\n"
                f"{summary}\n\n"
                f"🔗 {page.url}"
            )
        except Exception:
            return f"Multiple Wikipedia pages found: {', '.join(e.options[:5])}"

    except wiki.exceptions.PageError:
        return f"No Wikipedia page found for: '{query}'"

    except Exception as e:
        return f"❌ Wikipedia lookup failed: {e}"


# ── Tool registry ─────────────────────────────────────────────────────────────
# Collected here so agent.py can import a single list
ALL_TOOLS = [pdf_search, web_search, wikipedia_search]


# ── Standalone test ───────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("🔍 Testing web_search...")
    print(web_search.invoke("latest advances in transformer models 2024"))
    print("\n" + "=" * 60 + "\n")

    print("📖 Testing wikipedia_search...")
    print(wikipedia_search.invoke("Retrieval Augmented Generation"))
