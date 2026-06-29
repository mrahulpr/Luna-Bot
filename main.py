import os
import sys
import importlib
import logging
import traceback
import asyncio
from telegram import Update
from telegram.ext import Application, ContextTypes


from dotenv import load_dotenv
load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
OWNER_ID = int(os.getenv("OWNER_ID"))
LOG_CHAT_ID = int(os.getenv("LOG_CHAT_ID"))

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Universal error reporting system with loop protection."""
    
    # 1. Always log the error locally to your VPS console
    logging.error(msg="Exception while handling an update:", exc_info=context.error)

    # 2. CRITICAL FIX: If the error is a 409 Conflict, exit immediately.
    # This prevents the bot from making API calls that cause infinite log loops.
    if isinstance(context.error, Conflict):
        return

    # 3. Process tracebacks only for other types of errors
    tb_list = traceback.format_exception(None, context.error, context.error.__traceback__)
    tb_string = "".join(tb_list)
    
    error_log = (
        f"🚨 **An Error Occurred**\n\n"
        f"**Update Details:**\n`{update}`\n\n"
        f"**Traceback:**\n`{tb_string[:3000]}`"
    )
    
    # Send permanent details to the log chat
    try:
        await context.bot.send_message(chat_id=LOG_CHAT_ID, text=error_log, parse_mode="Markdown")
    except Exception as log_error:
        logging.error(f"Failed sending to log chat: {log_error}")

    # Send temporary notice to the point of happening and auto-delete
    if isinstance(update, Update) and update.effective_chat:
        try:
            temp_message = await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="❌ **An internal error occurred.** This message will self-destruct in 10 seconds."
            )
            # Wait 10 seconds then delete the alert
            await asyncio.sleep(10)
            await context.bot.delete_message(
                chat_id=update.effective_chat.id, 
                message_id=temp_message.message_id
            )
        except Exception as delete_error:
            logging.error(f"Failed to handle ephemeral message: {delete_error}")

def load_plugins(application: Application) -> None:
    """Dynamically loads modules from the plugins directory."""
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
    """Starts the application."""
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Register global error handling
    application.add_error_handler(error_handler)
    
    # Dynamic plugin loading
    load_plugins(application)
    
    logging.info("Bot is now polling...")
    # This prevents the bot from answering old messages on startup
    application.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
