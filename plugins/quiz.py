from bson import ObjectId
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes, ConversationHandler
)
# Added progress_col to the import list below
from shared import (
    is_admin, OWNER_ID, admins_col, quizzes_col, settings_col, progress_col, log_error,
    WAITING_ADMIN_ID, WAITING_QUIZ_TOPIC, WAITING_QUIZ_QUESTION, WAITING_QUIZ_ANSWER, WAITING_INTERVAL
)

async def quiz_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Main entry point for any user requesting the quiz panel."""
    keyboard = [
        [
            InlineKeyboardButton("▶️ Start Quiz", callback_data="start_quiz_menu", style="success"),
            InlineKeyboardButton("⚙️ Admin Only", callback_data="admin_menu", style="primary")
        ]
    ]
    await update.message.reply_text(
        "🎯 *Welcome to the Quiz System*\n\nPlease choose an option below:", 
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )

async def admin_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Verifies admin status and displays the Admin panel."""
    query = update.callback_query
    if not await is_admin(query.from_user.id):
        await query.answer("❌ Only admins can use this.", show_alert=True)
        return
    await query.answer()
    
    # Added "Reset Group Progress" button
    keyboard = [
        [InlineKeyboardButton("➕ Add Admin", callback_data="admin_add_admin", style="primary"),
         InlineKeyboardButton("📝 Add Quiz", callback_data="admin_add_quiz", style="primary")],
        [InlineKeyboardButton("🗑 Delete Quiz", callback_data="admin_delete_quiz", style="danger"),
         InlineKeyboardButton("⏱ Set Interval", callback_data="admin_set_interval", style="primary")],
        [InlineKeyboardButton("🔄 Reset Group Progress", callback_data="admin_reset_progress", style="primary")],
        [InlineKeyboardButton("❌ Cancel", callback_data="admin_cancel", style="danger")]
    ]
    await query.edit_message_text("⚙️ *Admin Panel Options:*", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

# --- 1. ADD ADMIN FLOW ---
async def add_admin_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query.from_user.id != OWNER_ID:
        await query.answer("❌ Only the Owner can assign new admins.", show_alert=True)
        return ConversationHandler.END
    await query.answer()
    keyboard = [[InlineKeyboardButton("❌ Cancel Process", callback_data="admin_cancel", style="danger")]]
    await query.edit_message_text("Send the *User ID* to authorize them as Admin:", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
    return WAITING_ADMIN_ID

async def add_admin_receive(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        new_admin_id = int(update.message.text.strip())
        await admins_col.update_one({"user_id": new_admin_id}, {"$set": {"user_id": new_admin_id}}, upsert=True)
        await update.message.reply_text(f"✅ User `{new_admin_id}` is now an authorized Admin.", parse_mode="Markdown")
    except ValueError:
        await update.message.reply_text("❌ Invalid ID format. It must be an integer number.")
    return ConversationHandler.END

# --- 2. ADD QUIZ FLOW ---
async def add_quiz_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    topics = ["Maths", "Science", "Social", "GK", "English"]
    keyboard = [[InlineKeyboardButton(t, callback_data=f"addq_topic_{t}", style="primary")] for t in topics]
    keyboard.append([InlineKeyboardButton("❌ Cancel Process", callback_data="admin_cancel", style="danger")])
    await query.edit_message_text("📚 *Choose a Topic* to add questions to:", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
    return WAITING_QUIZ_TOPIC

async def add_quiz_topic(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    topic = query.data.split("_")[-1]
    context.user_data['current_topic'] = topic
    keyboard = [[InlineKeyboardButton("❌ Cancel Process", callback_data="admin_cancel", style="danger")]]
    await query.edit_message_text(f"📌 *Topic:* {topic}\n\nSend the *Question* now (Upload a Photo with caption or send a Text message):", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
    return WAITING_QUIZ_QUESTION

async def add_quiz_question(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    if msg.photo:
        context.user_data['q_type'] = 'photo'
        context.user_data['q_file_id'] = msg.photo[-1].file_id
        context.user_data['q_text'] = msg.caption or ""
    else:
        context.user_data['q_type'] = 'text'
        context.user_data['q_text'] = msg.text or ""
        
    await msg.reply_text("Got it! Now send the **exact correct answer** (Text format):", parse_mode="Markdown")
    return WAITING_QUIZ_ANSWER

async def add_quiz_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    answer = update.message.text.strip().lower()
    topic = context.user_data.get('current_topic', 'General')
    doc = {
        "topic": topic,
        "type": context.user_data['q_type'],
        "text": context.user_data.get('q_text', ''),
        "file_id": context.user_data.get('q_file_id', ''),
        "answer": answer
    }
    try:
        await quizzes_col.insert_one(doc)
    except Exception as e:
        await log_error(context, "Database Insertion Failed", e)
        await update.message.reply_text("❌ Database error while saving.")
        return ConversationHandler.END
        
    keyboard = [[InlineKeyboardButton("❌ Finish / Cancel", callback_data="admin_cancel", style="danger")]]
    await update.message.reply_text(f"✅ *Question Saved to {topic}!*\n\nSend the **next question** (Photo/Text) for this topic, or click Finish to stop.", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
    return WAITING_QUIZ_QUESTION

# --- 3. SET INTERVAL FLOW ---
async def set_interval_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    keyboard = [[InlineKeyboardButton("❌ Cancel Process", callback_data="admin_cancel", style="danger")]]
    await query.edit_message_text("⏱ Send the *time interval* in seconds between quizzes:", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
    return WAITING_INTERVAL

async def set_interval_receive(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        secs = int(update.message.text.strip())
        await settings_col.update_one({"_id": "config"}, {"$set": {"interval": secs}}, upsert=True)
        await update.message.reply_text(f"✅ Interval updated. Next quiz will post {secs} seconds after a correct answer.")
    except Exception as e:
        await update.message.reply_text("❌ Please send a valid number.")
    return ConversationHandler.END

# --- 4. DELETE QUIZ FLOW (Independent Callback & Message) ---
async def delete_quiz_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not await is_admin(query.from_user.id):
        return
    await query.answer()
    topics = ["Maths", "Science", "Social", "GK", "English"]
    keyboard = [[InlineKeyboardButton(t, callback_data=f"delq_topic_{t}", style="primary")] for t in topics]
    keyboard.append([InlineKeyboardButton("❌ Cancel Process", callback_data="admin_cancel", style="danger")])
    await query.edit_message_text("🗑 *Choose a topic* to delete questions from:", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

async def delete_quiz_topic(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    parts = query.data.split("_")
    
    if parts[1] == "topic":
        topic, page = parts[2], 0
    else:
        topic, page = parts[2], int(parts[3])
        
    cursor = quizzes_col.find({"topic": topic})
    questions = await cursor.to_list(length=None)
    total = len(questions)
    
    if total == 0:
        await query.edit_message_text("No questions found in this topic.")
        return
        
    batch_size = 10
    start = page * batch_size
    end = start + batch_size
    batch = questions[start:end]
    
    text = f"🗑 *Questions in {topic} (Batch {start+1} to {min(end, total)}):*\n\n"
    for i, q in enumerate(batch):
        q_text = q.get('text', '🖼 [Photo Question]')[:35].replace('\n', ' ')
        text += f"{start+i+1}. {q_text}...\n👉 Delete: /delete_question_{str(q['_id'])}\n\n"
        
    buttons = []
    nav_row = []
    if page > 0:
        nav_row.append(InlineKeyboardButton("⬅️ Prev", callback_data=f"delq_page_{topic}_{page-1}", style="primary"))
    if end < total:
        nav_row.append(InlineKeyboardButton("Next ➡️", callback_data=f"delq_page_{topic}_{page+1}", style="primary"))
        
    if nav_row:
        buttons.append(nav_row)
    buttons.append([InlineKeyboardButton("❌ Cancel Process", callback_data="admin_cancel", style="danger")])
    
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(buttons))

async def delete_question_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update.message.from_user.id):
        return
    q_id = update.message.text.split("_")[-1]
    try:
        res = await quizzes_col.delete_one({"_id": ObjectId(q_id)})
        if res.deleted_count > 0:
            await update.message.reply_text("✅ Question permanently deleted.")
        else:
            await update.message.reply_text("❌ Question not found in Database.")
    except Exception as e:
        await log_error(context, "Delete Exception", e)
        await update.message.reply_text("❌ Invalid ID or DB Error.")

# --- 5. RESET GROUP PROGRESS FLOW (New!) ---
async def reset_progress_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not await is_admin(query.from_user.id):
        return
    await query.answer()
    
    # We enforce that they must use this inside a group, so we know which chat ID to reset!
    if update.effective_chat.type == 'private':
        await query.edit_message_text("⚠️ *Important:* To reset a group's progress, please send the `/quiz` command and click this button **inside that specific group**.", parse_mode="Markdown")
        return

    topics = ["Maths", "Science", "Social", "GK", "English"]
    keyboard = [[InlineKeyboardButton(t, callback_data=f"resetq_topic_{t}", style="primary")] for t in topics]
    keyboard.append([InlineKeyboardButton("❌ Cancel Process", callback_data="admin_cancel", style="danger")])

    await query.edit_message_text("🔄 *Choose a topic* to reset progress for THIS group:", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

async def reset_progress_topic(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    topic = query.data.split("_")[-1]
    chat_id = update.effective_chat.id

    try:
        # Delete the progress memory for this chat and topic
        await progress_col.delete_one({"chat_id": chat_id, "topic": topic})
        await query.edit_message_text(f"✅ Progress for **{topic}** has been successfully reset!\n\nThis group can now play all questions again.", parse_mode="Markdown")
    except Exception as e:
        await log_error(context, "Reset Progress Exception", e)
        await query.edit_message_text("❌ Failed to reset progress due to a database error.")

# --- CANCEL FALLBACK ---
async def admin_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text("❌ Action cancelled.")
    else:
        await update.message.reply_text("❌ Action cancelled.")
    return ConversationHandler.END

def setup(application) -> None:
    # 1. Base command and open menu
    application.add_handler(CommandHandler("quiz", quiz_command))
    application.add_handler(CallbackQueryHandler(admin_menu, pattern="^admin_menu$"))
    
    # 2. Conversation Handler for Admin flows
    admin_conv = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(add_admin_start, pattern="^admin_add_admin$"),
            CallbackQueryHandler(add_quiz_start, pattern="^admin_add_quiz$"),
            CallbackQueryHandler(set_interval_start, pattern="^admin_set_interval$")
        ],
        states={
            WAITING_ADMIN_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_admin_receive)],
            WAITING_QUIZ_TOPIC: [CallbackQueryHandler(add_quiz_topic, pattern="^addq_topic_")],
            WAITING_QUIZ_QUESTION: [MessageHandler((filters.PHOTO | filters.TEXT) & ~filters.COMMAND, add_quiz_question)],
            WAITING_QUIZ_ANSWER: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_quiz_answer)],
            WAITING_INTERVAL: [MessageHandler(filters.TEXT & ~filters.COMMAND, set_interval_receive)],
        },
        fallbacks=[
            CallbackQueryHandler(admin_cancel, pattern="^admin_cancel$"),
            CommandHandler("cancel", admin_cancel)
        ],
        per_message=False 
    )
    application.add_handler(admin_conv)
    
    # 3. Independent Handlers for Deletion & Pagination
    application.add_handler(CallbackQueryHandler(delete_quiz_start, pattern="^admin_delete_quiz$"))
    application.add_handler(CallbackQueryHandler(delete_quiz_topic, pattern="^delq_(topic|page)_"))
    application.add_handler(MessageHandler(filters.Regex(r"^/delete_question_[a-fA-F0-9]{24}$"), delete_question_cmd))
    
    # 4. Independent Handlers for Group Progress Reset (New!)
    application.add_handler(CallbackQueryHandler(reset_progress_start, pattern="^admin_reset_progress$"))
    application.add_handler(CallbackQueryHandler(reset_progress_topic, pattern="^resetq_topic_"))
