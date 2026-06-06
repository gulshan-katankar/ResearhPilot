"""
Step 5 — LangChain ReAct Agent
================================
Wires together:
  - Ollama llama3.1 (the reasoning LLM)
  - The 3 tools from tools.py (pdf_search, web_search, wikipedia_search)
  - A ReAct prompt that makes the LLM think step-by-step

The agent loop:
  Question → Thought → Action (tool call) → Observation → ... → Final Answer

Exposes:
  - AgentManager  — singleton that manages the agent lifecycle
  - stream_agent  — yields reasoning steps for the UI to display
"""

import os
from dotenv import load_dotenv
from langchain_ollama import ChatOllama
from langchain.agents import AgentExecutor, create_react_agent
from langchain_core.prompts import PromptTemplate
from langchain_core.messages import HumanMessage, AIMessage

from src.ingest import (
    ingest,
    load_vector_store,
    vector_store_exists,
    VECTOR_STORE_DIR,
)
from src.rag_chain import get_retriever
from src.tools import ALL_TOOLS, set_retriever

load_dotenv()

BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
MODEL    = os.getenv("OLLAMA_MODEL", "llama3.1")

# ── ReAct Prompt ─────────────────────────────────────────────────────────────
# Standard ReAct template with tool names/descriptions injected.
# llama3.1 works best with explicit step-by-step instructions.
REACT_PROMPT_TEMPLATE = """You are ResearchPilot, an expert AI research assistant.
You have access to the following tools:

{tools}

Always follow this reasoning format EXACTLY:

Question: the input question you must answer
Thought: think about what to do step by step
Action: the action to take, must be one of [{tool_names}]
Action Input: the input to the action (a plain string, no JSON)
Observation: the result of the action
... (this Thought/Action/Action Input/Observation can repeat up to 4 times)
Thought: I now know the final answer
Final Answer: your complete, well-formatted answer to the original question

Rules:
- ALWAYS start by using pdf_search to check the uploaded documents first.
- If pdf_search returns insufficient info, use web_search or wikipedia_search.
- Never make up information — only use what you observed from tools.
- Always cite your sources in the Final Answer.
- If no tool returns useful info, say so honestly.

Begin!

Question: {input}
Thought: {agent_scratchpad}"""

REACT_PROMPT = PromptTemplate.from_template(REACT_PROMPT_TEMPLATE)


# ────────────────────────────────────────────────────────────────────────────
# AgentManager — singleton that holds the agent executor
# ────────────────────────────────────────────────────────────────────────────
class AgentManager:
    """
    Manages the lifecycle of the ReAct agent.

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

    # ── Setup ────────────────────────────────────────────────────────────────
    def initialize(self, force_reindex: bool = False) -> str:
        """
        Load (or build) the vector store, wire up tools, create the agent.
        Returns a status message.
        """
        # 1. Load or build vector store
        if force_reindex or not vector_store_exists():
            status = "🔄 Indexing PDF documents..."
            self.vector_store = ingest()
        else:
            status = "📂 Loading existing vector store..."
            self.vector_store = load_vector_store()

        # 2. Inject retriever into the pdf_search tool
        retriever = get_retriever(self.vector_store)
        set_retriever(retriever)

        # 3. Build the LLM
        llm = ChatOllama(
            model=MODEL,
            base_url=BASE_URL,
            temperature=0.1,
            num_predict=2048,
        )

        # 4. Create the ReAct agent
        agent = create_react_agent(
            llm=llm,
            tools=ALL_TOOLS,
            prompt=REACT_PROMPT,
        )

        # 5. Wrap in an executor (handles the action loop)
        self.agent_executor = AgentExecutor(
            agent=agent,
            tools=ALL_TOOLS,
            verbose=True,           # prints Thought/Action/Observation to console
            max_iterations=6,       # safety cap — prevents infinite loops
            handle_parsing_errors=True,  # gracefully handle malformed LLM output
            return_intermediate_steps=True,
        )

        self.is_ready = True
        return f"✅ ResearchPilot ready! Using model: {MODEL}"

    # ── Query ────────────────────────────────────────────────────────────────
    def run(self, question: str) -> dict:
        """
        Run a question through the agent and return structured output.

        Returns:
            {
                "answer":       str,            # Final Answer from the agent
                "steps":        list[tuple],    # (action, observation) pairs
                "tools_used":   list[str],      # names of tools called
            }
        """
        if not self.is_ready:
            return {
                "answer": "⚠️ Agent not initialized. Please index documents first.",
                "steps":  [],
                "tools_used": [],
            }

        # Build chat history string for context (last 6 messages)
        history_str = self._format_history()

        result = self.agent_executor.invoke({
            "input": question if not history_str else
                     f"Previous conversation:\n{history_str}\n\nNew question: {question}",
        })

        # Extract intermediate steps
        steps      = result.get("intermediate_steps", [])
        tools_used = [step[0].tool for step in steps]
        answer     = result.get("output", "No answer generated.")

        # Store in chat history
        self.chat_history.append(HumanMessage(content=question))
        self.chat_history.append(AIMessage(content=answer))

        return {
            "answer":     answer,
            "steps":      steps,
            "tools_used": tools_used,
        }

    def reset_history(self) -> None:
        """Clear the conversation history."""
        self.chat_history = []

    def _format_history(self) -> str:
        """Format the last 6 messages as a readable string."""
        recent = self.chat_history[-6:]
        lines  = []
        for msg in recent:
            role = "User" if isinstance(msg, HumanMessage) else "Assistant"
            lines.append(f"{role}: {msg.content}")
        return "\n".join(lines)


# ── Standalone test ───────────────────────────────────────────────────────────
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
