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
from sqlite3 import IntegrityError
import sqlite3

from src.storage.chat_history import ChatHistory
from src.storage.user_db import (
    init_db, create_user, get_user, save_message,
    increment_usage, get_usage_stats, add_chats, get_messages, DB_PATH
)

# ======================================================================
# 🔧 CONFIGURATION - CHANGE THIS FOR TESTING VS PRODUCTION
# ======================================================================
# 🟢 For INTERNAL TESTING: Use "testing"
# 🔴 For emulator & ANDROID PRODUCTION: Use "android"

# DEPLOYMENT_MODE = "testing"  # ← CHANGE THIS LINE FOR DIFFERENT DEPLOYMENTS
DEPLOYMENT_MODE = "android"  # ← CHANGE THIS LINE FOR DIFFERENT DEPLOYMENTS

# Set chat threshold (0 = unlimited, or set to your desired limit)
THRESHOLD_TOTAL = 0

# Logging setup
logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger("backend")
logger.setLevel(logging.DEBUG)

# Initialize FastAPI app
app = FastAPI(title="Mental Health RAG API - Unified")
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
    # Accept int or string for session_id to tolerate client values like "default"
    session_id: Optional[Union[int, str]] = 1
    # Optional client-supplied short history (string) — backend should prefer DB history
    history: Optional[str] = None

class RegisterRequest(BaseModel):
    email: str
    age: int
    sex: str
    password: str

class LoginRequest(BaseModel):
    email: str
    password: str

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
            if DEPLOYMENT_MODE == "testing":
                return JSONResponse(err, status_code=409)
            return err

        try:
            create_user(email, req.age, req.sex, req.password)
            logger.info("User created: %s", req.email)
        except IntegrityError:
            logger.warning("Duplicate registration attempt (race): %s", req.email)
            err = {"error": "User already exists. Please login."}
            if DEPLOYMENT_MODE == "testing":
                return JSONResponse(err, status_code=409)
            return err
        except ValueError as ve:
            # create_user raises ValueError("user_exists") on duplicate
            if str(ve) == "user_exists":
                logger.warning("Duplicate registration attempt: %s", req.email)
                err = {"error": "User already exists. Please login."}
                if DEPLOYMENT_MODE == "testing":
                    return JSONResponse(err, status_code=409)
                return err
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
            "chats": user[5] if len(user) > 5 else 0,
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
    # Normalize session_id: accept int, numeric string, or fallback to 1 for values like "default"
    raw_sid = None
    try:
        raw_sid = getattr(req, 'session_id', None)
    except Exception:
        raw_sid = None
    # also accept camelCase if client sends sessionId
    if raw_sid is None:
        try:
            raw_sid = getattr(req, 'sessionId', None)
        except Exception:
            raw_sid = None

    session_id = 1
    try:
        if raw_sid is None:
            session_id = 1
        elif isinstance(raw_sid, int):
            session_id = raw_sid
        elif isinstance(raw_sid, str):
            # numeric string -> int, otherwise use default session 1
            if raw_sid.isdigit():
                session_id = int(raw_sid)
            else:
                session_id = 1
        else:
            session_id = int(raw_sid)
    except Exception:
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
    chats = user[5] if len(user) > 5 else 0
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

            documents = retriever.retrieve(message) if retriever else []
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

            # Deduct from available chats
            logger.debug(f"Before deduction - User: {email}, Chats: {chats}")
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute("UPDATE users SET chats = chats - 1 WHERE email = ?", (email,))
            conn.commit()
            
            # Verify the update
            cursor.execute("SELECT chats FROM users WHERE email = ?", (email,))
            new_chats = cursor.fetchone()[0]
            logger.debug(f"After deduction - User: {email}, Chats: {new_chats}")
            conn.close()
            
            # Also increment usage_count for statistics
            increment_usage(email)
            
            # Generate LLM response. Prefer passing DB history when available so debug LLM
            # can reference prior messages.
            if history_msgs:
                # Convert history_msgs to the messages format expected by LLMClient
                llm_messages = []
                for m in history_msgs:
                    llm_messages.append({"role": m.get("role", "user"), "content": m.get("content", "")})
                # append the current user message only if we did NOT pre-save it
                if not user_saved_before:
                    llm_messages.append({"role": "user", "content": message})
                reply = llm_client.generate_response(llm_messages)
            else:
                reply = llm_client.generate_response([
                    {"role": "user", "content": message}
                ])
            
            # Save chat history
            chat_history.add_user(message)
            chat_history.add_assistant(reply)
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
                    "text": d["text"],
                    "score": d["score"],
                    "metadata": d["metadata"]
                }
                for d in documents
            ]
            
            return JSONResponse({
                "reply": reply,
                "documents": documents_clean,
                "has_retrieval": has_documents,
                "usage_stats": {
                    "total": usage_total + 1
                },
                "chats": chats - 1 if chats > 0 else 0,
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

            # Fetch stored messages for this session and pass them into the RAG pipeline
            logger.debug("/chat - fetching history for email=%s session_id=%s limit=%s", email, session_id, 7)
            history_rows = get_messages(email, limit=7, session_id=session_id)
            history_msgs = [{"role": r[0], "content": r[1], "timestamp": r[2]} for r in history_rows]
            logger.debug("/chat - history_msgs count=%s preview=%s", len(history_msgs), history_msgs[:3])

            # Run RAG pipeline in threadpool; log start/end for timing
            logger.debug("/chat - running run_rag_pipeline for email=%s session_id=%s", email, session_id)
            reply = await run_in_threadpool(run_rag_pipeline, message, chat_history, history_msgs)
            logger.debug("/chat - run_rag_pipeline completed for email=%s session_id=%s reply_len=%s", email, session_id, len(reply) if isinstance(reply, str) else 0)

            # Safe deduct from available chats (avoid negatives / NULL)
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
                "error": f"Failed to generate reply: {str(e)}",
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
    product_id = req.get("product_id")
    
    # Step 1: Validate user exists
    user = get_user(email)
    if not user:
        return {
            "success": False,
            "error": "User not found",
            "chats_added": 0
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
    
    # Step 3: Add chats to user's account
    # Note: This adds to 'chats' column which works for ALL chat types
    add_chats(email, chats_to_add)

    # Re-read user to get authoritative updated chats value
    user = get_user(email)

    # Step 4: Get updated statistics
    updated_stats = get_usage_stats(email)

    # Step 5: Return success response
    remaining = user[5] + 0 if (user and len(user) > 5) else chats_to_add
    if user and len(user) > 5:
        remaining = user[5]

    return {
        "success": True,
        "chats_added": chats_to_add,
        "product_id": product_id,
        "message": f"✅ Successfully added {chats_to_add} chats to your account!",
        "remaining_chats": remaining,
        "updated_usage": updated_stats
    }


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
    
    # Extract chats (column index 5) with inline fallback
    chats = user[5] if len(user) > 5 else 0
    
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
@app.get("/healthz")
def healthz():
    return {"ok": True}

@app.get("/")
def root():
    return "ok"


# ======================================================================
# MAIN ENTRY POINT
# ======================================================================
if __name__ == "__main__":
    import uvicorn
    
    # 🟡 Change port if needed: 8000 for testing, 8001 for Android
    port = 8001 if DEPLOYMENT_MODE == "android" else 8000
    
    logger.info(f"🚀 Starting {DEPLOYMENT_MODE.upper()} server on port {port}...")
    # uvicorn.run("src.api.s:app", host="0.0.0.0", port=port, reload=False)
