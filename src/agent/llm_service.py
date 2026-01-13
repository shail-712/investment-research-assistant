from google.genai import Client
from google.genai.types import GenerateContentConfig
from dotenv import load_dotenv
import os

class LLMService:
    def __init__(self):
        load_dotenv()
        api_key = os.getenv("GEMINI_API_KEY")

        if not api_key:
            raise ValueError("GEMINI_API_KEY is missing in .env")

        self.client = Client(api_key=api_key)

        self.config = GenerateContentConfig(
            max_output_tokens=1024,
            temperature=0.7,
        )

        # Use the latest stable flash model
        self.model = "models/gemini-2.5-flash"

    def generate(self, prompt: str) -> str:
        try:
            response = self.client.models.generate_content(
                model=self.model,
                config=self.config,
                contents=prompt,
            )
            return response.text
        except Exception as e:
            return f"[LLM ERROR] {str(e)}"
