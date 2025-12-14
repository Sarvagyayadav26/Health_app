import os
import datetime

from src.rag.embeddings import Embedder
from src.storage.vector_store import InMemoryVectorStore
from src.rag.indexer import Indexer
from src.rag.retriever import Retriever
from src.storage.chat_history import ChatHistory
from src.llm.client import LLMClient
from src.llm.prompts import build_messages
from src.llm.instruction_templates import DEFAULT_INSTRUCTION
from src.rag.doc_loader import load_text_documents
import src.utils.config as config


def save_chat_to_file(user_input, assistant_output):
    """Save chat to text file with timestamp."""
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    folder = os.path.join(os.path.dirname(__file__), "saved_chats")
    os.makedirs(folder, exist_ok=True)

    filepath = os.path.join(folder, f"chat_{timestamp}.txt")
    with open(filepath, "w", encoding="utf-8") as f:
        f.write("User: " + user_input + "\n\n")
        f.write("Assistant: " + assistant_output + "\n")

    print(f"\n[Chat saved at: {filepath}]")


def main():
    # Initialize components
    embedder = Embedder()
    vector_store = InMemoryVectorStore()
    vector_store.load()

    indexer = Indexer(embedder, vector_store)

    # Always re-index documents to pick up new sections/changes
    # print("📚 Loading and indexing documents...")
    docs = load_text_documents(os.path.join(config.DATA_DIR, "docs"))
    # Clear existing data and re-index
    vector_store.ids = []
    vector_store.texts = []
    vector_store.metadatas = []
    vector_store.embeddings = None
    indexer.index_documents(docs)
    print(f"✅ Indexed {len(docs)} document sections")

    retriever = Retriever(embedder, vector_store)
    chat_history = ChatHistory()
    llm = LLMClient()

    print("RAG CLI ready. Type 'exit' to quit.")

    while True:
        try:
            user_q = input("\nYou: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nExiting.")
            break

        if not user_q:
            continue
        if user_q.lower() in ("exit", "quit"):
            break

        chat_history.add_user(user_q)

        # Run retrieval
        retrieved = retriever.retrieve(user_q, top_k=3)
        
        # Display retrieved documents and sections
        if len(retrieved) > 0:
            print("\n📄 Retrieved Documents/Sections:")
            for idx, doc in enumerate(retrieved, 1):
                doc_id = doc.get("id", "unknown")
                topics = doc.get("metadata", {}).get("topics", [])
                source = doc.get("metadata", {}).get("source", "unknown")
                text_preview = doc.get("text", "")[:100].replace("\n", " ")
                score = doc.get("score", 0.0)
                
                print(f"  {idx}. Document: {source}")
                print(f"     Section ID: {doc_id}")
                print(f"     Topics: {', '.join(topics)}")
                print(f"     Similarity Score: {score:.4f}")
                print(f"     Preview: {text_preview}...")
                print()
        else:
            print("\n⚠️  No matching documents found for this query.")

        # 1️⃣ — FALLBACK: No matching topical documents found
        if len(retrieved) == 0:
            # Step 1: Simple explanation
            simple_explain_msg = [{
                "role": "user",
                "content": f"Explain this in very simple words: '{user_q}'"
            }]
            simple_explanation = llm.generate(simple_explain_msg)

            final_answer = (
                "\n\nI don't have a solution yet. Try consulting a doctor until we find one."+simple_explanation.strip()
            )

            print("\nAssistant:\n", final_answer)
            chat_history.add_assistant(final_answer)
            save_chat_to_file(user_q, final_answer)
            continue

        # 2️⃣ — NORMAL RAG PIPELINE: Matching doc(s) found
        try:
            messages = build_messages(
                user_q,
                retrieved,
                chat_history.last_n(6),
                instruction=DEFAULT_INSTRUCTION
            )
            
            # Debug: Show what's being sent to LLM
            print("\n🔍 Content sent to LLM:")
            print("=" * 60)
            for msg in messages:
                role = msg.get("role", "unknown")
                content = msg.get("content", "")
                # Truncate very long content for display
                if len(content) > 500:
                    content_preview = content[:500] + "... [truncated]"
                else:
                    content_preview = content
                print(f"\n[{role.upper()}]:")
                print(content_preview)
            print("=" * 60)
            
            answer = llm.generate(messages)
            
            # Check if answer is empty or None
            if not answer or answer.strip() == "":
                print("\n⚠️  WARNING: LLM returned empty response!")
                answer = "I apologize, but I'm having trouble generating a response. Please try rephrasing your question."

        except Exception as e:
            print(f"\n❌ ERROR during LLM generation: {e}")
            answer = "RAG failed internally. Error: " + str(e)

        print("\nAssistant:\n", answer)
        chat_history.add_assistant(answer)
        save_chat_to_file(user_q, answer)


if __name__ == "__main__":
    main()
