import os
from dotenv import load_dotenv

dotenv_path = ".env"

# Only load .env locally, ignore missing file on Railway
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path)
else:
    print("⚠️ .env file not found — using Railway environment variables")

load_dotenv()

# OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
# OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = os.getenv("GROQ_MODEL")

EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL")

# -------------------------------
# 🗂 ROOT DATA DIR (contains docs)
# -------------------------------
DATA_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "data")
)

# -------------------------------
# 📄 DOCS DIR (this must exist)
# -------------------------------
DOCS_DIR = os.path.join(DATA_DIR, "docs")

# -------------------------------
# 💾 VECTOR STORE SAVED IN src/data
# -------------------------------
VECTOR_STORE_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "data", "vector_store.index.npz")
)

CHAT_HISTORY_PATH = os.path.join(DATA_DIR, "chat_history.json")

# Number of past messages to include from user chat history for RAG context
# Can be overridden via environment variable `CHAT_HISTORY_WINDOW`
CHAT_HISTORY_WINDOW = int(os.getenv("CHAT_HISTORY_WINDOW", "10"))

# --------------------------------------------------------
# ✅ NEW: Chat history folder for per-user chat storage
# (You requested: "keep code intact and add additional code with comments")
# --------------------------------------------------------
CHAT_HISTORY_DIR = os.path.join(DATA_DIR, "chat_history")
os.makedirs(CHAT_HISTORY_DIR, exist_ok=True)   # ensure folder exists
