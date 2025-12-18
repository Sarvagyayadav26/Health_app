import email
import os
import datetime
import hashlib
import threading
import logging

from groq import Groq
from src.rag.embeddings import Embedder
from src.storage.vector_store import InMemoryVectorStore
from src.rag.indexer import Indexer
from src.rag.retriever import Retriever
from src.storage.chat_history import ChatHistory
from src.llm.prompts import build_messages
from src.llm.instruction_templates import DEFAULT_INSTRUCTION
from src.rag.doc_loader import load_text_documents
from src.llm.client import LLMClient
import src.utils.config as config

# GLOBAL placeholders (not initialized at import!)
EMBEDDER = None
VECTOR_STORE = None
RAG = None
LLM = None
chat_history = None

# Event to signal that startup/initialization has completed
INITIALIZED = threading.Event()
logger = logging.getLogger("backend")

def init_rag():
    logger.info("🔄 Initializing RAG pipeline...")

    embedder = Embedder()
    store = InMemoryVectorStore()
    vs_path = config.VECTOR_STORE_PATH

    if os.path.exists(vs_path):
        logger.info(f"Found vector store at: {vs_path}")
        store.load(vs_path)
        logger.info(f"Loaded vector store with {len(store.ids)} documents.")
    else:
        logger.info("No vector store found — building index...")
        docs = load_text_documents(config.DOCS_DIR)
        indexer = Indexer(embedder, store)
        indexer.index_documents(docs)
        store.save(vs_path)

    retriever = Retriever(embedder, store)
    return embedder, store, retriever

def initialize_all():
    """Called by FastAPI startup event."""
    global EMBEDDER, VECTOR_STORE, RAG, LLM, chat_history

    EMBEDDER, VECTOR_STORE, RAG = init_rag()

    # ✅ NEW: Initialize Groq client (IMPORTANT)
    GROQ_API_KEY = os.getenv("GROQ_API_KEY")
    if not GROQ_API_KEY:
        raise RuntimeError("🚨 GROQ_API_KEY is missing in environment variables!")

    LLM = Groq(api_key=GROQ_API_KEY)

    # Do not initialize ChatHistory at startup without a user email.
    chat_history = None

    logger.info("All components initialized")
    # Signal that initialization is complete so request threads can proceed
    try:
        INITIALIZED.set()
    except Exception:
        logger.exception("Failed to set INITIALIZED event")


def run_rag_pipeline(user_query: str, chat_history, history_msgs: list | None = None):
    """Used by android_server.py

    Args:
        user_query: current user message
        chat_history: ChatHistory instance for in-memory session messages
        history_msgs: optional list of dicts from DB [{"role","content","timestamp"}, ...]
    """
    global EMBEDDER, VECTOR_STORE, RAG, LLM

    # Wait briefly for initialization to complete (non-blocking for long waits)
    try:
        # If initialization hasn't completed, wait up to 5 seconds for it.
        # This avoids returning immediately when startup is still in progress.
        if not INITIALIZED.wait(timeout=5):
            return "System not initialized yet. Please retry shortly."
    except Exception:
        # Fallback: if the wait call fails, still check the EMBEDDER as a guard
        if EMBEDDER is None:
            return "System not initialized yet. Please retry shortly."

    user_query = user_query.strip()
    if not user_query:
        return "Empty query"

    # append current user message to in-memory history
    try:
        chat_history.add_user(user_query)
    except Exception:
        logger.debug("chat_history.add_user failed; continuing without in-memory add", exc_info=True)

    retrieved = RAG.retrieve(user_query, top_k=3)

    # Debug: log retrieved documents count and snippets
    try:
        logger.debug("[run_rag_pipeline] retrieved_count=%s", len(retrieved) if retrieved else 0)
        if retrieved:
            for i, d in enumerate(retrieved[:3]):
                try:
                    if isinstance(d, dict):
                        text = d.get('text', '')
                        meta = d.get('metadata', {})
                    else:
                        # defensive: try attribute access
                        text = getattr(d, 'text', '')
                        meta = getattr(d, 'metadata', {})
                    logger.debug("[run_rag_pipeline] retrieved[%d] meta=%s snippet=%s", i, meta, text[:120])
                except Exception:
                    logger.debug("Failed to parse retrieved doc", exc_info=True)
                    continue
    except Exception:
        logger.exception("Error while logging retrieved docs")

    # Debug: incoming history sizes
    try:
        logger.debug("[run_rag_pipeline] incoming_history_msgs=%s", len(history_msgs) if history_msgs else 0)
    except Exception:
        logger.exception("Error computing incoming_history_msgs")

    # Build combined history: DB-persisted messages first, then recent in-memory messages
    from src.utils import config
    combined_history = []
    if history_msgs:
        # expect history_msgs as list of dicts with keys 'role' and 'content'
        for m in history_msgs:
            try:
                combined_history.append({"role": m.get("role", "user"), "content": m.get("content", "")})
            except Exception:
                logger.debug("Skipping malformed history message: %s", m, exc_info=True)
                continue

    try:
        in_memory = chat_history.last_n(config.CHAT_HISTORY_WINDOW)
        in_memory_count = len(in_memory) if in_memory else 0
        logger.debug("[run_rag_pipeline] in_memory_count=%s", in_memory_count)
        if in_memory:
            combined_history.extend(in_memory)
    except Exception:
        logger.debug("Failed to retrieve in-memory history", exc_info=True)

    # Log combined history size along with DB vs in-memory contribution
    try:
        db_count = len(history_msgs) if history_msgs else 0
        in_memory_count = len(in_memory) if 'in_memory' in locals() and in_memory else 0
        logger.debug("[run_rag_pipeline] combined_history_count=%s (db=%s in_memory=%s)",
                     len(combined_history), db_count, in_memory_count)
    except Exception:
        logger.exception("Failed to log combined_history_count")

    # Deduplicate combined history while preserving order. This avoids sending
    # duplicate messages to the LLM when the same message exists in both the
    # DB-persisted history and the in-memory session history.
    try:
        seen = set()
        unique_combined = []
        for m in combined_history:
            role = m.get("role") if isinstance(m, dict) else None
            content = (m.get("content") if isinstance(m, dict) else str(m)) or ""
            key = (role, content.strip())
            if key not in seen:
                seen.add(key)
                unique_combined.append(m)
        combined_history = unique_combined
        logger.debug("[run_rag_pipeline] deduped_combined_history_count=%s", len(combined_history))
    except Exception:
        logger.exception("Failed to deduplicate combined_history")

    messages = build_messages(
        user_query,
        retrieved,
        combined_history,
        instruction=DEFAULT_INSTRUCTION,
    )

    llm_client = LLMClient()
    answer = llm_client.generate_response(messages)

    if not answer:
        return "LLM failed to generate a reply"

    try:
        chat_history.add_assistant(answer)
    except Exception:
        logger.debug("chat_history.add_assistant failed; continuing", exc_info=True)

    return answer
