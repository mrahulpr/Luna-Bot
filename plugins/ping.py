import time
import asyncio
import speedtest
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import CommandHandler, CallbackQueryHandler, ContextTypes
from telegram.constants import ParseMode
from telegram.error import BadRequest

async def ping_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles the /ping command and displays response time."""
    start_time = time.time()
    message = await update.message.reply_text("🏓 Pinging...")
    end_time = time.time()
    ping_ms = int((end_time - start_time) * 1000)

    keyboard = [
        [InlineKeyboardButton("🚀 Speed Test", callback_data="test_speed")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await message.edit_text(
        f"✅ <b>Pong!</b>\n📡 <b>Ping:</b> {ping_ms} ms",
        parse_mode=ParseMode.HTML,
        reply_markup=reply_markup
    )

async def test_speed_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles the inline button callback to run a speed test."""
    query = update.callback_query
    await query.answer("Starting speed test. This might take a minute...", show_alert=False)

    msg = await query.edit_message_text("• 🚀 Running speed test...\n• Please wait ⏳")

    loop = asyncio.get_running_loop()
    animation_task = asyncio.create_task(animate_loading(msg))

    try:
        results = await loop.run_in_executor(None, run_speed_test)
        
        await msg.edit_text(
            f"📊 <b>Speed Test Results</b>\n\n"
            f"🖥 <b>Server:</b> <code>{results['server']}</code>\n"
            f"📡 <b>Ping:</b> <code>{results['ping']} ms</code>\n"
            f"⬇️ <b>Download:</b> <code>{results['download']} Mbps</code>\n"
            f"⬆️ <b>Upload:</b> <code>{results['upload']} Mbps</code>",
            parse_mode=ParseMode.HTML
        )
    except Exception as e:
        await msg.edit_text(f"❌ <b>Speed test failed:</b>\n<code>{str(e)}</code>", parse_mode=ParseMode.HTML)
    finally:
        if not animation_task.done():
            animation_task.cancel()

async def animate_loading(msg) -> None:
    """Animates the loading message."""
    dots = [".", "..", "...", "...."]
    i = 0
    while True:
        await asyncio.sleep(2.0)
        try:
            await msg.edit_text(f"• 🚀 Running speed test {dots[i % len(dots)]}\n• Please wait ⏳")
            i += 1
        except BadRequest:
            pass
        except Exception:
            break

def run_speed_test() -> dict:
    """Synchronous function to perform the actual speed test."""
    st = speedtest.Speedtest()
    st.get_best_server()
    st.download()
    st.upload()
    
    download = round(st.results.download / 1_000_000, 2)
    upload = round(st.results.upload / 1_000_000, 2)
    ping = round(st.results.ping, 2)
    server_name = st.results.server.get("name", "Unknown")
    
    return {
        "download": download,
        "upload": upload,
        "ping": ping,
        "server": server_name
    }

def setup(application) -> None:
    """Dynamically loads the plugin handlers into the main bot application."""
    application.add_handler(CommandHandler("ping", ping_command))
    application.add_handler(CallbackQueryHandler(test_speed_callback, pattern="^test_speed$"))
