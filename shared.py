# shared.py
import os
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

load_dotenv()

# Environment Variables
BOT_TOKEN = os.getenv("BOT_TOKEN")
OWNER_ID = int(os.getenv("OWNER_ID"))
LOG_CHAT_ID = int(os.getenv("LOG_CHAT_ID"))
MONGO_URI = os.getenv("MONGO_URI")

# Database Setup
db_client = AsyncIOMotorClient(MONGO_URI)
db = db_client["QuizBotDB"]
admins_col = db["admins"]
quizzes_col = db["quizzes"]
settings_col = db["settings"]

# In-Memory States
# Tracks what an admin is currently adding (e.g., waiting for question text)
ADMIN_STATES = {} 

# Tracks active quizzes in groups
# Format: {chat_id: {"topic": str, "questions": list, "current_index": int, "waiting_for_next": bool}}
ACTIVE_QUIZZES = {} 

async def log_error(client, error_message: str):
    """Utility to send errors to the log chat."""
    try:
        await client.send_message(LOG_CHAT_ID, f"❌ **Error Occurred:**\n\n`{error_message}`")
    except Exception as e:
        print(f"Failed to log error: {e}")
