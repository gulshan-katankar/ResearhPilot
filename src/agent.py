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
# llama3.1 (8B) fails with complex prompts — it writes "Action:" then forgets
# "Action Input:", causing parse loops.  Fix:
#   1. Ultra-minimal format section
#   2. ONE concrete few-shot example showing the full loop
#   3. No extra "Rules" block that adds tokens between format and scratchpad
REACT_PROMPT_TEMPLATE = """You are ResearchPilot, a helpful research assistant.
Answer the user's question using the tools below.

Tools available:
{tools}

You MUST respond using this EXACT format and nothing else:

Thought: <your reasoning>
Action: <one of [{tool_names}]>
Action Input: <plain text input to the tool>
Observation: <tool result will appear here>
... repeat Thought/Action/Action Input/Observation as needed ...
Thought: I now have enough information to answer.
Final Answer: <your complete answer>

Example of correct format:
Thought: The user is asking about transformers. Let me check the PDFs first.
Action: pdf_search
Action Input: transformer architecture
Observation: [Excerpt 1] Source: paper.pdf, Page 3 — Transformers use self-attention...
Thought: I found a relevant passage. I can now answer.
Final Answer: According to the uploaded paper (page 3), transformers use self-attention mechanisms...

Important rules:
- Always start with pdf_search.
- After each Observation, write a new Thought before the next Action or Final Answer.
- Never skip Action Input after Action.
- When you have enough information, write "Final Answer:" and stop.

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
        # Note: do NOT pass stop=["Observation:"] here — langchain-ollama
        # already injects stop sequences internally via the ReAct prompt,
        # and passing it again raises "stop found in both input and default params".
        llm = ChatOllama(
            model=MODEL,
            base_url=BASE_URL,
            temperature=0,      # most deterministic — best for strict format adherence
            num_predict=1024,
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
            verbose=True,
            max_iterations=6,
            # Provide a helpful re-prompt when parsing fails instead of empty string
            handle_parsing_errors=(
                "Output format was incorrect. You MUST respond with:\n"
                "Thought: <reasoning>\n"
                "Action: <tool name>\n"
                "Action Input: <query>\n"
                "or end with: Final Answer: <answer>"
            ),
            return_intermediate_steps=True,
        )

        self.is_ready = True
        return f"Agent ready! Model: {MODEL}"

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
        answer     = result.get("output", "")

        # ── Fallback: if agent hit iteration limit, synthesise from observations ──
        # llama3.1 sometimes can't write "Final Answer:" on its own after tool calls.
        # We detect the failure and build an answer from what the tools returned.
        FAILURE_PHRASES = [
            "agent stopped due to iteration limit",
            "agent stopped due to time limit",
            "no answer generated",
        ]
        if not answer or any(p in answer.lower() for p in FAILURE_PHRASES):
            if steps:
                # Collect all non-empty observations from tool calls
                obs_parts = []
                for action, observation in steps:
                    if observation and str(observation).strip():
                        obs_parts.append(
                            f"[From {action.tool}]:\n{str(observation)[:800]}"
                        )
                if obs_parts:
                    answer = (
                        "Based on the information retrieved from your documents:\n\n"
                        + "\n\n---\n\n".join(obs_parts)
                    )
                else:
                    answer = "I could not find a relevant answer in the documents or the web for your question."
            else:
                answer = "I could not find a relevant answer. Please try rephrasing your question."

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
