import email
import os
import datetime
import hashlib

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

def init_rag():
    print("🔄 Initializing RAG pipeline...")

    embedder = Embedder()
    store = InMemoryVectorStore()
    vs_path = config.VECTOR_STORE_PATH

    if os.path.exists(vs_path):
        print(f"🔍 Found vector store at: {vs_path}")
        store.load(vs_path)
        print(f"✅ Loaded vector store with {len(store.ids)} documents.")
    else:
        print("📚 No vector store found — building index...")
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
    
    chat_history = ChatHistory(email)

    print("✅ All components initialized!")


def run_rag_pipeline(user_query: str, chat_history):
    """Used by android_server.py"""
    global EMBEDDER, VECTOR_STORE, RAG, LLM

    if EMBEDDER is None:
        return "System not initialized yet. Please wait 2 seconds and retry."

    user_query = user_query.strip()
    if not user_query:
        return "Empty query"

    chat_history.add_user(user_query)

    retrieved = RAG.retrieve(user_query, top_k=3)

    messages = build_messages(
        user_query,
        retrieved,
        chat_history.last_n(6),
        instruction=DEFAULT_INSTRUCTION,
    )
    LLm= LLMClient()
    answer = LLm.generate_response(messages)

    if not answer:
        return "LLM failed to generate a reply"

    chat_history.add_assistant(answer)

    return answer
