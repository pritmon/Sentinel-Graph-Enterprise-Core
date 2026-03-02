import os
from dotenv import load_dotenv

load_dotenv()
print("GEMINI_API_KEY:", os.environ.get("GEMINI_API_KEY"))
print("GOOGLE_API_KEY:", os.environ.get("GOOGLE_API_KEY"))
