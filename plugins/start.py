import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
    ContextTypes
)

async def enable_echo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Enables echo or prompts to disable if already active."""
    if not update.effective_chat:
        return
        
    is_enabled = context.chat_data.get('echo_enabled', False)
    
    if is_enabled:
        keyboard = [
            [
                InlineKeyboardButton("Yes, disable it", callback_data="echo_disable"),
                InlineKeyboardButton("No, cancel", callback_data="echo_cancel")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "Echo is already enabled in this chat. Do you want to disable it?", 
            reply_markup=reply_markup
        )
        return

    context.chat_data['echo_enabled'] = True
    await update.message.reply_text("🗣️ Echo mode enabled.")

async def disable_echo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Disables echo or alerts if already inactive."""
    if not update.effective_chat:
        return
        
    is_enabled = context.chat_data.get('echo_enabled', False)
    
    if not is_enabled:
        await update.message.reply_text("🔇 Echo mode is already disabled in this chat.")
        return

    context.chat_data['echo_enabled'] = False
    await update.message.reply_text("🔇 Echo mode disabled.")

async def echo_button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles inline button presses for the echo toggle."""
    query = update.callback_query
    await query.answer()
    
    if query.data == "echo_disable":
        context.chat_data['echo_enabled'] = False
        await query.edit_message_text("🔇 Echo mode has been disabled.")
    elif query.data == "echo_cancel":
        await query.edit_message_text("Action cancelled. Echo remains active.")

async def echo_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Copies all text and media back to the chat without a forward tag."""
    if not context.chat_data.get('echo_enabled', False):
        return
        
    if update.message:
        # copy() duplicates the message (text, photo, video, etc.) without the forward header
        await update.message.copy(chat_id=update.effective_chat.id)

def setup(application) -> None:
    """Registers the handlers with the main application."""
    application.add_handler(CommandHandler("addecho", enable_echo))
    application.add_handler(CommandHandler("remecho", disable_echo))
    
    # Handle the inline buttons specifically for echo
    application.add_handler(CallbackQueryHandler(echo_button_callback, pattern="^echo_"))
    
    # Filter ALL messages except commands to catch media, stickers, documents, etc.
    application.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, echo_message))
