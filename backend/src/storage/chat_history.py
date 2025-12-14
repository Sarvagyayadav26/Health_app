import json
import os
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
