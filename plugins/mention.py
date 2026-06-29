import asyncio
import html
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CommandHandler, MessageHandler, CallbackQueryHandler, filters

async def is_admin(chat, user_id: int) -> bool:
    # Simplified admin check
    return True # Replace with actual admin logic if needed

async def cache_members(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.effective_chat or update.effective_chat.type == 'private':
        return
    user = update.effective_user
    if not user or user.is_bot:
        return

    # Safely get or create the members dictionary
    chat_members = context.chat_data.setdefault('members', {})
    chat_members[user.id] = {'id': user.id, 'name': user.first_name}

async def trigger_mention_panel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_chat.type == 'private':
        return await update.message.reply_text("Only for groups.")

    keyboard = [[
        InlineKeyboardButton("Start Mention", callback_data="mention_start"),
        InlineKeyboardButton("Cancel", callback_data="mention_cancel")
    ]]
    await update.message.reply_text("Mention Confirmation, Click Below button to start the process or to cancel 🚗", reply_markup=InlineKeyboardMarkup(keyboard))

async def mention_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    
    if query.data == "mention_cancel":
        context.chat_data['mention_active'] = False
        await query.edit_message_text("Cancelled.")
    elif query.data == "mention_start":
        members = list(context.chat_data.get('members', {}).values())
        if not members:
            return await query.edit_message_text("No members cached.")
        
        context.chat_data['mention_active'] = True
        await query.edit_message_text("Mentioning started...")
        asyncio.create_task(run_mentions(query.message.chat.id, members, context))

async def run_mentions(chat_id: int, members: list, context: ContextTypes.DEFAULT_TYPE) -> None:
    chunk_size = 5
    for i in range(0, len(members), chunk_size):
        if not context.chat_data.get('mention_active', False): break
        chunk = members[i:i + chunk_size]
        text = "\n".join([f"• <a href='tg://user?id={m['id']}'>{html.escape(m['name'])}</a>" for m in chunk])
        try:
            await context.bot.send_message(chat_id=chat_id, text=text, parse_mode='HTML')
        except Exception: break
        await asyncio.sleep(2.5)
    context.chat_data['mention_active'] = False

def setup(application) -> None:
    application.add_handler(CommandHandler("mention", trigger_mention_panel))
    application.add_handler(CallbackQueryHandler(mention_callback, pattern="^mention_"))
    application.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, cache_members), group=1)
