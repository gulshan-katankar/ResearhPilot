"""
Step 5 — LangChain ReAct Agent
================================
Wires together:
  - OpenAI gpt-4o-mini (the reasoning LLM)
  - The 3 tools from tools.py (pdf_search, web_search, wikipedia_search)
  - A ChatPromptTemplate that makes the LLM use tools natively

Exposes:
  - AgentManager  — singleton that manages the agent lifecycle
"""

import os
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage, AIMessage

from src.ingest import (
    ingest,
    load_vector_store,
    vector_store_exists,
)
from src.rag_chain import get_retriever
from src.tools import ALL_TOOLS, set_retriever

GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")

AGENT_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """You are ResearchPilot, an expert research assistant that synthesizes
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

When you receive tool results, PRESERVE the [Source: ...] tags in your final answer.
Every paragraph of your answer should end with its source citation.
"""),
    MessagesPlaceholder(variable_name="chat_history", optional=True),
    ("human", "{input}"),
    MessagesPlaceholder(variable_name="agent_scratchpad"),
])

class AgentManager:
    """
    Manages the lifecycle of the agent.

    Usage:
        manager = AgentManager()
        manager.initialize()          # load/build vector store, set up agent
        response = manager.run("What is the paper about?")
    """

    def __init__(self):
        self.vector_store = None
        self.agent_executor: AgentExecutor | None = None
        self.chat_history: list = []
        self.is_ready: bool = False

    def initialize(self, force_reindex: bool = False) -> str:
        if force_reindex or not vector_store_exists():
            status = "🔄 Indexing PDF documents..."
            self.vector_store = ingest()
        else:
            status = "📂 Loading existing vector store..."
            self.vector_store = load_vector_store()

        retriever = get_retriever(self.vector_store)
        set_retriever(retriever)

        load_dotenv(override=True)
        llm = ChatGoogleGenerativeAI(
            model=GEMINI_MODEL,
            google_api_key=os.getenv("GEMINI_API_KEY"),
            temperature=0,
            max_tokens=2048,
            max_retries=5,
        )

        agent = create_tool_calling_agent(
            llm=llm,
            tools=ALL_TOOLS,
            prompt=AGENT_PROMPT,
        )

        self.agent_executor = AgentExecutor(
            agent=agent,
            tools=ALL_TOOLS,
            verbose=True,
            max_iterations=6,
            return_intermediate_steps=True,
        )

        self.is_ready = True
        return f"Agent ready! Model: {GEMINI_MODEL}"

    def run(self, question: str) -> dict:
        if not self.is_ready:
            return {
                "answer": "⚠️ Agent not initialized. Please index documents first.",
                "steps":  [],
                "tools_used": [],
            }

        # Use recent 4 messages for context to avoid token bloat
        recent_history = self.chat_history[-4:]

        try:
            result = self.agent_executor.invoke({
                "input": question,
                "chat_history": recent_history,
            })

            steps      = result.get("intermediate_steps", [])
            tools_used = [step[0].tool for step in steps]
            answer     = result.get("output", "")

            if not answer:
                answer = "I could not find a relevant answer. Please try rephrasing your question."
        except Exception as e:
            error_msg = str(e)
            if "503" in error_msg or "high demand" in error_msg.lower() or "429" in error_msg:
                answer = "⚠️ The AI model is currently experiencing high demand or rate limits. Please try again in a few moments."
            else:
                answer = f"⚠️ An error occurred while generating the answer: {error_msg}"
            steps = []
            tools_used = []

        self.chat_history.append(HumanMessage(content=question))
        self.chat_history.append(AIMessage(content=answer))

        return {
            "answer":     answer,
            "steps":      steps,
            "tools_used": tools_used,
        }

    def reset_history(self) -> None:
        self.chat_history = []

if __name__ == "__main__":
    manager = AgentManager()
    print(manager.initialize())
    print()

    while True:
        question = input("You: ").strip()
        if question.lower() in ("exit", "quit", "q"):
            break
        if not question:
            continue

        result = manager.run(question)
        print(f"\n🤖 ResearchPilot: {result['answer']}")
        if result["tools_used"]:
            print(f"   🛠 Tools used: {', '.join(result['tools_used'])}")
        print()
