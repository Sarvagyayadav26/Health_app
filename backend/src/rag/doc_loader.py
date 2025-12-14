import os

def load_text_documents(doc_dir):
    docs = []
    for filename in os.listdir(doc_dir):
        if not filename.endswith(".txt"):
            continue

        path = os.path.join(doc_dir, filename)
        with open(path, "r", encoding="utf-8") as f:
            text = f.read().strip()

        lines = text.split("\n")
        
        # Split file into sections by topic headers
        sections = []
        current_section = {"topics": None, "content": []}
        
        for line in lines:
            line_stripped = line.strip()
            line_lower = line_stripped.lower()
            
            # Check if this line is a topic header (supports #topic:, topic:, #topic1:, topic1:, topic 20:, etc.)
            # Handles: #Topic1:, Topic4:, Topic 20:, etc.
            is_topic_header = (
                (line_lower.startswith("#topic") or line_lower.startswith("topic")) 
                and ":" in line_lower
            )
            if is_topic_header:
                # Save previous section if it has content
                if current_section["topics"] is not None and current_section["content"]:
                    sections.append(current_section)
                
                # Start new section
                # Extract topics after the colon (handles #topic: or #topic1:, etc.)
                colon_idx = line_lower.index(":")
                topics_str = line_lower[colon_idx + 1:].strip()
                topics = [t.strip() for t in topics_str.split(",") if t.strip()]
                current_section = {"topics": topics, "content": []}
            else:
                # Add line to current section
                current_section["content"].append(line)
        
        # Don't forget the last section
        if current_section["topics"] is not None and current_section["content"]:
            sections.append(current_section)
        
        # If no topic headers found, treat entire file as one document
        if not sections:
            # default topic = filename
            topics = [filename.replace(".txt", "")]
            text_content = text
            docs.append({
                "id": filename,
                "text": text_content,
                "metadata": {
                    "source": filename,
                    "topics": topics
                }
            })
        else:
            # Create a document for each section
            for idx, section in enumerate(sections):
                text_content = "\n".join(section["content"]).strip()
                if text_content:  # Only add non-empty sections
                    doc_id = f"{filename}#section{idx+1}" if len(sections) > 1 else filename
                    docs.append({
                        "id": doc_id,
                        "text": text_content,
                        "metadata": {
                            "source": filename,
                            "topics": section["topics"]
                        }
                    })

    return docs
