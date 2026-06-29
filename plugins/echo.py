import os
from telegram import Update
from telegram.ext import (
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes
)

async def enable_echo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Enables the echo feature for the current chat."""
    if not update.effective_chat:
        return
        
    context.chat_data['echo_enabled'] = True
    await update.message.reply_text("🗣️ Echo mode has been **enabled** for this chat.", parse_mode="Markdown")

async def disable_echo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Disables the echo feature for the current chat."""
    if not update.effective_chat:
        return
        
    context.chat_data['echo_enabled'] = False
    await update.message.reply_text("🔇 Echo mode has been **disabled** for this chat.", parse_mode="Markdown")

async def echo_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Echoes back the received message if the feature is enabled in the chat."""
    # Check if echo is enabled for this specific chat (defaults to False)
    if not context.chat_data.get('echo_enabled', False):
        return
        
    # Ensure there is text to echo
    if update.message and update.message.text:
        await update.message.reply_text(update.message.text)

def setup(application) -> None:
    """Registers the handlers with the main application."""
    # Command handlers to toggle the feature
    application.add_handler(CommandHandler("addecho", enable_echo))
    application.add_handler(CommandHandler("remecho", disable_echo))
    
    # Message handler for all text messages (excluding commands)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo_message))
