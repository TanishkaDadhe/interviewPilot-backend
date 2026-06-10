from dotenv import load_dotenv
import os

load_dotenv()

# Database
MONGODB_URI = os.getenv("MONGODB_URI")

# AI
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# App
PORT = int(os.getenv("PORT", 8080))
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")

JWT_SECRET = os.getenv("JWT_SECRET")