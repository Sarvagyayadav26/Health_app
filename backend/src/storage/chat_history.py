import json
import os
import re
from difflib import SequenceMatcher
import src.utils.config as config
from datetime import datetime

class ChatHistory:
    def __init__(self, email: str):
        # Each user gets their own JSON file
        self.path = os.path.join(config.CHAT_HISTORY_DIR, f"{email}.json")
        os.makedirs(config.CHAT_HISTORY_DIR, exist_ok=True)
        self._messages = []
        self.load()

    def add_user(self, text: str):
        self._messages.append({
            "role": "user",
            "content": text,
            "time": datetime.utcnow().isoformat()
        })
        self.save()

    def add_assistant(self, text: str):
        self._messages.append({
            "role": "assistant",
            "content": text,
            "time": datetime.utcnow().isoformat()
        })
        self.save()

    def last_n(self, n=6):
        return [
            {"role": msg["role"], "content": msg["content"]}
            for msg in self._messages[-n:]
        ]

    def save(self):
        # Skip near-duplicate consecutive messages to avoid noise
        try:
            deduped = []
            prev_norm = None
            for msg in self._messages:
                content = msg.get("content", "") if isinstance(msg, dict) else str(msg)
                # normalize: lowercase, remove punctuation, collapse whitespace
                norm = re.sub(r"[^\w\s]", "", content.lower()).strip()
                norm = re.sub(r"\s+", " ", norm)

                if prev_norm is not None:
                    # exact match
                    if norm == prev_norm:
                        continue
                    # high similarity -> treat as duplicate
                    try:
                        if SequenceMatcher(None, norm, prev_norm).ratio() >= 0.9:
                            continue
                    except Exception:
                        pass

                deduped.append(msg)
                prev_norm = norm

            self._messages = deduped
        except Exception:
            # If dedupe fails for any reason, keep original list
            pass

        # Guard: prevent unbounded in-memory growth by trimming old messages
        try:
            # Keep a reasonable multiple of the RAG window to preserve context.
            max_keep = max(100, config.CHAT_HISTORY_WINDOW * 5)
        except Exception:
            max_keep = 200

        if len(self._messages) > max_keep:
            # preserve most recent messages
            self._messages = self._messages[-max_keep:]

        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(self._messages, f, ensure_ascii=False, indent=2)

    def load(self):
        if os.path.exists(self.path):
            try:
                with open(self.path, "r", encoding="utf-8") as f:
                    data = json.load(f)

                    # Convert old format if needed
                    for msg in data:
                        if "text" in msg:
                            msg["content"] = msg.pop("text")

                    self._messages = data
            except:
                self._messages = []
