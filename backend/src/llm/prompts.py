from .instruction_templates import DEFAULT_INSTRUCTION

def build_messages(user_query: str, retrieved_docs: list, chat_history: list, instruction: str = None):
    """
    Build a clean, safe prompt with NO document IDs, NO chain-of-thought, 
    and NO mention of retrieval or sections.
    """
    instruction = instruction or DEFAULT_INSTRUCTION

    system_msg = {
        "role": "system",
        "content": instruction
    }

    # Summaries only — silent RAG
    combined_knowledge = ""
    for d in retrieved_docs:
        combined_knowledge += f"{d['text']}\n\n"

    # Build clean user message
    user_content = f"""
Here is some helpful background information (use it silently, without mentioning documents):

{combined_knowledge.strip()}

User question:
{user_query}

Provide a natural, empathetic answer following the guidelines. 
Do NOT mention:
- documents
- retrieval
- filenames
- sections
- IDs
- reasoning steps
- chain-of-thought
    """

    # Add chat history (assistant + user messages)
    history_messages = []
    for msg in chat_history:
        history_messages.append(msg)

    return [system_msg] + history_messages + [{"role": "user", "content": user_content}]
