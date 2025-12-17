
import logging
import groq
from groq import Groq
import src.utils.config as config
import os

# Initialize logger for this module
logger = logging.getLogger("backend")

# Debug info about groq package (debug-level, will not appear unless logging set to DEBUG)
logger.debug("runtime debug: groq package version = %s", getattr(groq, "__version__", "unknown"))


class LLMClient:
    def __init__(self, model_name=None):
        # Support a debug/no-LLM mode via env var `DEBUG_NO_LLM=1`
        self.debug_mode = os.environ.get("DEBUG_NO_LLM", "0") == "1"
        self.api_key = config.GROQ_API_KEY

        if self.debug_mode:
            logger.info("LLMClient running in DEBUG_NO_LLM mode — returning canned responses")
            self.client = None
            self.model = model_name or config.GROQ_MODEL
            return

        if not self.api_key:
            raise ValueError("GROQ_API_KEY is missing in .env file")

        # Initialize Groq client
        self.client = Groq(api_key=self.api_key)
        self.model = model_name or config.GROQ_MODEL

    def generate_response(self, messages):
        try:
            if getattr(self, "debug_mode", False):
                # History-aware debug reply: try to reference previous user messages
                try:
                    # messages is expected to be a list of dicts with 'role' and 'content'
                    user_msgs = [m.get("content", "") for m in messages if m.get("role") == "user"]
                    # keep reasonable length
                    user_msgs = [u if len(u) <= 1000 else u[:1000] + "..." for u in user_msgs]
                    if len(user_msgs) >= 2:
                        prev = user_msgs[-2]
                        last = user_msgs[-1]
                        return f"[DEBUG_REPLY] Previously you said: \"{prev}\". Now you said: \"{last}\""
                    elif len(user_msgs) == 1:
                        last = user_msgs[-1]
                        return f"[DEBUG_REPLY] I remember: \"{last}\""
                    else:
                        return "[DEBUG_REPLY] No user history available"
                except Exception:
                    logger.exception("Error while building debug reply")
                    return "[DEBUG_REPLY] (debug fallback)"

            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.7,
                max_tokens=500
            )

            # If Groq returned invalid content
            if not response or not hasattr(response, "choices") or len(response.choices) == 0:
                try:
                    logger.error("RAW GROQ ERROR: %s", response.error)
                except Exception:
                    logger.error("RAW GROQ RESPONSE: %s", response)
                return None

            content = response.choices[0].message.content
            return content or ""

        except Exception as e:
            logger.exception("Error in LLM.generate: %s", e)
            return None

