"""
ResearchPilot — Premium Chat UI
Completely redesigned: glassmorphism, avatars, animated elements,
suggested prompts, proper markdown rendering, and polished sidebar.
"""

import sys

# ── Windows UTF-8 fix ─────────────────────────────────────────────────────────
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

import os
from pathlib import Path
from dotenv import load_dotenv
import streamlit as st

from src.agent import AgentManager
from src.ingest import vector_store_exists, PDF_DIR

load_dotenv()

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="ResearchPilot · AI Research Assistant",
    page_icon="🔬",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── CSS ───────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

/* ══════════════════════ BASE ══════════════════════ */
*, *::before, *::after { box-sizing: border-box; }

html, body, [class*="css"] {
    font-family: 'Inter', sans-serif !important;
}

.stApp {
    background: #060818;
    background-image:
        radial-gradient(ellipse 80% 60% at 20% -10%, rgba(59,130,246,0.12) 0%, transparent 60%),
        radial-gradient(ellipse 60% 50% at 80% 110%, rgba(139,92,246,0.10) 0%, transparent 60%);
    min-height: 100vh;
}

/* Hide streamlit default elements */
#MainMenu, footer, header { visibility: hidden; }
.block-container { padding-top: 1.5rem !important; padding-bottom: 0 !important; }

/* ══════════════════════ SIDEBAR ══════════════════════ */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0b0f1e 0%, #080c18 100%) !important;
    border-right: 1px solid rgba(255,255,255,0.06) !important;
    padding: 0 !important;
}
[data-testid="stSidebar"] > div:first-child {
    padding: 0;
}

.sidebar-logo {
    padding: 24px 20px 20px;
    border-bottom: 1px solid rgba(255,255,255,0.06);
    margin-bottom: 16px;
}
.sidebar-logo h2 {
    margin: 0;
    font-size: 1.3rem;
    font-weight: 800;
    letter-spacing: -0.02em;
    background: linear-gradient(135deg, #60a5fa, #a78bfa);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
}
.sidebar-logo p {
    margin: 4px 0 0 0;
    font-size: 0.72rem;
    color: #6b7280;         /* was #4b5563 — now readable */
    letter-spacing: 0.06em;
    text-transform: uppercase;
}

/* Status pill */
.status-pill {
    display: inline-flex;
    align-items: center;
    gap: 7px;
    padding: 5px 14px;
    border-radius: 99px;
    font-size: 0.75rem;
    font-weight: 600;
    letter-spacing: 0.03em;
}
.status-ready {
    background: rgba(34,197,94,0.1);
    border: 1px solid rgba(34,197,94,0.25);
    color: #4ade80;
}
.status-ready::before {
    content: '';
    display: block;
    width: 7px; height: 7px;
    border-radius: 50%;
    background: #4ade80;
    box-shadow: 0 0 8px #4ade80;
    animation: pulse-green 2s infinite;
}
.status-offline {
    background: rgba(251,191,36,0.08);
    border: 1px solid rgba(251,191,36,0.2);
    color: #fbbf24;
}
.status-offline::before {
    content: '';
    display: block;
    width: 7px; height: 7px;
    border-radius: 50%;
    background: #fbbf24;
}
@keyframes pulse-green {
    0%, 100% { box-shadow: 0 0 4px #4ade80; }
    50%       { box-shadow: 0 0 12px #4ade80, 0 0 20px rgba(74,222,128,0.3); }
}

/* Sidebar sections */
.sb-section {
    padding: 0 16px;
    margin-bottom: 8px;
}
.sb-label {
    font-size: 0.68rem;
    font-weight: 700;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    color: #6b7280;         /* was #374151 — now visible */
    margin-bottom: 8px;
    padding: 0 4px;
}

/* File cards */
.file-card {
    display: flex;
    align-items: center;
    gap: 10px;
    background: rgba(255,255,255,0.03);
    border: 1px solid rgba(255,255,255,0.06);
    border-radius: 10px;
    padding: 9px 12px;
    margin-bottom: 6px;
}
.file-icon {
    font-size: 1.1rem;
    flex-shrink: 0;
}
.file-name {
    font-size: 0.78rem;
    color: #9ca3af;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}

/* Tool cards */
.tool-card {
    display: flex;
    align-items: flex-start;
    gap: 10px;
    padding: 10px 12px;
    border-radius: 10px;
    background: rgba(255,255,255,0.02);
    border: 1px solid rgba(255,255,255,0.05);
    margin-bottom: 6px;
}
.tool-icon-wrap {
    width: 28px; height: 28px;
    border-radius: 8px;
    display: flex; align-items: center; justify-content: center;
    font-size: 0.9rem;
    flex-shrink: 0;
}
.ti-pdf   { background: rgba(96,165,250,0.15); }
.ti-web   { background: rgba(52,211,153,0.15); }
.ti-wiki  { background: rgba(167,139,250,0.15); }
.tool-info-name {
    font-size: 0.78rem;
    font-weight: 600;
    color: #e5e7eb;
    line-height: 1;
    margin-bottom: 2px;
}
.tool-info-desc {
    font-size: 0.7rem;
    color: #9ca3af;         /* was #4b5563 — now readable */
    line-height: 1.3;
}

/* ══════════════════════ HEADER ══════════════════════ */
.main-header {
    position: relative;
    overflow: hidden;
    background: linear-gradient(135deg,
        rgba(30,41,59,0.8) 0%,
        rgba(15,23,42,0.9) 100%);
    border: 1px solid rgba(255,255,255,0.07);
    border-radius: 18px;
    padding: 22px 32px;
    margin-bottom: 20px;
    backdrop-filter: blur(20px);
}
.main-header::before {
    content: '';
    position: absolute;
    inset: 0;
    background: linear-gradient(135deg,
        rgba(59,130,246,0.08) 0%,
        rgba(139,92,246,0.05) 50%,
        transparent 100%);
    pointer-events: none;
}
.header-inner {
    position: relative;
    display: flex;
    align-items: center;
    justify-content: space-between;
}
.header-title {
    margin: 0;
    font-size: 1.75rem;
    font-weight: 800;
    letter-spacing: -0.03em;
    background: linear-gradient(135deg, #93c5fd, #c4b5fd, #93c5fd);
    background-size: 200% auto;
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    animation: shimmer 4s linear infinite;
}
@keyframes shimmer {
    0%   { background-position: 0% center; }
    100% { background-position: 200% center; }
}
.header-subtitle {
    margin: 4px 0 0 0;
    font-size: 0.83rem;
    color: #4b5563;
    font-weight: 400;
}
.header-badge {
    display: flex;
    align-items: center;
    gap: 6px;
    padding: 6px 14px;
    border-radius: 99px;
    background: rgba(99,102,241,0.12);
    border: 1px solid rgba(99,102,241,0.25);
    font-size: 0.72rem;
    font-weight: 600;
    color: #a5b4fc;
    letter-spacing: 0.04em;
    white-space: nowrap;
}

/* ══════════════════════ CHAT AREA ══════════════════════ */
.chat-wrap {
    display: flex;
    flex-direction: column;
    gap: 6px;
    padding-bottom: 12px;
}

/* User bubble */
.msg-user {
    display: flex;
    justify-content: flex-end;
    align-items: flex-end;
    gap: 10px;
    margin: 4px 0;
    animation: slide-in-right 0.25s ease;
}
@keyframes slide-in-right {
    from { opacity: 0; transform: translateX(16px); }
    to   { opacity: 1; transform: translateX(0); }
}
.msg-user .bubble {
    max-width: 70%;
    background: linear-gradient(135deg, #2563eb, #4f46e5);
    border-radius: 18px 18px 4px 18px;
    padding: 12px 18px;
    font-size: 0.88rem;
    color: #e0e7ff;
    line-height: 1.6;
    box-shadow: 0 4px 20px rgba(37,99,235,0.3);
}
.avatar {
    width: 32px; height: 32px;
    border-radius: 50%;
    display: flex; align-items: center; justify-content: center;
    font-size: 0.9rem;
    flex-shrink: 0;
}
.avatar-user { background: linear-gradient(135deg, #2563eb, #4f46e5); }
.avatar-bot  { background: linear-gradient(135deg, #0f172a, #1e293b);
               border: 1px solid rgba(99,179,237,0.2); }

/* Bot bubble */
.msg-bot {
    display: flex;
    justify-content: flex-start;
    align-items: flex-end;
    gap: 10px;
    margin: 4px 0;
    animation: slide-in-left 0.25s ease;
}
@keyframes slide-in-left {
    from { opacity: 0; transform: translateX(-16px); }
    to   { opacity: 1; transform: translateX(0); }
}
.msg-bot .bubble {
    max-width: 75%;
    background: linear-gradient(135deg,
        rgba(30,41,59,0.95) 0%,
        rgba(15,23,42,0.95) 100%);
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 18px 18px 18px 4px;
    padding: 14px 18px;
    font-size: 0.88rem;
    color: #cbd5e1;
    line-height: 1.7;
    box-shadow: 0 4px 24px rgba(0,0,0,0.4);
    backdrop-filter: blur(10px);
}
.bot-label {
    font-size: 0.65rem;
    font-weight: 700;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: #60a5fa;
    margin-bottom: 6px;
}

/* Tool chips */
.chips-row {
    display: flex;
    flex-wrap: wrap;
    gap: 5px;
    margin-top: 10px;
    padding-top: 10px;
    border-top: 1px solid rgba(255,255,255,0.05);
}
.chip {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    padding: 3px 10px;
    border-radius: 99px;
    font-size: 0.68rem;
    font-weight: 600;
    letter-spacing: 0.03em;
}
.chip-pdf  { background: rgba(96,165,250,0.12); border: 1px solid rgba(96,165,250,0.25); color: #93c5fd; }
.chip-web  { background: rgba(52,211,153,0.12); border: 1px solid rgba(52,211,153,0.25); color: #6ee7b7; }
.chip-wiki { background: rgba(167,139,250,0.12); border: 1px solid rgba(167,139,250,0.25); color: #c4b5fd; }
.chip-other{ background: rgba(148,163,184,0.10); border: 1px solid rgba(148,163,184,0.2); color: #94a3b8; }

/* Reasoning steps */
.steps-wrap {
    margin-top: 10px;
    padding-top: 10px;
    border-top: 1px solid rgba(255,255,255,0.05);
}
.step-item {
    background: rgba(0,0,0,0.2);
    border-left: 2px solid rgba(99,102,241,0.4);
    border-radius: 0 8px 8px 0;
    padding: 8px 12px;
    margin: 5px 0;
    font-size: 0.75rem;
}
.step-tool  { color: #a5b4fc; font-weight: 700; margin-bottom: 3px; }
.step-input { color: #6b7280; margin-bottom: 4px; }
.step-obs   { color: #34d399; max-height: 80px; overflow-y: auto; white-space: pre-wrap; }

/* ══════════════════════ WELCOME SCREEN ══════════════════════ */
.welcome-wrap {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    padding: 60px 20px;
    text-align: center;
}
.welcome-icon {
    font-size: 3.5rem;
    margin-bottom: 16px;
    animation: float 3s ease-in-out infinite;
}
@keyframes float {
    0%, 100% { transform: translateY(0); }
    50%       { transform: translateY(-8px); }
}
.welcome-title {
    font-size: 1.4rem;
    font-weight: 700;
    color: #e2e8f0;
    margin-bottom: 8px;
    letter-spacing: -0.02em;
}
.welcome-sub {
    font-size: 0.85rem;
    color: #4b5563;
    max-width: 420px;
    line-height: 1.6;
    margin-bottom: 32px;
}
.suggestions-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 10px;
    max-width: 560px;
    width: 100%;
}
.suggestion-card {
    background: rgba(255,255,255,0.03);
    border: 1px solid rgba(255,255,255,0.07);
    border-radius: 12px;
    padding: 14px 16px;
    text-align: left;
    cursor: pointer;
    transition: all 0.2s ease;
}
.suggestion-card:hover {
    background: rgba(59,130,246,0.08);
    border-color: rgba(59,130,246,0.25);
    transform: translateY(-2px);
}
.sug-icon { font-size: 1.2rem; margin-bottom: 6px; }
.sug-text { font-size: 0.78rem; color: #9ca3af; line-height: 1.4; }

/* ══════════════════════ INPUT AREA FOOTER ══════════════════════ */
/* The button is position:absolute inside a position:relative wrapper.
   Only override background/border-radius on wrappers — don't touch
   display/flex/position which breaks the native Streamlit layout. */

[data-testid="stBottom"] {
    background: #060818 !important;
    border-top: 1px solid rgba(255,255,255,0.05) !important;
    padding: 8px 16px !important;
    border-radius: 0 !important;
}

/* Kill white bg/radius on wrapper divs — only bg and radius, nothing else */
[data-testid="stBottom"] div,
[data-testid="stChatInput"] div,
[data-testid="stChatInput"] form {
    background: #060818 !important;
    border-radius: 0 !important;
}

/* The direct wrapper inside stChatInput is position:relative and holds the
   absolute-positioned button — give it matching border-radius + overflow:hidden
   so the textarea corners don't bleed grey outside the rounded clip */
[data-testid="stChatInput"] > div {
    border-radius: 14px !important;
    overflow: hidden !important;
    position: relative !important;
}

/* ── Textarea ── */
[data-testid="stChatInputTextArea"] {
    background: rgba(15,23,42,0.9) !important;
    border: 1px solid rgba(255,255,255,0.12) !important;
    border-radius: 14px !important;
    color: #e2e8f0 !important;
    font-family: 'Inter', sans-serif !important;
    font-size: 0.9rem !important;
    padding: 12px 36px 12px 16px !important;  /* right padding tucked tight */
    caret-color: #60a5fa !important;
    resize: none !important;
    overflow: hidden !important;   /* hides native scrollbar track = no grey strip */
    width: 100% !important;
    box-sizing: border-box !important;
    transition: border-color 0.2s !important;
}
[data-testid="stChatInputTextArea"]:focus {
    border-color: rgba(96,165,250,0.5) !important;
    box-shadow: 0 0 0 3px rgba(96,165,250,0.1) !important;
    outline: none !important;
}
[data-testid="stChatInputTextArea"]::placeholder {
    color: #94a3b8 !important;
}

/* ── Send button — transparent arrow icon, vertically centered via absolute pos ── */
[data-testid="stChatInputSubmitButton"] {
    background: transparent !important;
    border: none !important;
    border-radius: 0 !important;
    box-shadow: none !important;
    outline: none !important;
    position: absolute !important;
    right: 6px !important;
    top: 50% !important;
    bottom: auto !important;
    transform: translateY(-50%) !important;
    width: 28px !important;
    height: 28px !important;
    padding: 0 !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    opacity: 0.65 !important;
    transition: opacity 0.2s, transform 0.2s !important;
    cursor: pointer !important;
}
[data-testid="stChatInputSubmitButton"]:hover {
    background: transparent !important;
    box-shadow: none !important;
    opacity: 1 !important;
    transform: translateY(-50%) scale(1.15) !important;
}
[data-testid="stChatInputSubmitButton"] svg {
    display: block !important;
    width: 18px !important;
    height: 18px !important;
    fill: #60a5fa !important;
    color: #60a5fa !important;
}

/* ══════════════════════ BUTTONS ══════════════════════ */
.stButton > button {
    background: linear-gradient(135deg, rgba(37,99,235,0.8), rgba(79,70,229,0.8)) !important;
    color: white !important;
    border: 1px solid rgba(96,165,250,0.2) !important;
    border-radius: 10px !important;
    font-family: 'Inter', sans-serif !important;
    font-weight: 600 !important;
    font-size: 0.82rem !important;
    transition: all 0.2s ease !important;
    width: 100%;
    backdrop-filter: blur(10px);
}
.stButton > button:hover {
    background: linear-gradient(135deg, rgba(59,130,246,0.9), rgba(99,102,241,0.9)) !important;
    box-shadow: 0 4px 20px rgba(37,99,235,0.35) !important;
    transform: translateY(-1px) !important;
    border-color: rgba(96,165,250,0.35) !important;
}
.stButton > button:active { transform: translateY(0) !important; }

/* Danger button (clear chat) */
.danger-btn > button {
    background: rgba(239,68,68,0.08) !important;
    border-color: rgba(239,68,68,0.2) !important;
    color: #f87171 !important;
}
.danger-btn > button:hover {
    background: rgba(239,68,68,0.15) !important;
    box-shadow: 0 4px 20px rgba(239,68,68,0.2) !important;
}

/* ══════════════════════ FILE UPLOADER ══════════════════════ */
[data-testid="stFileUploader"] {
    background: rgba(15,23,42,0.6) !important;
    border: 1px dashed rgba(96,165,250,0.25) !important;
    border-radius: 12px !important;
}
[data-testid="stFileUploader"] > div {
    background: rgba(15,23,42,0.6) !important;
    border-radius: 12px !important;
}
/* The inner white drop zone */
[data-testid="stFileUploaderDropzoneInstructions"],
[data-testid="stFileUploaderDropzone"] {
    background: transparent !important;
    color: #6b7280 !important;
}
[data-testid="stFileUploader"] small,
[data-testid="stFileUploader"] span,
[data-testid="stFileUploader"] p {
    color: #9ca3af !important;  /* was #4b5563 — now visible */
}
[data-testid="stFileUploader"] button {
    background: rgba(30,41,59,0.8) !important;
    border: 1px solid rgba(255,255,255,0.1) !important;
    color: #94a3b8 !important;
    border-radius: 8px !important;
    font-size: 0.8rem !important;
}
[data-testid="stFileUploader"] button:hover {
    background: rgba(37,99,235,0.2) !important;
    border-color: rgba(96,165,250,0.3) !important;
    color: #93c5fd !important;
}

/* ══════════════════════ SIDEBAR TOGGLE BUTTON ══════════════════════ */
/* Style the collapse/expand button without overriding its position */
[data-testid="stSidebarCollapseButton"] button,
[data-testid="collapsedControl"] button {
    background: rgba(30,41,59,0.9) !important;
    border: 1px solid rgba(96,165,250,0.35) !important;
    border-radius: 10px !important;
    width: 34px !important;
    height: 34px !important;
    box-shadow: 0 2px 12px rgba(0,0,0,0.4) !important;
    transition: all 0.2s ease !important;
}
[data-testid="stSidebarCollapseButton"] button:hover,
[data-testid="collapsedControl"] button:hover {
    background: rgba(37,99,235,0.25) !important;
    border-color: rgba(96,165,250,0.65) !important;
    box-shadow: 0 4px 20px rgba(37,99,235,0.3) !important;
    transform: scale(1.06) !important;
}
/* Hide the default SVG arrow and inject ☰ */
[data-testid="stSidebarCollapseButton"] button svg,
[data-testid="collapsedControl"] button svg {
    display: none !important;
}
[data-testid="stSidebarCollapseButton"] button::after,
[data-testid="collapsedControl"] button::after {
    content: '☰';
    font-size: 0.9rem;
    color: #60a5fa;
    line-height: 1;
    display: block;
}
::-webkit-scrollbar { width: 4px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.08); border-radius: 4px; }
::-webkit-scrollbar-thumb:hover { background: rgba(255,255,255,0.15); }

.st-expander {
    background: rgba(0,0,0,0.2) !important;
    border: 1px solid rgba(255,255,255,0.06) !important;
    border-radius: 10px !important;
}

/* Info/success/error boxes */
[data-testid="stAlert"] {
    border-radius: 10px !important;
    font-size: 0.82rem !important;
}

/* Divider */
hr { border-color: rgba(255,255,255,0.05) !important; margin: 12px 0 !important; }
</style>
""", unsafe_allow_html=True)


# ── Session state ─────────────────────────────────────────────────────────────
if "agent_manager" not in st.session_state:
    st.session_state.agent_manager = AgentManager()
if "messages" not in st.session_state:
    st.session_state.messages = []
if "agent_ready" not in st.session_state:
    st.session_state.agent_ready = False
if "indexed_files" not in st.session_state:
    st.session_state.indexed_files = []
if "pending_prompt" not in st.session_state:
    st.session_state.pending_prompt = None


# ── Helpers ───────────────────────────────────────────────────────────────────
TOOL_META = {
    "pdf_search":       ("📄", "PDF Search",  "chip-pdf"),
    "web_search":       ("🌐", "Web Search",  "chip-web"),
    "wikipedia_search": ("📖", "Wikipedia",   "chip-wiki"),
}

def chip_html(tool_name: str) -> str:
    icon, label, cls = TOOL_META.get(tool_name, ("🛠", tool_name, "chip-other"))
    return f'<span class="chip {cls}">{icon} {label}</span>'

def render_message(msg: dict):
    role = msg["role"]
    content = msg["content"]
    tools  = msg.get("tools", [])
    steps  = msg.get("steps", [])

    if role == "user":
        st.markdown(f"""
        <div class="msg-user">
            <div class="bubble">{content}</div>
            <div class="avatar avatar-user">🧑</div>
        </div>""", unsafe_allow_html=True)
    else:
        chips = "".join(chip_html(t) for t in tools) if tools else ""
        chips_row = f'<div class="chips-row">{chips}</div>' if chips else ""

        st.markdown(f"""
        <div class="msg-bot">
            <div class="avatar avatar-bot">🔬</div>
            <div class="bubble">
                <div class="bot-label">ResearchPilot</div>
                {content}
                {chips_row}
            </div>
        </div>""", unsafe_allow_html=True)

        if steps:
            with st.expander("🧠 Agent Reasoning", expanded=False):
                for i, (action, observation) in enumerate(steps, 1):
                    icon, label, _ = TOOL_META.get(action.tool, ("🛠", action.tool, ""))
                    obs_preview = str(observation)[:500] + ("…" if len(str(observation)) > 500 else "")
                    st.markdown(f"""
                    <div class="step-item">
                        <div class="step-tool">{icon} Step {i} — {label}</div>
                        <div class="step-input">Query: <code>{action.tool_input}</code></div>
                        <div class="step-obs">{obs_preview}</div>
                    </div>""", unsafe_allow_html=True)


# ── SIDEBAR ───────────────────────────────────────────────────────────────────
with st.sidebar:
    # Logo
    st.markdown("""
    <div class="sidebar-logo">
        <h2>🔬 ResearchPilot</h2>
        <p>AI · Local · Private</p>
    </div>""", unsafe_allow_html=True)

    # Status
    st.markdown('<div class="sb-section">', unsafe_allow_html=True)
    if st.session_state.agent_ready:
        st.markdown('<span class="status-pill status-ready">Agent Ready</span>',
                    unsafe_allow_html=True)
    else:
        st.markdown('<span class="status-pill status-offline">Not Initialized</span>',
                    unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("<hr>", unsafe_allow_html=True)

    # PDF Upload
    st.markdown('<div class="sb-section"><div class="sb-label">Upload Documents</div>', unsafe_allow_html=True)
    uploaded = st.file_uploader(
        "Drop PDFs here",
        type=["pdf"],
        accept_multiple_files=True,
        label_visibility="collapsed",
    )
    if uploaded:
        PDF_DIR.mkdir(parents=True, exist_ok=True)
        saved = []
        for f in uploaded:
            dest = PDF_DIR / f.name
            with open(dest, "wb") as out:
                out.write(f.read())
            saved.append(f.name)
        if saved:
            st.session_state.indexed_files = saved
            st.success(f"Saved {len(saved)} file(s)")
    st.markdown('</div>', unsafe_allow_html=True)

    # Show saved files
    if st.session_state.indexed_files:
        st.markdown('<div class="sb-section">', unsafe_allow_html=True)
        for fname in st.session_state.indexed_files[:5]:
            short = fname if len(fname) < 28 else fname[:25] + "…"
            st.markdown(f"""
            <div class="file-card">
                <span class="file-icon">📄</span>
                <span class="file-name">{short}</span>
            </div>""", unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("<hr>", unsafe_allow_html=True)

    # Index buttons
    st.markdown('<div class="sb-section"><div class="sb-label">Index & Load</div>', unsafe_allow_html=True)
    col1, col2 = st.columns(2)
    with col1:
        index_btn = st.button("⚡ Index", use_container_width=True, key="index")
    with col2:
        reindex_btn = st.button("🔄 Re-index", use_container_width=True, key="reindex")

    if index_btn or reindex_btn:
        with st.spinner("Indexing documents…"):
            try:
                status = st.session_state.agent_manager.initialize(
                    force_reindex=bool(reindex_btn)
                )
                st.session_state.agent_ready = True
                st.success("Ready!")
            except FileNotFoundError as e:
                st.error(str(e))
            except Exception as e:
                st.error(f"Failed: {e}")
    st.markdown('</div>', unsafe_allow_html=True)

    # Auto-load
    if not st.session_state.agent_ready and vector_store_exists():
        with st.spinner("Loading index…"):
            try:
                st.session_state.agent_manager.initialize(force_reindex=False)
                st.session_state.agent_ready = True
                st.rerun()
            except Exception:
                pass

    st.markdown("<hr>", unsafe_allow_html=True)

    # Tools legend
    st.markdown('<div class="sb-section"><div class="sb-label">Available Tools</div>', unsafe_allow_html=True)
    tools_html = """
    <div class="tool-card">
        <div class="tool-icon-wrap ti-pdf">📄</div>
        <div><div class="tool-info-name">PDF Search</div>
             <div class="tool-info-desc">Searches your uploaded documents</div></div>
    </div>
    <div class="tool-card">
        <div class="tool-icon-wrap ti-web">🌐</div>
        <div><div class="tool-info-name">Web Search</div>
             <div class="tool-info-desc">Live results via DuckDuckGo</div></div>
    </div>
    <div class="tool-card">
        <div class="tool-icon-wrap ti-wiki">📖</div>
        <div><div class="tool-info-name">Wikipedia</div>
             <div class="tool-info-desc">Encyclopedic background facts</div></div>
    </div>"""
    st.markdown(tools_html, unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("<hr>", unsafe_allow_html=True)

    # Model info
    st.markdown(f"""
    <div class="sb-section">
        <div class="sb-label">Model</div>
        <div class="file-card">
            <span class="file-icon">⚡</span>
            <span class="file-name">gemini-2.5-flash · Google Gemini</span>
        </div>
    </div>""", unsafe_allow_html=True)

    # Clear chat
    st.markdown('<div class="sb-section" style="margin-top:8px;">', unsafe_allow_html=True)
    st.markdown('<div class="danger-btn">', unsafe_allow_html=True)
    if st.button("🗑 Clear Chat", use_container_width=True, key="clear"):
        st.session_state.messages = []
        st.session_state.agent_manager.reset_history()
        st.rerun()
    st.markdown('</div></div>', unsafe_allow_html=True)


# ── MAIN ─────────────────────────────────────────────────────────────────────
# Header
model_label = "gemini-2.5-flash · Google Gemini"
st.markdown(f"""
<div class="main-header">
    <div class="header-inner">
        <div>
            <h1 class="header-title">🔬 ResearchPilot</h1>
            <p class="header-subtitle">
                Ask questions across your research PDFs · powered by local AI · no data leaves your machine
            </p>
        </div>
        <div class="header-badge">⚡ {model_label}</div>
    </div>
</div>""", unsafe_allow_html=True)

# Chat area
if not st.session_state.messages:
    # Welcome / suggestion screen
    st.markdown("""
    <div class="welcome-wrap">
        <div class="welcome-icon">🔬</div>
        <div class="welcome-title">What do you want to explore?</div>
        <div class="welcome-sub">
            Upload your research PDFs, index them, and ask anything.
            The agent searches your documents first, then the web if needed.
        </div>
        <div class="suggestions-grid">
            <div class="suggestion-card">
                <div class="sug-icon">📋</div>
                <div class="sug-text">Summarize the main findings of the uploaded papers</div>
            </div>
            <div class="suggestion-card">
                <div class="sug-icon">🔍</div>
                <div class="sug-text">What methods are compared in these papers?</div>
            </div>
            <div class="suggestion-card">
                <div class="sug-icon">📊</div>
                <div class="sug-text">What are the key results and benchmarks?</div>
            </div>
            <div class="suggestion-card">
                <div class="sug-icon">🌐</div>
                <div class="sug-text">Search the web for the latest related research</div>
            </div>
        </div>
    </div>""", unsafe_allow_html=True)
else:
    st.markdown('<div class="chat-wrap">', unsafe_allow_html=True)
    for msg in st.session_state.messages:
        render_message(msg)
    st.markdown('</div>', unsafe_allow_html=True)

# Chat input
if not st.session_state.agent_ready:
    st.info("👈 Upload PDFs and click **⚡ Index** in the sidebar to get started.", icon="ℹ️")

if prompt := st.chat_input(
    "Ask anything about your research…" if st.session_state.agent_ready else "Initialize the agent first…",
    disabled=not st.session_state.agent_ready,
):
    st.session_state.messages.append({"role": "user", "content": prompt})

    with st.spinner("Thinking…"):
        try:
            result     = st.session_state.agent_manager.run(prompt)
            answer     = result["answer"]
            tools_used = result["tools_used"]
            steps      = result["steps"]
        except Exception as e:
            answer     = f"❌ An error occurred: {e}"
            tools_used = []
            steps      = []

    st.session_state.messages.append({
        "role":    "assistant",
        "content": answer,
        "tools":   tools_used,
        "steps":   steps,
    })
    st.rerun()
