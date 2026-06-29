import os
import importlib
import logging
import traceback
import asyncio
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, PicklePersistence
from telegram.error import Conflict
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
OWNER_ID = int(os.getenv("OWNER_ID"))
LOG_CHAT_ID = int(os.getenv("LOG_CHAT_ID"))

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logging.error(msg="Exception while handling an update:", exc_info=context.error)
    if isinstance(context.error, Conflict):
        return

    tb_list = traceback.format_exception(None, context.error, context.error.__traceback__)
    tb_string = "".join(tb_list)
    error_log = f"🚨 **An Error Occurred**\n\n**Update Details:**\n`{update}`\n\n**Traceback:**\n`{tb_string[:3000]}`"
    
    try:
        await context.bot.send_message(chat_id=LOG_CHAT_ID, text=error_log, parse_mode="Markdown")
    except Exception as log_error:
        logging.error(f"Failed sending to log chat: {log_error}")

    if isinstance(update, Update) and update.effective_chat:
        try:
            temp_message = await context.bot.send_message(chat_id=update.effective_chat.id, text="❌ **An internal error occurred.**")
            await asyncio.sleep(10)
            await context.bot.delete_message(chat_id=update.effective_chat.id, message_id=temp_message.message_id)
        except Exception:
            pass

def load_plugins(application) -> None:
    plugins_dir = "plugins"
    if not os.path.exists(plugins_dir):
        os.makedirs(plugins_dir)
        return
    for filename in os.listdir(plugins_dir):
        if filename.endswith(".py") and not filename.startswith("__"):
            module = importlib.import_module(f"{plugins_dir}.{filename[:-3]}")
            if hasattr(module, "setup"):
                module.setup(application)
                logging.info(f"Successfully loaded module: {filename}")

def main() -> None:
    # Persistence enabled with concurrent-safe settings
    my_persistence = PicklePersistence(filepath="bot_data", single_file=True)
    
    application = (
        ApplicationBuilder()
        .token(BOT_TOKEN)
        .persistence(persistence=my_persistence)
        .concurrent_updates(True) # This enables the concurrent processing
        .build()
    )
    
    application.add_error_handler(error_handler)
    load_plugins(application)
    
    logging.info("Bot is now polling with full concurrency...")
    application.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
