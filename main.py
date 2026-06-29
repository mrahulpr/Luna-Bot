import os
import sys
import importlib
import logging
import traceback
import asyncio
from telegram import Update
from telegram.ext import Application, ContextTypes, ApplicationBuilder
from telegram.ext import PicklePersistence
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
    
    error_log = (
        f"🚨 **An Error Occurred**\n\n"
        f"**Update Details:**\n`{update}`\n\n"
        f"**Traceback:**\n`{tb_string[:3000]}`"
    )
    
    try:
        await context.bot.send_message(chat_id=LOG_CHAT_ID, text=error_log, parse_mode="Markdown")
    except Exception as log_error:
        logging.error(f"Failed sending to log chat: {log_error}")

    if isinstance(update, Update) and update.effective_chat:
        try:
            temp_message = await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="❌ **An internal error occurred.**"
            )
            await asyncio.sleep(10)
            await context.bot.delete_message(
                chat_id=update.effective_chat.id, 
                message_id=temp_message.message_id
            )
        except Exception:
            pass

def load_plugins(application: Application) -> None:
    plugins_dir = "plugins"
    if not os.path.exists(plugins_dir):
        os.makedirs(plugins_dir)
        return

    for filename in os.listdir(plugins_dir):
        if filename.endswith(".py") and not filename.startswith("__"):
            module_name = f"{plugins_dir}.{filename[:-3]}"
            module = importlib.import_module(module_name)
            if hasattr(module, "setup"):
                module.setup(application)
                logging.info(f"Successfully loaded module: {filename}")

def main() -> None:
    """Starts the application with concurrency enabled."""
    
    # Enable concurrent_updates to allow multiple commands to run at once
    application = (
        ApplicationBuilder()
        .token(BOT_TOKEN)
        .concurrent_updates(True) 
        .build()
    )
    
    application.add_error_handler(error_handler)
    load_plugins(application)
    
    logging.info("Bot is now polling with concurrency enabled...")
    application.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
