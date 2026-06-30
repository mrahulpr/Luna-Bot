# plugins/startquiz.py
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackQueryHandler, MessageHandler, filters, ContextTypes

# Make sure this import perfectly matches your folder structure!
# If shared.py is inside plugins folder, this must be: from plugins.shared import ...
from shared import ACTIVE_QUIZZES, quizzes_col, settings_col, log_error


async def start_quiz_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Shows the user which topics are available right now to start."""
    print("🎯 DEBUG: Start Quiz button was clicked!") # <-- ADD THIS LINE
    query = update.callback_query
    await query.answer()
    
    topics = await quizzes_col.distinct("topic")
    if not topics:
        await query.edit_message_text("😔 No quizzes available in the database yet.")
        return
        
    keyboard = []
    for t in topics:
        keyboard.append([InlineKeyboardButton(f"📘 {t}", callback_data=f"play_topic_{t}", style="primary")])
    keyboard.append([InlineKeyboardButton("❌ Cancel Process", callback_data="cancel_quiz_play", style="danger")])
    
    await query.edit_message_text("🎯 *Select a Quiz Topic to start:*", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

async def play_topic_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Initializes the chat's active memory dictionary and posts the first question."""
    query = update.callback_query
    chat_id = update.effective_chat.id
    
    # Verify group admin / owner before starting a global chat quiz game
    if update.effective_chat.type in ['group', 'supergroup']:
        user_status = await context.bot.get_chat_member(chat_id, query.from_user.id)
        if user_status.status not in ['administrator', 'creator']:
            from shared import OWNER_ID
            if query.from_user.id != OWNER_ID:
                await query.answer("❌ Only Group Admins can initiate the quiz here.", show_alert=True)
                return
                
    await query.answer()
    topic = query.data.split("_")[-1]
    
    cursor = quizzes_col.find({"topic": topic})
    questions = await cursor.to_list(length=None)
    
    if not questions:
        await query.edit_message_text("😔 No questions found for this topic.")
        return
        
    ACTIVE_QUIZZES[chat_id] = {
        "topic": topic,
        "questions": questions,
        "current_index": 0,
        "solved_by": set(),
        "timer_task": None,
        "is_active": True
    }
    
    await query.edit_message_text(f"🚀 *Starting {topic} Quiz!*\n\nGet ready...", parse_mode="Markdown")
    await asyncio.sleep(2)
    await post_next_question(chat_id, context)

async def post_next_question(chat_id: int, context: ContextTypes.DEFAULT_TYPE):
    """Pulls the next question and posts it to the chat."""
    quiz = ACTIVE_QUIZZES.get(chat_id)
    if not quiz or not quiz["is_active"]:
        return
        
    idx = quiz["current_index"]
    if idx >= len(quiz["questions"]):
        await context.bot.send_message(chat_id, "🎉 *The quiz has ended!* Thanks for playing.", parse_mode="Markdown")
        quiz["is_active"] = False
        del ACTIVE_QUIZZES[chat_id]
        return
        
    q = quiz["questions"][idx]
    quiz["solved_by"].clear()
    quiz["timer_task"] = None
    
    text_content = q.get("text", "")
    caption = f"{text_content}\n\n👇 *Send the Correct answer below*"
    
    keyboard = [[InlineKeyboardButton("🛑 Stop Quiz", callback_data="cancel_quiz_play", style="danger")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    try:
        if q["type"] == "photo":
            await context.bot.send_photo(chat_id, q["file_id"], caption=caption, parse_mode="Markdown", reply_markup=reply_markup)
        else:
            await context.bot.send_message(chat_id, caption, parse_mode="Markdown", reply_markup=reply_markup)
    except Exception as e:
        await log_error(context, "Error posting quiz question", e)
        # Advance and retry if failed
        quiz["current_index"] += 1
        await post_next_question(chat_id, context)

async def handle_quiz_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Listens globally for users posting the correct answer."""
    chat_id = update.effective_chat.id
    quiz = ACTIVE_QUIZZES.get(chat_id)
    
    # Early returns if no quiz active
    if not quiz or not quiz["is_active"] or not update.message or not update.message.text:
        return
        
    idx = quiz["current_index"]
    if idx >= len(quiz["questions"]):
        return
        
    current_q = quiz["questions"][idx]
    correct_ans = current_q.get("answer", "").strip().lower()
    user_ans = update.message.text.strip().lower()
    
    if user_ans == correct_ans:
        user_id = update.message.from_user.id
        
        # Throw heart reaction - gracefully fail if chat restricted reactions
        try:
            await update.message.set_reaction(reaction="❤️")
        except Exception:
            pass 
            
        if user_id not in quiz["solved_by"]:
            quiz["solved_by"].add(user_id)
            
        # Start the countdown timer the moment the FIRST correct answer drops.
        if quiz["timer_task"] is None:
            config = await settings_col.find_one({"_id": "config"})
            interval = config.get("interval", 30) if config else 30
            quiz["timer_task"] = asyncio.create_task(next_question_countdown(chat_id, context, interval))

async def next_question_countdown(chat_id: int, context: ContextTypes.DEFAULT_TYPE, interval: int):
    """Background waiting task to push next question after interval passes."""
    await asyncio.sleep(interval)
    quiz = ACTIVE_QUIZZES.get(chat_id)
    if quiz and quiz["is_active"]:
        quiz["current_index"] += 1
        await post_next_question(chat_id, context)

async def cancel_quiz_play(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancels an ongoing quiz mid-game."""
    query = update.callback_query
    chat_id = update.effective_chat.id
    
    if update.effective_chat.type in ['group', 'supergroup']:
        user_status = await context.bot.get_chat_member(chat_id, query.from_user.id)
        if user_status.status not in ['administrator', 'creator']:
            from shared import OWNER_ID
            if query.from_user.id != OWNER_ID:
                await query.answer("❌ Only Admins can cancel the quiz.", show_alert=True)
                return
                
    await query.answer("Quiz cancelled.")
    
    quiz = ACTIVE_QUIZZES.get(chat_id)
    if quiz:
        quiz["is_active"] = False
        if quiz["timer_task"]:
            quiz["timer_task"].cancel()
        del ACTIVE_QUIZZES[chat_id]
        
    try:
        if query.message.photo:
            await query.edit_message_reply_markup(reply_markup=None)
        else:
            await query.edit_message_text(query.message.text + "\n\n❌ [Quiz Stopped]", reply_markup=None)
    except Exception:
        pass
        
    await context.bot.send_message(chat_id, "❌ *Quiz session was stopped mid-way.*", parse_mode="Markdown")

def setup(application) -> None:
    print("🚀 DEBUG: Attempting to load startquiz.py...")
    
    application.add_handler(CallbackQueryHandler(start_quiz_menu, pattern="^start_quiz_menu$"))
    application.add_handler(CallbackQueryHandler(play_topic_start, pattern="^play_topic_"))
    application.add_handler(CallbackQueryHandler(cancel_quiz_play, pattern="^cancel_quiz_play$"))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_quiz_answer), group=1)
    
    print("✅ DEBUG: startquiz.py loaded successfully!")
