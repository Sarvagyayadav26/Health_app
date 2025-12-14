"""
UNIFIED SERVER - Internal Testing & Android Production

This server works for both internal testing and Android production.
Use the configuration section below to switch between modes.

CONFIGURATION:
- For INTERNAL TESTING: Set DEPLOYMENT_MODE = "testing"
- For ANDROID PRODUCTION: Set DEPLOYMENT_MODE = "android"
"""

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel
import time
import logging
import bcrypt
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
# 🔴 For ANDROID PRODUCTION: Use "android"

# DEPLOYMENT_MODE = "testing"  # ← CHANGE THIS LINE FOR DIFFERENT DEPLOYMENTS
DEPLOYMENT_MODE = "android"  # ← CHANGE THIS LINE FOR DIFFERENT DEPLOYMENTS

# Set chat threshold (0 = unlimited, or set to your desired limit)
THRESHOLD_TOTAL = 0

# Logging setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(title="Mental Health RAG API - Unified")
init_db()

# ======================================================================
# CONDITIONAL IMPORTS & INITIALIZATION (based on deployment mode)
# ======================================================================
if DEPLOYMENT_MODE == "testing":
    # 🟢 INTERNAL TESTING - Direct RAG pipeline
    from src.rag.retriever import Retriever
    from src.llm.client import LLMClient
    from src.rag.embeddings import Embedder
    from src.storage.vector_store import InMemoryVectorStore as VectorStore
    
    embedder = Embedder()
    vector_store = VectorStore()
    retriever = Retriever(embedder, vector_store)
    llm_client = LLMClient()
    
    logger.info("✅ INTERNAL TESTING MODE - Direct RAG Pipeline")
    
elif DEPLOYMENT_MODE == "android":
    # 🔴 ANDROID PRODUCTION - Async RAG pipeline
    from src.android_main import initialize_all, run_rag_pipeline
    
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

# ======================================================================
# AUTH ENDPOINTS
# ======================================================================
@app.post("/auth/register")
async def register(req: RegisterRequest):
    """Register a new user"""
    try:
        if get_user(req.email):
            if DEPLOYMENT_MODE == "android":
                return {
                    "success": "User already exists, continue your healing",
                    "error": None
                }
            else:
                return JSONResponse({"error": "User already exists"}, status_code=400)
        
        create_user(req.email, req.age, req.sex, req.password)
        
        if DEPLOYMENT_MODE == "android":
            return {
                "success": "New User Created",
                "chats": 2,
                "error": None
            }
        else:
            return JSONResponse({"success": "User registered", "chats": 2})
    
    except Exception as e:
        if DEPLOYMENT_MODE == "android":
            return {"success": None, "error": str(e)}
        else:
            return JSONResponse({"error": str(e)}, status_code=500)

@app.post("/auth/login")
async def login(req: LoginRequest):
    """Login user and return usage statistics"""
    try:
        # 🟡 Android: Strip and lowercase email
        email = req.email.strip().lower() if DEPLOYMENT_MODE == "android" else req.email
        
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
    chats = user[5] if len(user) > 5 else 0  # Available chats
    print(f"[DEBUG] /chat endpoint - Email: {email}, Chats before deduction: {chats}")
    try:
        usage_total = int(usage_total) if usage_total else 0
        chats = int(chats) if chats else 0
    except:
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
            documents = retriever.retrieve(message)
            has_documents = len(documents) > 0
            
            # Deduct from available chats
            print(f"🔍 Before deduction - User: {email}, Chats: {chats}")
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute("UPDATE users SET chats = chats - 1 WHERE email = ?", (email,))
            conn.commit()
            
            # Verify the update
            cursor.execute("SELECT chats FROM users WHERE email = ?", (email,))
            new_chats = cursor.fetchone()[0]
            print(f"✅ After deduction - User: {email}, Chats: {new_chats}")
            conn.close()
            
            # Also increment usage_count for statistics
            increment_usage(email)
            
            # Generate LLM response
            reply = llm_client.generate_response([
                {"role": "user", "content": message}
            ])
            
            # Save chat history
            chat_history.add_user(message)
            chat_history.add_assistant(reply)
            save_message(email, "user", message)
            save_message(email, "assistant", reply)
            
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
            
            reply = await run_in_threadpool(run_rag_pipeline, message, chat_history)
            
            # Deduct from available chats
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute("UPDATE users SET chats = chats - 1 WHERE email = ?", (email,))
            conn.commit()
            # Fetch updated chats for debug
            cursor.execute("SELECT chats FROM users WHERE email = ?", (email,))
            updated_chats = cursor.fetchone()[0]
            print(f"[DEBUG] /chat endpoint - Email: {email}, Chats after deduction: {updated_chats}")
            conn.close()
            
            # Also increment usage_count for statistics
            increment_usage(email)
            usage_now = usage_total + 1
            
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
    "mental_health_10_chats_v1": 10
}
    
    chats_to_add = product_chats.get(product_id, 5)  # Default 5 if unknown
    
    # Step 3: Add chats to user's account
    # Note: This adds to 'chats' column which works for ALL chat types
    add_chats(email, chats_to_add)
    
    # Step 4: Get updated statistics
    updated_stats = get_usage_stats(email)
    
    # Step 5: Return success response
    return {
        "success": True,
        "chats_added": chats_to_add,
        "product_id": product_id,
        "message": f"✅ Successfully added {chats_to_add} chats to your account!",
        "remaining_chats": user[5] + chats_to_add if len(user) > 5 else chats_to_add,
        "updated_usage": updated_stats
    }

@app.get("/purchase/options")
def get_purchase_options():
    """Get available purchase options with pricing"""
    return {
        "success": True,
        "options": [
            {
                "id": "mental_health_5_chats",
                "name": "5 Chats",
                "description": "Get 5 additional chats",
                "chats": 5,
                "price": "$0.99",
                "price_usd": 0.99
            },
            {
                "id": "mental_health_10_chats",
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
    
    # Extract chats (column index 5)
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
# ✅ GET AVAILABLE CHAT SESSIONS (5 most recent)
# --------------------------------------------------------
@app.post("/chat/history/list")
async def get_chat_history_list(request: dict):
    email = request.get("email")
    if not email:
        raise HTTPException(status_code=400, detail="Email required")
    
    chat_history = ChatHistory(email)
    
    # Get last 5 chats (or create dummy ones for new users)
    messages = chat_history._messages
    
    if len(messages) == 0:
        # For new users, return 5 empty chat slots
        return {
            "chats": [
                {"id": i+1, "title": f"New Chat {i+1}", "preview": "Start a conversation...", "message_count": 0}
                for i in range(5)
            ]
        }
    
    # Group messages into chat sessions (every conversation pair)
    chat_sessions = []
    for i in range(0, min(len(messages), 10), 2):  # Get last 5 pairs (10 messages)
        if i < len(messages):
            preview = messages[i].get("content", "")[:50] + "..."
            chat_sessions.append({
                "id": i//2 + 1,
                "title": f"Chat {i//2 + 1}",
                "preview": preview,
                "message_count": 2
            })
    
    return {"chats": chat_sessions[:5]}  # Return max 5

# --------------------------------------------------------
# ✅ GET MESSAGES FROM A SPECIFIC CHAT SESSION
# --------------------------------------------------------
@app.post("/chat/history/get")
async def get_chat_history_messages(request: dict):
    """Get all messages for a user's chat history"""
    email = request.get("email")
    limit = request.get("limit", 100)  # Default to 100 messages
    
    if not email:
        raise HTTPException(status_code=400, detail="Email required")
    
    # Get messages from database
    messages = get_messages(email, limit=limit)
    
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

# ======================================================================
# MAIN ENTRY POINT
# ======================================================================
if __name__ == "__main__":
    import uvicorn
    
    # 🟡 Change port if needed: 8000 for testing, 8001 for Android
    port = 8000 if DEPLOYMENT_MODE == "testing" else 8001
    
    logger.info(f"🚀 Starting {DEPLOYMENT_MODE.upper()} server on port {port}...")
    uvicorn.run("src.api.s:app", host="0.0.0.0", port=port, reload=True)
