from telegram import Update
from telegram.ext import CommandHandler, ContextTypes

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Responds to the start command."""
    await update.message.reply_text("Hello! The modular architecture is active.")

def setup(application) -> None:
    """Registers handlers to the main application workflow."""
    application.add_handler(CommandHandler("start", start_command))
