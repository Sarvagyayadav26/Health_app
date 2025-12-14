import os

# 🔥 Debug print must come FIRST
import groq
print("🚩 runtime debug: groq package version =", getattr(groq, "__version__", "unknown"))

from groq import Groq
import src.utils.config as config

class LLMClient:
    def __init__(self, model_name=None):
        self.api_key = config.GROQ_API_KEY
        if not self.api_key:
            raise ValueError("GROQ_API_KEY is missing in .env file")

        # No patched http_client, use plain Groq
        self.client = Groq(api_key=self.api_key)
        self.model = model_name or config.GROQ_MODEL

    def generate_response(self, messages):
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.7,
                max_tokens=500
            )

            # If Groq returned 400 or invalid content
            # Invalid or empty choices
            if not response or not hasattr(response, "choices") or len(response.choices) == 0:
                try:
                    print("❌ RAW GROQ ERROR:", response.error)
                except:
                    print("❌ RAW GROQ RESPONSE:", response)
                return None


            content = response.choices[0].message.content
            return content or ""

        except Exception as e:
            print(f"❌ Error in LLM.generate: {e}")
            return None
        
