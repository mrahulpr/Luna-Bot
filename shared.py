# shared.py
import os
import dns.resolver

# --- 🚨 THE BULLETPROOF DNS FIX 🚨 ---
# Force Python to use Google's and Cloudflare's public DNS servers
# This completely bypasses the broken 127.0.0.53 resolver on your host.
dns.resolver.default_resolver = dns.resolver.Resolver(configure=False)
dns.resolver.default_resolver.nameservers = ['8.8.8.8', '1.1.1.1']
# -------------------------------------

from motor.motor_asyncio import AsyncIOMotorClient

# Get Environment Variables
BOT_TOKEN = os.getenv("BOT_TOKEN", "")

# ... (the rest of your existing shared.py code remains exactly the same below here) ...

try:
    OWNER_ID = int(os.getenv("OWNER_ID", "0"))
except ValueError:
    OWNER_ID = 0

try:
    LOG_CHAT_ID = int(os.getenv("LOG_CHAT_ID", "0"))
except ValueError:
    LOG_CHAT_ID = 0

# Setup MongoDB
# Database Setup



MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
db_client = AsyncIOMotorClient(MONGO_URI)

db = db_client["QuizBotDB"]
# Collections
admins_col = db["admins"]
quizzes_col = db["quizzes"]
settings_col = db["settings"]

progress_col = db["progress"] 
# ConversationHandler States for Admin panel
(
    WAITING_ADMIN_ID,
    WAITING_QUIZ_TOPIC,
    WAITING_QUIZ_QUESTION,
    WAITING_QUIZ_ANSWER,
    WAITING_INTERVAL,
) = range(5)

# Dictionary to hold the state of live playing quizzes in multiple chats
# Structure: { chat_id: { "topic": str, "questions": list, "current_index": int, "solved_by": set, "timer_task": Task, "is_active": bool } }
ACTIVE_QUIZZES = {}

async def is_admin(user_id: int) -> bool:
    """Check if a user is the owner or an assigned admin."""
    if user_id == OWNER_ID:
        return True
    admin_doc = await admins_col.find_one({"user_id": user_id})
    return bool(admin_doc)

async def log_error(context, error_msg: str, exc: Exception = None):
    """Sends detailed error logs directly to the Log Chat."""
    if not LOG_CHAT_ID:
        return
    full_err = f"⚠️ *Quiz System Error*\n\n{error_msg}"
    if exc:
        full_err += f"\n\n`{type(exc).__name__}: {str(exc)}`"
    try:
        await context.bot.send_message(chat_id=LOG_CHAT_ID, text=full_err, parse_mode="Markdown")
    except Exception:
        pass # Fail silently if the log chat itself is invalid

def setup(application) -> None:
    # Dummy setup so dynamic loaders don't crash if they load this file by mistake.
    pass
