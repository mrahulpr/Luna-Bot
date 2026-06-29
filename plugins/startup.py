import os
import time
import platform
import psutil
from telegram.ext import ContextTypes

# Retrieve log chat ID from environment variables
LOG_CHAT_ID = int(os.getenv("LOG_CHAT_ID"))

async def send_startup_msg(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Calculates diagnostics and logs them."""
    sys_os = platform.system()
    release = platform.release()
    uptime_sec = int(time.time() - psutil.boot_time())
    
    m, s = divmod(uptime_sec, 60)
    h, m = divmod(m, 60)
    d, h = divmod(h, 24)
    uptime_str = f"{d}d {h}h {m}m {s}s"
    
    ping_start = time.time()
    try:
        await context.bot.get_me()
        ping_time = round((time.time() - ping_start) * 1000)
    except:
        ping_time = "Timeout"

    msg = (
        f"✅ **System Online**\n\n"
        f"🖥 **OS:** `{sys_os} {release}`\n"
        f"⏳ **Server Uptime:** `{uptime_str}`\n"
        f"🏓 **Bot API Ping:** `{ping_time}ms`"
    )
    
    await context.bot.send_message(chat_id=LOG_CHAT_ID, text=msg, parse_mode="Markdown")

def setup(application) -> None:
    """Schedules the diagnostic panel execution right after startup."""
    application.job_queue.run_once(send_startup_msg, 1)
