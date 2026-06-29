import os
import asyncio
import html
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
)

async def is_admin(chat, user_id: int) -> bool:
    """Helper to check if a user is an admin in the chat or the global bot owner."""
    owner_id = os.getenv("OWNER_ID")
    if owner_id and user_id == int(owner_id):
        return True
        
    if chat.type == 'private':
        return True
        
    admins = await chat.get_administrators()
    return any(admin.user.id == user_id for admin in admins)

async def cache_members(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Silently cache members that send messages to build the mention list."""
    if not update.effective_chat or update.effective_chat.type == 'private':
        return
        
    user = update.effective_user
    if not user or user.is_bot:
        return

    if 'members' not in context.chat_data:
        context.chat_data['members'] = {}
        
    context.chat_data['members'][user.id] = {
        'id': user.id,
        'name': user.first_name
    }

async def trigger_mention_panel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Triggered by @all, #all, @mentionall, or /mention. Opens the panel."""
    chat = update.effective_chat
    user_id = update.effective_user.id
    
    if chat.type == 'private':
        await update.message.reply_text("This feature can only be used in groups.")
        return

    if not await is_admin(chat, user_id):
        return  # Ignore silently if a regular user tries to trigger it

    keyboard = [
        [
            InlineKeyboardButton("Start Mention", callback_data="mention_start", style="primary"),
            InlineKeyboardButton("Cancel", callback_data="mention_cancel", style="danger")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "**Mention Panel**\nClick below to start mentioning all cached members.",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )

async def mention_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles the start and cancel button clicks."""
    query = update.callback_query
    user_id = query.from_user.id
    chat = query.message.chat
    
    if not await is_admin(chat, user_id):
        await query.answer("Only admins can activate this command.", show_alert=True)
        return

    await query.answer() 
    data = query.data
    
    if data == "mention_cancel":
        context.chat_data['mention_active'] = False
        await query.edit_message_text("Mentioning process has been cancelled by an admin.")
        return
        
    if data == "mention_start":
        if context.chat_data.get('mention_active'):
            await query.answer("Mentioning is already in progress!", show_alert=True)
            return
            
        members = list(context.chat_data.get('members', {}).values())
        if not members:
            await query.edit_message_text("No members cached yet. Group members need to send messages first.")
            return

        context.chat_data['mention_active'] = True
        await query.edit_message_text("Mentioning started... Admins can use `/cancel` to stop.")
        
        # Start background task to mention users without blocking the application
        asyncio.create_task(run_mentions(chat.id, members, context))

async def run_mentions(chat_id: int, members: list, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Background task that loops and sends the actual mentions."""
    chunk_size = 5
    for i in range(0, len(members), chunk_size):
        if not context.chat_data.get('mention_active', False):
            break  # Break loop if an admin cancelled
            
        chunk = members[i:i + chunk_size]
        text_lines = []
        
        for m in chunk:
            safe_name = html.escape(m['name'])
            text_lines.append(f"• <a href='tg://user?id={m['id']}'>{safe_name}</a>")
            
        text = "\n".join(text_lines)
        
        try:
            await context.bot.send_message(chat_id=chat_id, text=text, parse_mode='HTML')
        except Exception:
            # Let unhandled exceptions bubble to global reporter, but stop loop to avoid flood blocks
            break
            
        await asyncio.sleep(2.5)  # Throttle to prevent Telegram API flood limits
        
    context.chat_data['mention_active'] = False

async def cmd_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Command to forcefully cancel an ongoing mention loop."""
    chat = update.effective_chat
    user_id = update.effective_user.id
    
    if chat.type == 'private':
        return
        
    if not await is_admin(chat, user_id):
        return

    if context.chat_data.get('mention_active'):
        context.chat_data['mention_active'] = False
        await update.message.reply_text("Mentioning process stopped.")
    else:
        await update.message.reply_text("No mention process is currently active.")

def setup(application) -> None:
    """Dynamically loaded by main.py to register handlers."""
    
    # 1. Regex handler for text-based keywords
    regex_pattern = r'^(?i)(@all|#all|@mentionall)'
    application.add_handler(MessageHandler(filters.Regex(regex_pattern), trigger_mention_panel))
    
    # 2. Command handler for /mention
    application.add_handler(CommandHandler("mention", trigger_mention_panel))
    
    # 3. Command handler for /cancel
    application.add_handler(CommandHandler("cancel", cmd_cancel))
    
    # 4. Callback query handler for the panel buttons
    application.add_handler(CallbackQueryHandler(mention_callback, pattern="^mention_"))
    
    # 5. Background member cacher (Group 1 prevents it from blocking other message handlers)
    application.add_handler(MessageHandler(filters.ALL, cache_members), group=1)
