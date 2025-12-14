import os
from src.rag.embeddings import Embedder
from src.storage.vector_store import InMemoryVectorStore
from src.rag.indexer import Indexer
from src.rag.doc_loader import load_text_documents
import src.utils.config as config

def build_vector_store():
    print("🔨 Building vector store offline...")

    embedder = Embedder()
    store = InMemoryVectorStore()
    indexer = Indexer(embedder, store)

    docs = load_text_documents(config.DOCS_DIR)

    indexer.index_documents(docs)
    print("✅ Saved to:", config.VECTOR_STORE_PATH)

if __name__ == "__main__":
    build_vector_store()
