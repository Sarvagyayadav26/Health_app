def safe_save(email, role, content, session_id):
    try:
        save_message(email, role, content, session_id)
    except Exception:
        pass
"""
UNIFIED SERVER - Internal Testing & Android Production

This server works for both internal testing and Android production.
Use the configuration section below to switch between modes.

CONFIGURATION:
- For INTERNAL TESTING: Set DEPLOYMENT_MODE = "testing"
- For ANDROID PRODUCTION: Set DEPLOYMENT_MODE = "android"
"""

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel
from typing import Optional, Union
import time
import logging
import bcrypt
import re
import random
from sqlite3 import IntegrityError
import sqlite3
import src.utils.config as config

from src.storage.chat_history import ChatHistory
from src.storage.user_db import (
    init_db, create_user, get_user, save_message,
    increment_usage, get_usage_stats, add_chats, get_messages, DB_PATH,
    is_purchase_token_processed, mark_purchase_token_processed, list_processed_purchases,
    hide_history, is_history_hidden
)
from src.payments import google_play
from src.llm.instruction_templates import DEFAULT_INSTRUCTION

# ======================================================================
# 🔧 CONFIGURATION - CHANGE THIS FOR TESTING VS PRODUCTION
# ======================================================================
# 🟢 For INTERNAL TESTING: Use "testing"
# 🔴 For emulator & ANDROID PRODUCTION: Use "android"

# DEPLOYMENT_MODE = "testing"  
DEPLOYMENT_MODE = "android"  

# Set chat threshold (0 = unlimited, or set to your desired limit)
THRESHOLD_TOTAL = 0

# Logging setup
logging.basicConfig(level=logging.INFO)  # root logger level; use INFO for production
logger = logging.getLogger("backend")
# keep logger at INFO by default; enable DEBUG locally when troubleshooting
logger.setLevel(logging.INFO)
"""
update this: logger.setLevel(logging.DEBUG)
logging.INFO: DEBUG, INFO, WARNING, ERROR, CRITICAL
logging.INFO: INFO, WARNING, ERROR, CRITICAL
logging.WARNING: WARNING, ERROR, CRITICAL
logging.ERROR: ERROR, CRITICAL
logging.CRITICAL: CRITICAL
"""

# Initialize FastAPI app
app = FastAPI(title="Mental Health RAG API")
init_db()

# ======================================================================
# CONDITIONAL IMPORTS & INITIALIZATION (based on deployment mode)
# ======================================================================
if DEPLOYMENT_MODE == "testing":
    # 🟢 INTERNAL TESTING - Direct RAG pipeline
    # Do NOT import heavy RAG/embedding modules at module import time on Windows.
    # Initialize lazily on first use to avoid torch/native DLL initialization errors.
    embedder = None
    vector_store = None
    retriever = None
    llm_client = None

    def ensure_testing_components():
        """Lazily initialize testing-mode components. Returns (retriever, llm_client).

        If heavy imports fail (torch/sentence-transformers missing), fall back to lightweight stubs.
        """
        global embedder, vector_store, retriever, llm_client
        if retriever is not None and llm_client is not None:
            return retriever, llm_client

        try:
            from src.rag.retriever import Retriever
            from src.llm.client import LLMClient
            from src.rag.embeddings import Embedder
            from src.storage.vector_store import InMemoryVectorStore as VectorStore

            embedder = Embedder()
            vector_store = VectorStore()
            retriever = Retriever(embedder, vector_store)
            llm_client = LLMClient()
            logger.info("✅ INTERNAL TESTING MODE - Direct RAG Pipeline initialized")
            return retriever, llm_client

        except Exception as e:
            logger.warning("Testing-mode lazy init failed, using stubs: %s", e)

            class _StubRetriever:
                def retrieve(self, q, top_k=3):
                    return []

            class _StubLLM:
                def generate_response(self, messages):
                    try:
                        user_msgs = [m.get("content", "") for m in messages if m.get("role") == "user"]
                        if len(user_msgs) >= 2:
                            prev = user_msgs[-2]
                            last = user_msgs[-1]
                            return f"[STUB_LLM] Previously you said: \"{prev}\". Now you said: \"{last}\""
                        elif len(user_msgs) == 1:
                            return f"[STUB_LLM] I remember: \"{user_msgs[-1]}\""
                        else:
                            return "[STUB_LLM] No user history available"
                    except Exception:
                        return "[STUB_LLM] (fallback)"

            retriever = _StubRetriever()
            llm_client = _StubLLM()
            return retriever, llm_client
    
elif DEPLOYMENT_MODE == "android":
    # 🔴 ANDROID PRODUCTION - Async RAG pipeline
    from src.api.android_main import initialize_all, run_rag_pipeline
    
    @app.on_event("startup")
    def startup_event():
        logger.info("🚀 Starting Android RAG initialization...")
        initialize_all()
        logger.info("✅ Android RAG system ready!")
    
    # Enable CORS for Android clients
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    logger.info("✅ ANDROID PRODUCTION MODE - Async RAG Pipeline")

# ======================================================================
# REQUEST MODELS
# ======================================================================
class ChatRequest(BaseModel):
    email: str
    message: str

class RegisterRequest(BaseModel):
    email: str
    age: int
    sex: str
    password: str

class LoginRequest(BaseModel):
    email: str
    password: str


def select_history_messages(history_rows, chat_history, current_message, max_total=12):
    """Select which DB messages to send to the RAG/LLM pipeline.

    Heuristics implemented:
    - Default: prefer the in-memory `chat_history` window (config.CHAT_HISTORY_WINDOW).
      If the in-memory window already provides enough context, send 0 DB msgs.
    - If `chat_history` is empty (session resume) and DB has messages, send 2-4 recent DB msgs.
    - If user explicitly refers to the past (keywords), allow up to 4-6 DB msgs.
    - Always cap total messages (DB + memory) <= `max_total` and reserve one for the current message.
    """
    try:
        window = int(getattr(config, "CHAT_HISTORY_WINDOW", 6))
    except Exception:
        window = 6

    mem_msgs = chat_history.last_n(window) if chat_history is not None else []
    mem_count = len(mem_msgs)

    # Normalize DB rows into dicts (oldest->newest assumed)
    db_msgs = [{"role": r[0], "content": r[1], "timestamp": r[2]} for r in (history_rows or [])]
    db_count = len(db_msgs)

    # Detect explicit user request to refer to past messages
    past_kw = re.compile(r"\b(earlier|before|previous|remind|remember|past|what did i|prior|last time)\b", re.I)
    wants_past = bool(past_kw.search(current_message or ""))

    # Determine DB quota
    if wants_past:
        db_quota = min(6, db_count)
    else:
        # If in-memory window already covers the desired window, prefer 0 DB messages
        if mem_count >= window:
            db_quota = 0
        else:
            # Session resume: chat_history empty but DB has messages -> 2-4 messages
            if mem_count == 0 and db_count > 0:
                db_quota = min(4, db_count)
            else:
                need = max(0, window - mem_count)
                db_quota = min(need, db_count)

    # Enforce total cap (reserve one for current message)
    total_allowed = max_total - 1
    remaining_for_db = max(0, total_allowed - mem_count)
    db_quota = min(db_quota, remaining_for_db)

    if db_quota <= 0:
        return []

    # Return the most recent `db_quota` messages
    return db_msgs[-db_quota:]


# -------------------------
# Tokenizer / trimming helpers
# -------------------------
try:
    import tiktoken
    try:
        _TOKENIZER = tiktoken.get_encoding("cl100k_base")
        _TOKENIZER_AVAILABLE = True
    except Exception:
        _TOKENIZER = None
        _TOKENIZER_AVAILABLE = False
except Exception:
    tiktoken = None
    _TOKENIZER = None
    _TOKENIZER_AVAILABLE = False


def estimate_tokens_from_text(text: str) -> int:
    """Estimate tokens for a single text. Prefer tiktoken when available,
    otherwise fall back to a simple heuristic: 1 token ≈ 4 chars.
    """
    if not text:
        return 0
    try:
        if _TOKENIZER_AVAILABLE and _TOKENIZER is not None:
            return len(_TOKENIZER.encode(text))
    except Exception:
        pass
    # fallback heuristic
    return max(1, len(text) // 4)


def count_tokens_for_messages(messages: list) -> int:
    """Messages is a list of dicts with 'content' or raw strings."""
    total = 0
    for m in messages or []:
        if isinstance(m, dict):
            text = (m.get("content") or "")
        else:
            text = str(m)
        total += estimate_tokens_from_text(text)
    return total


def trim_history_to_token_budget(instruction: str, db_msgs: list, mem_msgs: list, rag_docs: list, user_msg: str, budget: int = 1500):
    """Trim DB messages and RAG docs to fit within budget tokens.

    Strategy:
    - Count tokens for instruction + user_msg + mem_msgs (mem kept last, not trimmed unless necessary).
    - Drop oldest DB messages first until under budget.
    - If still over budget, trim RAG docs (drop lowest priority / oldest first).
    - Never drop in-memory `mem_msgs` unless absolutely necessary; if forced, drop oldest mem_msgs.
    Returns (db_msgs_trimmed, rag_docs_trimmed)
    """
    instr_tokens = estimate_tokens_from_text(instruction or "")
    user_tokens = estimate_tokens_from_text(user_msg or "")
    mem_tokens = count_tokens_for_messages(mem_msgs)
    db_tokens = count_tokens_for_messages(db_msgs)
    rag_tokens = count_tokens_for_messages(rag_docs)

    total = instr_tokens + user_tokens + mem_tokens + db_tokens + rag_tokens
    if total <= budget:
        return db_msgs, rag_docs

    # Start dropping oldest DB messages
    db_trim = list(db_msgs or [])
    rag_trim = list(rag_docs or [])

    # Drop DB messages oldest-first until either under budget or none left
    while db_trim and total > budget:
        removed = db_trim.pop(0)
        removed_tokens = estimate_tokens_from_text(removed.get("content") if isinstance(removed, dict) else str(removed))
        total -= removed_tokens

    # If still over budget, drop RAG docs (assume rag_docs is list of dicts with 'text')
    i = 0
    while rag_trim and total > budget:
        removed = rag_trim.pop(0)
        # try common keys
        text = (removed.get("text") if isinstance(removed, dict) else str(removed)) or ""
        removed_tokens = estimate_tokens_from_text(text)
        total -= removed_tokens
        i += 1

    # If still over budget, drop oldest mem messages as last resort
    mem_trim = list(mem_msgs or [])
    while mem_trim and total > budget:
        removed = mem_trim.pop(0)
        removed_tokens = estimate_tokens_from_text(removed.get("content") if isinstance(removed, dict) else str(removed))
        total -= removed_tokens

    return db_trim, rag_trim


# -------------------------
# Low-confidence detection & fallback
# -------------------------
LOW_CONF_PATTERNS = [
    "i'm not sure",
    "i am not sure",
    "i don't understand",
    "i do not understand",
    "can you clarify",
    "tell me more",
    "unclear",
    "i'm not able",
    "i am not able",
    "i can't",
    "i cannot",
]

EMOTION_KEYWORDS = [
    "anxiety", "anxious", "panic", "panic attack", "worried", "worry",
    "stress", "stressed", "sad", "depressed", "depression", "scared",
    "fear", "overwhelmed", "sleep", "insomnia", "tired", "upset",
    "heart", "racing", "breath", "breathing", "grounding"
]

SUPPORTED_TOPICS = [
    "Anxiety & Panic",
    "Overthinking & Mental Loops",
    "Stress, Burnout & Emotional Exhaustion",
    "Career, Studies & Work Pressure",
    "Fear of Failure, Mistakes & Success",
    "Uncertainty About the Future & Life Direction",
    "Self-Worth, Comparison & Confidence",
    "Social Anxiety, Judgement & Rejection",
    "Relationships, Attachment & Breakups",
    "Marriage & Long-Term Relationship Issues",
    "Loneliness, Abandonment & Being Alone",
    "Sleep Problems & Night Overthinking",
    "Health Anxiety & Body-Related Fears",
    "Emotional Numbness, Disconnection & Identity",
    "Feeling Overwhelmed & Losing Control",
]


# Crisis keywords (non-LLM immediate guard)
CRISIS_KW = [
    "suicide", "kill myself", "end my life", "self harm", "self-harm", "i want to die",
]

# -------------------------
# Greeting handler (fast, no-LLM)
# -------------------------
GREETING_PATTERNS = re.compile(
    # Match common greeting starters (allow punctuation and trailing text)
    r"^\s*(hi|hii|hi there|hello|hello there|hey|hey there|hlo|hola|namaste|good morning|good evening)\b[!.,?\"']?\s*(.*)$",
    re.I
)

GREETING_REPLIES = [
    "Hello 💙 Take a moment. What are you feeling right now?",
    "Hey 👋 You’re safe here. Tell me what’s troubling you.",
    "Hi there. What would you like help with today?",
    "Hello 🌱 You can talk freely here."
]

def is_greeting(text: str) -> bool:
    if not text:
        return False
    # Strip leading/trailing whitespace and rely on case-insensitive regex
    return bool(GREETING_PATTERNS.match(text.strip()))


def topic_confidence(text: str, min_keyword_matches: int = 1) -> bool:
    """Cheap topic confidence: true if message contains obvious topic keywords
    from SUPPORTED_TOPICS or common emotion keywords. This is intentionally simple
    and fast (no embeddings).
    """
    if not text:
        return False
    tl = text.lower()
    # Check emotion keywords first
    for k in EMOTION_KEYWORDS:
        if k in tl:
            return True
    # Check explicit topic phrase matches or keyword overlaps
    for topic in SUPPORTED_TOPICS:
        tlower = topic.lower()
        # full phrase match
        if tlower in tl:
            return True
        # keyword overlap: split topic into words and check presence
        words = [w for w in re.split(r"\W+", tlower) if w]
        matches = sum(1 for w in words if w and w in tl)
        if matches >= min_keyword_matches and matches >= 1:
            return True
    return False


# -------------------------
# Soft topic hints + greeting builder
# -------------------------
SOFT_TOPIC_HINTS = [
    "If you want, we can talk about anxiety, overthinking, sleep, or relationships.",
    "You can share anything — stress, fear, work pressure, or just how today feels.",
    "I can help with anxiety, overthinking, career stress, relationships, or sleep issues.",
    "We can talk about stress, emotions, or anything that’s bothering you quietly."
]

def build_greeting_reply() -> str:
    greeting = random.choice(GREETING_REPLIES)
    hint = random.choice(SOFT_TOPIC_HINTS)
    return f"{greeting}\n\n{hint}"


# -------------------------
# Topic prompts and UI buttons
# -------------------------
TOPIC_BUTTONS = [
    "Anxiety & Panic",
    "Overthinking & Mental Loops",
    "Stress & Burnout",
    "Sleep Problems",
    "Relationships"
]

TOPIC_PROMPTS = {
    "Overthinking & Mental Loops":
        "The user is experiencing overthinking. Respond with emotional validation and simple grounding steps.",
    "Anxiety & Panic":
        "The user is experiencing anxiety or panic. Respond calmly with reassurance and grounding.",
    "Stress & Burnout":
        "The user is dealing with stress or burnout. Offer brief pacing, boundaries and small recovery steps.",
    "Sleep Problems":
        "The user has sleep problems. Offer sleep hygiene tips and short grounding routines.",
    "Relationships":
        "The user is having relationship difficulties. Provide validation, reflective listening and small actions."
}



def is_low_confidence_reply(reply: str) -> bool:
    try:
        if not isinstance(reply, str) or not reply.strip():
            return True
        rl = reply.lower()
        # explicit low-confidence phrases
        for p in LOW_CONF_PATTERNS:
            if p in rl:
                return True
        # too short / generic
        if len(rl) < 60:
            return True
        # lacks any emotion/problem keyword and is not very long
        if not any(k in rl for k in EMOTION_KEYWORDS) and len(rl) < 200:
            return True
    except Exception:
        return True
    return False


def build_guided_fallback() -> str:
    bullets = "\n".join([f"• {t}" for t in SUPPORTED_TOPICS])
    return (
        "I may not have fully understood what you're feeling.\n\n"
        "Could you try explaining it in simpler words? For example:\n"
        "• “I feel anxious at night”\n"
        "• “My heart races suddenly”\n"
        "• “I feel scared without a reason”\n\n"
        "I can help with:\n"
        f"{bullets}\n\n"
        "You can pick one or describe it in your own words 💙"
    )

# ======================================================================
# AUTH ENDPOINTS
# ======================================================================
@app.post("/auth/register")
async def register(req: RegisterRequest):
    """Register a new user"""
    try:
        email = req.email.strip().lower()
        existing = get_user(email)
        logger.debug("Register attempt for email=%s", req.email)
        if existing:
            # Explicitly reject registration when the user already exists.
            err = {"error": "User already exists. Please login."}
            logger.info("Registration blocked - user exists: %s", req.email)
            return JSONResponse(err, status_code=409)

        try:
            create_user(email, req.age, req.sex, req.password)
            logger.info("User created: %s", req.email)
        except IntegrityError:
            logger.warning("Duplicate registration attempt (race): %s", req.email)
            err = {"error": "User already exists. Please login."}
            return JSONResponse(err, status_code=409)
        except ValueError as ve:
            # create_user raises ValueError("user_exists") on duplicate
            if str(ve) == "user_exists":
                logger.warning("Duplicate registration attempt: %s", req.email)
                err = {"error": "User already exists. Please login."}
                return JSONResponse(err, status_code=409)
            raise

        if DEPLOYMENT_MODE == "android":
            return {
                "success": "New User Created",
                "chats": 2,
                "error": None
            }
        else:
            return JSONResponse({"success": "User registered", "chats": 2})

    except Exception as e:
        logger.exception("Register error for %s: %s", req.email, e)
        if DEPLOYMENT_MODE == "android":
            return {"success": None, "error": str(e)}
        else:
            return JSONResponse({"error": str(e)}, status_code=500)

@app.post("/auth/login")
async def login(req: LoginRequest):
    """Login user and return usage statistics"""
    try:
        # Normalize email for login to match stored values
        email = req.email.strip().lower()
        user = get_user(email)
        
        if not user:
            error_response = {"error": "User does not exist"}
            if DEPLOYMENT_MODE == "testing":
                return JSONResponse(error_response, status_code=404)
            return error_response
        
        stored_hash = user[3]
        
        if not bcrypt.checkpw(req.password.encode(), stored_hash.encode()):
            error_response = {"error": "Incorrect password"}
            if DEPLOYMENT_MODE == "testing":
                return JSONResponse(error_response, status_code=401)
            return error_response
        
        usage_stats = get_usage_stats(email)
        
        login_response = {
            "success": "Login successful",
            "email": user[0],
            "age": user[1],
            "sex": user[2],
            "usage_count": user[4],
            # safe cast for chats (get_user returns COALESCE'd value)
            "chats": int(user[5]) if user and len(user) > 5 else 0,
            "usage_stats": usage_stats
        }
        
        if DEPLOYMENT_MODE == "testing":
            return JSONResponse(login_response)
        return login_response
    
    except Exception as e:
        error_msg = {"error": str(e)}
        if DEPLOYMENT_MODE == "testing":
            return JSONResponse(error_msg, status_code=500)
        return error_msg

# ======================================================================
# CHAT ENDPOINT
# ======================================================================
@app.post("/chat")
async def chat(req: ChatRequest):
    """Chat endpoint with conditional logic based on deployment mode"""
    email = req.email
    message = req.message
    # Clients no longer send session_id; default to session 1 for legacy storage calls
    session_id = 1
    
    # Check user exists
    user = get_user(email)
    if not user:
        error_response = {
            "allowed": False,
            "error": "User not registered",
            "reply": None
        } if DEPLOYMENT_MODE == "android" else {"error": "User not found"}
        
        if DEPLOYMENT_MODE == "testing":
            return JSONResponse(error_response, status_code=404)
        return error_response
    
    # Get usage statistics
    usage_total = user[4]              # Total usage count
    # `get_user()` now COALESCEs numeric fields; safely cast chats to int with fallback
    try:
        chats = int(user[5])
    except Exception:
        chats = 0
    logger.debug(f"/chat - Email: {email}, Chats before deduction: {chats}")
    try:
        usage_total = int(usage_total) if usage_total else 0
        chats = int(chats) if chats else 0
    except Exception:
        usage_total = 0
        chats = 0
    
    # 💰 Check if user has any chats remaining (includes free + purchased)
    if chats > 0:
        # User has chats available - allow chat
        pass  # Will process chat below and deduct after
    # 📊 No chats remaining - show limit message
    else:
        error_response = {
            "allowed": False if DEPLOYMENT_MODE == "android" else None,
            "error": "No chats remaining. Please buy more chats to continue.",
            "used_total": usage_total,
            "chats": 0,
            "reply": None if DEPLOYMENT_MODE == "android" else None
        }
        if DEPLOYMENT_MODE == "testing":
            return JSONResponse(error_response, status_code=429)
        return error_response
    
    chat_history = ChatHistory(email)
    start = time.time()

    # Detect synthetic topic-selection control signal IMMEDIATELY after reading message
    topic_selected = False
    selected_topic = None
    selected_prompt = None
    if isinstance(message, str) and message.startswith("__TOPIC_SELECTED__:"):
        selected_topic = message.replace("__TOPIC_SELECTED__:", "", 1).strip()
        selected_prompt = TOPIC_PROMPTS.get(
            selected_topic,
            f"The user is dealing with {selected_topic}. Respond with validation."
        )
        topic_selected = True

    # If user explicitly asks for a listing of their previous messages,
    # return a deterministic, DB-built numbered recap instead of delegating
    # to the LLM. This avoids non-deterministic re-ordering by the model.

    # 1️⃣ GREETING SHORT-CIRCUIT (soft guidance)
    if not topic_selected:
        try:
            if is_greeting(message):
                if chats <= 0:
                    return {
                        "allowed": False,
                        "reply": "You’ve used all your chats. Please buy more to continue 💙",
                        "chats": 0,
                        "error": None
                    }
                reply = build_greeting_reply()

                # Persist user + assistant for UI/history, but DO NOT deduct or increment usage
                safe_save(email, "user", message, session_id)
                safe_save(email, "assistant", reply, session_id)

                if DEPLOYMENT_MODE == "testing":
                    return JSONResponse({
                        "reply": reply,
                        "show_topics": True,
                        "topics": TOPIC_BUTTONS,
                        "documents": [],
                        "has_retrieval": False,
                        "usage_stats": {"total": usage_total},
                        "chats": chats,
                        "error": None
                    })
                else:
                    # For Android clients, do NOT prompt with topic chips on simple greetings.
                    # Keep the soft greeting reply but avoid requesting topic selection here.
                    return {
                        "allowed": True,
                        "reply": reply,
                        "show_topics": False,
                        "usage_now": usage_total,
                        "chats": chats,
                        "limit": THRESHOLD_TOTAL if THRESHOLD_TOTAL > 0 else "unlimited",
                        "processing_time": round(time.time() - start, 2),
                        "error": None
                    }
        except Exception:
            pass

        # 2️⃣ TOPIC CONFIDENCE CHECK (cheap heuristic). If not confident, show topic picker
        try:
            if not topic_confidence(message):
                if chats <= 0:
                    return {
                        "allowed": False,
                        "reply": "You’ve used all your chats. Please buy more to continue 💙",
                        "chats": 0,
                        "error": None
                    }
                picker = (
                    "I want to help — please pick a topic below or explain in your own words 💙"
                )
                # Persist user + assistant for UI/history but DO NOT charge
                safe_save(email, "user", message, session_id)
                safe_save(email, "assistant", picker, session_id)

                if DEPLOYMENT_MODE == "testing":
                    return JSONResponse({
                        "reply": picker,
                        "show_topics": True,
                        "topics": TOPIC_BUTTONS,
                        "documents": [],
                        "has_retrieval": False,
                        "usage_stats": {"total": usage_total},
                        "chats": chats,
                        "error": None
                    })
                else:
                    return {
                        "allowed": True,
                        "reply": picker,
                        "show_topics": True,
                        "topics": TOPIC_BUTTONS,
                        "usage_now": usage_total,
                        "chats": chats,
                        "limit": THRESHOLD_TOTAL if THRESHOLD_TOTAL > 0 else "unlimited",
                        "processing_time": round(time.time() - start, 2),
                        "error": None
                    }
        except Exception:
            pass
    
    try:
        if DEPLOYMENT_MODE == "testing":
            # 🟢 TESTING: Direct RAG pipeline
            # Ensure testing components are initialized (may return stubs)
            try:
                retriever, llm_client = ensure_testing_components()
            except Exception:
                # defensive fallback if ensure_testing_components not available
                retriever = None
                llm_client = None

            # If user selected a topic, retrieve by topic metadata for high-precision RAG
            user_for_generation = selected_prompt if topic_selected and selected_prompt else message
            if topic_selected and retriever:
                try:
                    # prefer an API that accepts query= and filter=kwargs
                    documents = retriever.retrieve(query=selected_topic, top_k=2, filter={"topic": selected_topic})
                except TypeError:
                    try:
                        documents = retriever.retrieve(selected_topic, top_k=2)
                    except Exception:
                        documents = []
                except Exception:
                    documents = []
                user_for_generation = selected_prompt or message
            else:
                documents = retriever.retrieve(message) if retriever else []
                user_for_generation = message
            has_documents = len(documents) > 0

            # Log retrieval results for easier debugging: counts, ids, and short previews
            try:
                ids = [d.get("id") for d in documents]
                logger.info("/chat (testing) - retrieved_count=%s ids=%s", len(documents), ids)
                for d in (documents or [])[:3]:
                    txt = (d.get("text") or "").replace("\n", " ")
                    preview = txt[:140] + ("..." if len(txt) > 140 else "")
                    logger.info("/chat (testing) doc id=%s score=%.4f preview=%s", d.get("id"), float(d.get("score", 0.0)), preview)
            except Exception as _log_e:
                logger.debug("/chat (testing) - failed to log retrieved docs: %s", _log_e)

            # Temporary safeguard: persist the incoming user message BEFORE calling the LLM
            # so DB-backed history is available to the LLM (useful for debug_mode stubs)
            user_saved_before = False
            try:
                save_message(email, "user", message, session_id=session_id)
                user_saved_before = True
            except Exception as e:
                logger.warning("/chat (testing) - failed to pre-save user message: %s", e)

            # Build messages from DB history (oldest -> newest)
            try:
                history_rows = get_messages(email, limit=7, session_id=session_id)
                history_msgs = [{"role": r[0], "content": r[1], "timestamp": r[2]} for r in history_rows]
            except Exception:
                history_msgs = None

            # Token-budget enforcement: trim DB history and retrieved docs to fit
            try:
                mem_msgs = chat_history.last_n(getattr(config, "CHAT_HISTORY_WINDOW", 6))
            except Exception:
                mem_msgs = chat_history.last_n(6)

            try:
                db_trimmed, rag_trimmed = trim_history_to_token_budget(
                    instruction=DEFAULT_INSTRUCTION,
                    db_msgs=history_msgs or [],
                    mem_msgs=mem_msgs,
                    rag_docs=documents or [],
                    user_msg=user_for_generation,
                    budget=1500,
                )
            except Exception:
                db_trimmed = history_msgs or []
                rag_trimmed = documents or []

            # Deduction moved after reply validation (do not charge before confirming reply)
            
            # Generate LLM response. Prefer passing DB history when available so debug LLM
            # can reference prior messages. Use trimmed DB and RAG docs.
            if db_trimmed:
                # Convert db_trimmed to the messages format expected by LLMClient
                llm_messages = []
                for m in db_trimmed:
                    llm_messages.append({"role": m.get("role", "user"), "content": m.get("content", "")})
                # append the current user message only if we did NOT pre-save it
                if not user_saved_before:
                    llm_messages.append({"role": "user", "content": user_for_generation})
                # Crisis guard (non-LLM) - immediate help for high-risk messages
                try:
                    ml = (message or "").lower()
                    if any(k in ml for k in CRISIS_KW):
                        crisis_text = ("I'm really glad you reached out. You deserve support. "
                                       "Please contact a trusted person or local helpline right now.")
                        return JSONResponse({
                            "reply": crisis_text,
                            "documents": [],
                            "has_retrieval": False,
                            "usage_stats": {"total": usage_total},
                            "chats": chats,
                            "error": None
                        })
                except Exception:
                    pass
                # Optionally, LLM client may accept retrievals separately; we pass trimmed RAG docs via documents variable if used by client
                reply = llm_client.generate_response(llm_messages)
            else:
                reply = llm_client.generate_response([
                    {"role": "user", "content": message}
                ])
            
            # Protect and cap reply before saving to history/DB
            fallback_reply = "I'm here with you. Let's take a breath and try again."
            try:
                if not isinstance(reply, str) or not reply.strip():
                    reply = fallback_reply
            except Exception:
                reply = fallback_reply

            try:
                reply = reply[:1200]
            except Exception:
                reply = str(reply)[:1200]

            # Low-confidence detection: if model reply seems vague or misses emotion/problem,
            # show guided fallback to the user and DO NOT charge or save assistant message.
            try:
                if is_low_confidence_reply(reply):
                    fallback = build_guided_fallback()
                    try:
                        chat_history.add_assistant(fallback)
                    except Exception:
                        pass
                    return JSONResponse({
                        "reply": fallback,
                        "documents": [],
                        "has_retrieval": False,
                        "usage_stats": {"total": usage_total},
                        "chats": chats,
                        "error": None
                    })
            except Exception:
                # If detection fails, proceed with normal flow (defensive)
                pass

            # Deduct from available chats now that reply validated
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE users
                SET chats = CASE
                    WHEN chats IS NULL THEN 0
                    WHEN chats > 0 THEN chats - 1
                    ELSE 0
                END
                WHERE email = ?
            """, (email,))
            conn.commit()
            cursor.execute("SELECT COALESCE(chats, 0) FROM users WHERE email = ?", (email,))
            row = cursor.fetchone()
            updated_chats = int(row[0]) if row and row[0] is not None else 0
            logger.debug(f"/chat (testing) - Email: {email}, Chats after deduction: {updated_chats}")
            conn.close()

            # Also increment usage_count for statistics
            increment_usage(email)
            usage_now = usage_total + 1

            # Save chat history (assistant) and persist to DB
            try:
                chat_history.add_user(message)
                chat_history.add_assistant(reply)
            except Exception:
                pass

            logger.debug(f"About to save user and assistant messages for email: {email}, Session: {session_id}")
            try:
                if not user_saved_before:
                    save_message(email, "user", message, session_id=session_id)
                save_message(email, "assistant", reply, session_id=session_id)
            except Exception as e:
                logger.warning("/chat (testing) - failed to save messages after reply: %s", e)
            logger.debug(f"Finished saving user and assistant messages for email: {email}, Session: {session_id}")

            documents_clean = [
                {
                    "text": d.get("text"),
                    "score": d.get("score"),
                    "metadata": d.get("metadata")
                }
                for d in (rag_trimmed if 'rag_trimmed' in locals() else documents)
            ]

            return JSONResponse({
                "reply": reply,
                "documents": documents_clean,
                "has_retrieval": has_documents,
                "usage_stats": {
                    "total": usage_now
                },
                "chats": updated_chats,
                "error": None
            })
        
        else:  # ANDROID MODE
            # 🔴 ANDROID: Async RAG pipeline
            # Normalize email for Android clients
            email = email.strip().lower() if isinstance(email, str) else email
            # Do NOT pre-save the incoming user message. Keep the DB as the
            # single source of truth and avoid writing the same message twice.
            # We'll persist user+assistant messages once after the RAG pipeline returns.
            user_saved_before = False

            # Fetch stored messages for this session and choose which DB messages
            # to send into the RAG pipeline using heuristics (avoid oversending).
            logger.debug("/chat - fetching history for email=%s session_id=%s", email, session_id)
            history_rows = get_messages(email, limit=50, session_id=session_id)
            # Use helper to select a small, relevant set of DB messages
            history_msgs = select_history_messages(history_rows, chat_history, message)
            logger.debug("/chat - history_msgs count=%s preview=%s", len(history_msgs), history_msgs[:3])

            # Token-budget enforcement (Android): we cannot see RAG docs here (pipeline will fetch them),
            # so conservatively trim DB messages to leave room for retrieval. Reserve ~600 tokens for RAG/docs.
            try:
                mem_msgs = chat_history.last_n(getattr(config, "CHAT_HISTORY_WINDOW", 6))
            except Exception:
                mem_msgs = chat_history.last_n(6)

            try:
                db_trimmed, _ = trim_history_to_token_budget(
                    instruction=DEFAULT_INSTRUCTION,
                    db_msgs=history_msgs or [],
                    mem_msgs=mem_msgs,
                    rag_docs=[],
                    user_msg=message,
                    budget=900,
                )
                history_msgs = db_trimmed
            except Exception:
                pass

            # Crisis guard (non-LLM) - immediate help for high-risk messages
            try:
                ml = (message or "").lower()
                if any(k in ml for k in CRISIS_KW):
                    crisis_text = ("I'm really glad you reached out. You deserve support. "
                                   "Please contact a trusted person or local helpline right now.")
                    return {
                        "allowed": True,
                        "reply": crisis_text,
                        "usage_now": usage_total,
                        "chats": chats,
                        "limit": THRESHOLD_TOTAL if THRESHOLD_TOTAL > 0 else "unlimited",
                        "processing_time": round(time.time() - start, 2),
                        "error": None
                    }
            except Exception:
                pass

            # If topic was selected, call pipeline with a focused prompt so pipeline can filter/retrieve by topic
            pipeline_message = selected_prompt if topic_selected and selected_prompt else message

            # Run RAG pipeline in threadpool; log start/end for timing
            logger.debug("/chat - running run_rag_pipeline for email=%s session_id=%s topic_selected=%s", email, session_id, topic_selected)
            reply = await run_in_threadpool(run_rag_pipeline, pipeline_message, chat_history, history_msgs)
            logger.debug("/chat - run_rag_pipeline completed for email=%s session_id=%s reply_len=%s", email, session_id, len(reply) if isinstance(reply, str) else 0)

            # Protect against non-string/empty replies and cap length
            fallback_reply = "I'm here with you. Let's take a breath and try again."
            try:
                if not isinstance(reply, str) or not reply.strip():
                    reply = fallback_reply
            except Exception:
                reply = fallback_reply

            # Final defensive check - if reply still falsy, abort (no deduction)
            if not reply:
                raise RuntimeError("LLM returned empty reply")

            # Cap response length to keep replies calm and focused
            try:
                reply = reply[:1200]
            except Exception:
                # ensure reply is a string
                reply = str(reply)[:1200]

            # Low-confidence detection (Android): if model reply seems vague, show guided fallback
            try:
                if is_low_confidence_reply(reply):
                    fallback = build_guided_fallback()
                    try:
                        chat_history.add_assistant(fallback)
                    except Exception:
                        pass
                    return {
                        "allowed": True,
                        "reply": fallback,
                        "usage_now": usage_total,
                        "chats": chats,
                        "limit": THRESHOLD_TOTAL if THRESHOLD_TOTAL > 0 else "unlimited",
                        "processing_time": round(time.time() - start, 2),
                        "error": None
                    }
            except Exception:
                pass

            # Safe deduct from available chats (avoid negatives / NULL) - do this only after reply validated
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE users
                SET chats = CASE
                    WHEN chats IS NULL THEN 0
                    WHEN chats > 0 THEN chats - 1
                    ELSE 0
                END
                WHERE email = ?
            """, (email,))
            conn.commit()
            # Read authoritative value using COALESCE
            cursor.execute("SELECT COALESCE(chats, 0) FROM users WHERE email = ?", (email,))
            row = cursor.fetchone()
            updated_chats = int(row[0]) if row and row[0] is not None else 0
            logger.debug(f"/chat - Email: {email}, Chats after deduction: {updated_chats}")
            conn.close()
            # Also increment usage_count for statistics
            increment_usage(email)
            usage_now = usage_total + 1

            # Save chat messages to DB once. `run_rag_pipeline` has already
            # appended messages to the in-memory `chat_history` for UI; persist
            # both the user message and assistant reply here so the DB is
            # authoritative and no duplicate writes occur.
            logger.debug("About to save user and assistant messages for email: %s, Session: %s", email, session_id)
            try:
                save_message(email, "user", message, session_id=session_id)
                save_message(email, "assistant", reply, session_id=session_id)
            except Exception as e:
                logger.warning("/chat - failed to save messages after reply: %s", e)
            logger.debug("Finished saving user and assistant messages for email: %s, Session: %s", email, session_id)

            return {
                "allowed": True,
                "reply": reply,
                "usage_now": usage_now,
                "chats": updated_chats,
                "limit": THRESHOLD_TOTAL if THRESHOLD_TOTAL > 0 else "unlimited",
                "processing_time": round(time.time() - start, 2),
                "error": None
            }
    
    except Exception as e:
        logger.error(f"Chat error: {e}")
        
        if DEPLOYMENT_MODE == "testing":
            return JSONResponse({"error": f"Internal Server Error: {str(e)}"}, status_code=500)
        else:
            return {
                "allowed": False,
                "error": f"Service is temporarily unavailable, try again later.",
                "chats": chats,
                "reply": None
            }
# ======================================================================
# PURCHASE ENDPOINT
# ======================================================================
@app.post("/purchase/verify")
async def verify_purchase(req: dict):
    """
    Verify purchase and add chats to user account
    
    Chats are added to a universal pool that works for BOTH:
    - Chats WITH document retrieval
    - Chats WITHOUT document retrieval
    
    The purchased chats bypass threshold limits.
    """
    email = req.get("email")
    # Accept either `purchase_token` (frontend test) or `purchaseToken`.
    purchase_token = req.get("purchase_token") or req.get("purchaseToken")
    product_id = req.get("product_id") or req.get("productId")
    
    # Step 1: Validate user exists
    user = get_user(email)
    if not user:
        return {
            "success": False,
            "error": "User not found",
            "chats_added": 0
        }
    
    # (Optional) Log that we received a purchase token.
    if purchase_token:
        logger.debug("/purchase/verify - received purchase_token (truncated)=%s", str(purchase_token)[:12])

    # Idempotency: if we've already processed this purchase token, return success without double-grant
    if purchase_token and is_purchase_token_processed(purchase_token):
        logger.info("/purchase/verify - purchase_token already processed: %s", str(purchase_token)[:12])
        # Re-read user to return current remaining chats
        user = get_user(email)
        try:
            remaining = int(user[5]) if user else 0
        except Exception:
            remaining = 0
        return {
            "success": True,
            "chats_added": 0,
            "product_id": product_id,
            "message": "Already processed purchase token",
            "remaining_chats": remaining,
            "updated_usage": get_usage_stats(email)
        }

    # Step 2: Map product to chats amount
    # Product ID -> Number of chats to add
    product_chats = {
    "mental_health_5_chats_v1": 5,
    "mental_health_10_chats_v1": 10,
    "mental_health_5_chats": 5,
    "mental_health_10_chats": 10,
}
    
    chats_to_add = product_chats.get(product_id, 5)  # Default 5 if unknown
    
    # Optional: Verify with Google Play if service account + package name are configured
    try:
        if config.GOOGLE_SERVICE_ACCOUNT_FILE and config.PLAY_PACKAGE_NAME:
            try:
                verify_resp = google_play.verify_product_purchase(config.PLAY_PACKAGE_NAME, product_id, purchase_token)
                # Google Play returns purchaseState==0 when purchased
                if verify_resp is None:
                    logger.debug("Google Play verification skipped (no response)")
                else:
                    purchase_state = int(verify_resp.get("purchaseState", 1))
                    if purchase_state != 0:
                        logger.warning("Google Play reports non-purchased state for token: %s state=%s", str(purchase_token)[:12], purchase_state)
                        return {
                            "success": False,
                            "chats_added": 0,
                            "product_id": product_id,
                            "message": "Google Play verification failed: not purchased",
                            "remaining_chats": get_user(email)[5] if get_user(email) else 0,
                            "updated_usage": get_usage_stats(email)
                        }
            except Exception as e:
                logger.exception("Google Play verification exception: %s", e)
                return {
                    "success": False,
                    "chats_added": 0,
                    "product_id": product_id,
                    "message": "Google Play verification error",
                    "remaining_chats": get_user(email)[5] if get_user(email) else 0,
                    "updated_usage": get_usage_stats(email)
                }

    except Exception:
        logger.debug("Skipping Google Play verification - config not available or error")

    # Step 3: Add chats to user's account
    # Note: This adds to 'chats' column which works for ALL chat types
    add_chats(email, chats_to_add)

    # Mark this purchase token as processed to ensure idempotency
    if purchase_token:
        try:
            mark_purchase_token_processed(purchase_token, email, product_id)
            logger.debug("/purchase/verify - marked token processed: %s", str(purchase_token)[:12])
        except Exception:
            logger.exception("Failed to mark purchase token as processed")

    # Re-read user to get authoritative updated chats value
    user = get_user(email)

    # Step 4: Get updated statistics
    updated_stats = get_usage_stats(email)

    # Step 5: Return success response
    try:
        remaining = int(user[5]) if user else chats_to_add
    except Exception:
        remaining = chats_to_add

    return {
        "success": True,
        "chats_added": chats_to_add,
        "product_id": product_id,
        "message": f"✅ Successfully added {chats_to_add} chats to your account!",
        "remaining_chats": remaining,
        "updated_usage": updated_stats
    }


@app.get("/debug/purchases")
def debug_list_purchases(limit: int = 50):
    """Return recent processed purchase tokens for debugging (truncated)."""
    try:
        rows = list_processed_purchases(limit)
        # redact tokens in output (show only first 12 chars)
        return {
            "success": True,
            "purchases": [
                {"token_preview": (r[0][:12] if r[0] else None), "email": r[1], "product_id": r[2], "created_at": r[3]} for r in rows
            ]
        }
    except Exception as e:
        logger.exception("debug_list_purchases failed: %s", e)
        return {"success": False, "error": str(e)}



# ======================================================================
# CHAT HISTORY ENDPOINTS
# ======================================================================
@app.post("/history/list")
async def history_list(req: dict):
    """Return list of sessions for a given user (session id, count, last_updated)."""
    email = req.get("email")
    if not email:
        return {"success": False, "error": "Missing email", "chats": []}

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT session_id, COUNT(*), MAX(timestamp)
        FROM messages
        WHERE email = ?
        GROUP BY session_id
        ORDER BY MAX(timestamp) DESC
        """,
        (email,)
    )
    rows = cursor.fetchall()
    conn.close()

    sessions = [
        {"id": r[0], "message_count": r[1], "last_updated": r[2], "title": f"Session {r[0]}"}
        for r in rows
    ]

    return {"success": True, "chats": sessions}


@app.post("/history/messages")
async def history_messages(req: dict):
    """Return messages for a given user and session_id. Expects {email, session_id, limit}"""
    email = req.get("email")
    session_id = int(req.get("session_id", 1))
    limit = int(req.get("limit", 100))

    if not email:
        return {"success": False, "error": "Missing email", "messages": []}
    # If user has hidden their history, return empty list (UI-only hide)
    try:
        if is_history_hidden(email):
            return {"success": True, "messages": []}
    except Exception:
        pass

    rows = get_messages(email, limit=limit, session_id=session_id)
    messages = [{"role": r[0], "content": r[1], "timestamp": r[2]} for r in rows]
    return {"success": True, "messages": messages}

@app.get("/purchase/options")
def get_purchase_options():
    """Get available purchase options with pricing"""
    return {
        "success": True,
        "options": [
            {
                "id": "mental_health_5_chats_v1",
                "name": "5 Chats",
                "description": "Get 5 additional chats",
                "chats": 5,
                "price": "$0.99",
                "price_usd": 0.99
            },
            {
                "id": "mental_health_10_chats_v1",
                "name": "10 Chats",
                "description": "Get 10 additional chats",
                "chats": 10,
                "price": "$1.99",
                "price_usd": 1.99,
                "popular": True
            }
        ]
    }
# ======================================================================
# USER CHATS ENDPOINT
# ======================================================================
@app.post("/user/chats")
async def get_user_chats(request: dict):
    """Get real-time chats for a user"""
    email = request.get("email")
    
    if not email:
        return {"error": "Email required", "chats": 0}
    
    # Get user from database
    user = get_user(email)
    
    if not user:
        return {"error": "User not found", "chats": 0}
    
    # Extract chats (column index 5) with safe cast fallback
    try:
        chats = int(user[5])
    except Exception:
        chats = 0
    
    return {
        "chats": chats,
        "error": None
    }

# ======================================================================
# STATISTICS & UTILITY ENDPOINTS
# ======================================================================
@app.get("/stats/{email}")
def get_stats(email: str):
    """Get usage statistics for a user"""
    user = get_user(email)
    
    if not user:
        error_response = {"error": "User not found"}
        if DEPLOYMENT_MODE == "testing":
            return JSONResponse(error_response, status_code=404)
        return error_response
    
    usage_stats = get_usage_stats(email)
    
    stats_response = {
        "email": email,
        "usage_stats": usage_stats
    }
    
    if DEPLOYMENT_MODE == "testing":
        return JSONResponse(stats_response)
    return stats_response

@app.get("/health")
def health():
    """Health check endpoint"""
    return {
        "status": "ok",
        "message": "server running",
        "mode": DEPLOYMENT_MODE
    }
# --------------------------------------------------------
# ✅ GET Chat history
# --------------------------------------------------------
@app.post("/chat/history/list")
async def get_chat_history_list(request: dict):
    email = request.get("email")
    if not email:
        raise HTTPException(status_code=400, detail="Email required")
    
    # Query DB for real chat sessions
    import sqlite3
    from collections import defaultdict
    from src.storage.user_db import DB_PATH
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    # Get all session_ids for this user, most recent first
    cursor.execute("""
        SELECT session_id, MAX(timestamp) as last_time
        FROM messages
        WHERE email = ?
        GROUP BY session_id
        ORDER BY last_time DESC
        LIMIT 5;
    """, (email,))
    sessions = cursor.fetchall()
    chat_sessions = []
    for sess in sessions:
        session_id = sess[0]
        # Get preview (first user message in session)
        cursor.execute("""
            SELECT content FROM messages
            WHERE email = ? AND session_id = ? AND role = 'user'
            ORDER BY id ASC LIMIT 1;
        """, (email, session_id))
        preview_row = cursor.fetchone()
        preview = preview_row[0][:50] + "..." if preview_row else "Start a conversation..."
        # Get message count
        cursor.execute("""
            SELECT COUNT(*) FROM messages
            WHERE email = ? AND session_id = ?;
        """, (email, session_id))
        count_row = cursor.fetchone()
        message_count = count_row[0] if count_row else 0
        chat_sessions.append({
            "id": session_id,
            "title": f"Chat {session_id}",
            "preview": preview,
            "message_count": message_count
        })
    conn.close()
    # If no sessions, return empty list so frontend can render an empty state
    if not chat_sessions:
        return {"chats": []}
    return {"chats": chat_sessions}

# --------------------------------------------------------
# ✅ GET MESSAGES FROM A SPECIFIC CHAT SESSION
# --------------------------------------------------------
@app.post("/chat/history/get")
async def get_chat_history_messages(request: dict):
    """Get all messages for a user's chat history"""
    email = request.get("email")
    limit = request.get("limit", 100)  # Default to 100 messages
    session_id = request.get("session_id", 1)
    if not email:
        raise HTTPException(status_code=400, detail="Email required")
    # If user has hidden their history, return empty response
    try:
        if is_history_hidden(email):
            return {"messages": [], "count": 0}
    except Exception:
        pass
    # Get messages from database
    messages = get_messages(email, limit=limit, session_id=session_id)
    
    # Format messages for frontend
    formatted_messages = []
    for msg in messages:
        formatted_messages.append({
            "role": msg[0],      # role: 'user' or 'assistant'
            "content": msg[1],   # message content
            "timestamp": msg[2]  # timestamp
        })
    
    return {
        "messages": formatted_messages,
        "count": len(formatted_messages)
    }


@app.post("/user/history/hide")
def hide_user_history(req: dict):
    """Mark a user's history as hidden (UI-only; does not delete DB rows)."""
    email = req.get("email")
    if not email:
        return {"success": False, "error": "Missing email"}
    try:
        hide_history(email)
        return {"success": True}
    except Exception as e:
        logger.exception("hide_user_history failed: %s", e)
        return {"success": False, "error": str(e)}
@app.get("/healthz")
def healthz():
    return {"ok": True}

@app.get("/")
def root():
    return "ok"


# =======================================================================
# MAIN ENTRY POINT
# ======================================================================
if __name__ == "__main__":
    import uvicorn
    
    # 🟡 Change port if needed: 8000 for testing, 8001 for Android
    port = 8001 if DEPLOYMENT_MODE == "android" else 8000
    
    logger.info(f"🚀 Starting {DEPLOYMENT_MODE.upper()} server on port {port}...")
    # uvicorn.run("src.api.s:app", host="0.0.0.0", port=port, reload=True)
