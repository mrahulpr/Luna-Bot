# plugins/quiz.py
import traceback
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, Message
from bson.objectid import ObjectId
from shared import db, admins_col, quizzes_col, settings_col, ADMIN_STATES, OWNER_ID, log_error

@Client.on_message(filters.command("quiz"))
async def quiz_command(client: Client, message: Message):
    try:
        # Pass the user ID in the callback data so we know who initiated it
        user_id = message.from_user.id
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🟢 Start Quiz", callback_data=f"start_quiz:{user_id}")],
            [InlineKeyboardButton("🔵 Admin Only", callback_data="admin_menu")]
        ])
        await message.reply("Welcome to the Quiz! Please choose an option below:", reply_markup=keyboard)
    except Exception as e:
        await log_error(client, traceback.format_exc())

@Client.on_callback_query(filters.regex("^admin_menu$"))
async def admin_menu(client: Client, callback: CallbackQuery):
    try:
        user_id = callback.from_user.id
        
        # Check Authorization
        is_admin = await admins_col.find_one({"user_id": user_id})
        if user_id != OWNER_ID and not is_admin:
            return await callback.answer("Only admins can use this.", show_alert=True)
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("Add Admin", callback_data="add_admin"),
             InlineKeyboardButton("Set Interval", callback_data="set_interval")],
            [InlineKeyboardButton("Add Quiz Topic/Question", callback_data="add_quiz")],
            [InlineKeyboardButton("Delete Quiz", callback_data="delete_quiz_topics")],
            [InlineKeyboardButton("❌ Cancel", callback_data="cancel_admin")]
        ])
        await callback.edit_message_text("🛠 **Admin Panel**\nChoose an action:", reply_markup=keyboard)
    except Exception as e:
        await log_error(client, traceback.format_exc())

@Client.on_callback_query(filters.regex("^(add_admin|set_interval|add_quiz)$"))
async def admin_actions(client: Client, callback: CallbackQuery):
    action = callback.data
    user_id = callback.from_user.id
    
    # Restrict Add Admin to OWNER only
    if action == "add_admin" and user_id != OWNER_ID:
        return await callback.answer("Only the Owner can add admins.", show_alert=True)
    
    cancel_kb = InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancel", callback_data="cancel_admin")]])
    
    if action == "add_admin":
        ADMIN_STATES[user_id] = {"step": "wait_admin_id"}
        await callback.edit_message_text("Send the User ID of the new admin:", reply_markup=cancel_kb)
    
    elif action == "set_interval":
        ADMIN_STATES[user_id] = {"step": "wait_interval"}
        await callback.edit_message_text("Send the time interval (in seconds) between quizzes:", reply_markup=cancel_kb)
        
    elif action == "add_quiz":
        ADMIN_STATES[user_id] = {"step": "wait_topic"}
        await callback.edit_message_text("Send the Topic Name for this quiz (e.g., Maths, Science):", reply_markup=cancel_kb)

@Client.on_callback_query(filters.regex("^cancel_admin$"))
async def cancel_admin(client: Client, callback: CallbackQuery):
    user_id = callback.from_user.id
    if user_id in ADMIN_STATES:
        del ADMIN_STATES[user_id]
    await callback.edit_message_text("Action cancelled.")

# --- FSM (State Machine) for Admin Inputs ---
@Client.on_message(filters.private & filters.text & ~filters.command(["quiz", "delete_question"]))
async def process_admin_inputs(client: Client, message: Message):
    user_id = message.from_user.id
    if user_id not in ADMIN_STATES:
        return
    
    state = ADMIN_STATES[user_id]
    step = state.get("step")
    
    try:
        if step == "wait_admin_id":
            new_admin_id = int(message.text)
            await admins_col.insert_one({"user_id": new_admin_id})
            await message.reply(f"✅ User `{new_admin_id}` added as admin.")
            del ADMIN_STATES[user_id]
            
        elif step == "wait_interval":
            interval = int(message.text)
            await settings_col.update_one({"key": "quiz_interval"}, {"$set": {"value": interval}}, upsert=True)
            await message.reply(f"✅ Quiz interval set to {interval} seconds.")
            del ADMIN_STATES[user_id]
            
        elif step == "wait_topic":
            state["topic"] = message.text
            state["step"] = "wait_question"
            await message.reply(f"Topic set to **{message.text}**.\n\nNow send the Question (Text or Photo):")
            
        elif step == "wait_answer":
            # Save the quiz to the database
            topic = state["topic"]
            q_type = state["q_type"]
            q_content = state["q_content"]
            answer = message.text.strip()
            
            await quizzes_col.insert_one({
                "topic": topic,
                "type": q_type,
                "content": q_content,
                "answer": answer
            })
            await message.reply("✅ Quiz question added successfully!\n\nYou can send another question for this topic or type /cancel.")
            state["step"] = "wait_question" # Loop back to add more questions to the same topic
            
    except ValueError:
        await message.reply("Invalid input. Please provide a valid number.")
    except Exception as e:
        await log_error(client, traceback.format_exc())

@Client.on_message(filters.private & (filters.text | filters.photo) & ~filters.command("quiz"))
async def process_question_input(client: Client, message: Message):
    user_id = message.from_user.id
    if user_id not in ADMIN_STATES:
        return
    
    state = ADMIN_STATES[user_id]
    if state.get("step") == "wait_question":
        try:
            if message.photo:
                state["q_type"] = "photo"
                state["q_content"] = message.photo.file_id
            else:
                state["q_type"] = "text"
                state["q_content"] = message.text
                
            state["step"] = "wait_answer"
            await message.reply("Great! Now send the **exact correct answer** for this question:")
        except Exception as e:
            await log_error(client, traceback.format_exc())

# --- Delete Logic ---
@Client.on_callback_query(filters.regex("^delete_quiz_topics$"))
async def delete_quiz_topics(client: Client, callback: CallbackQuery):
    # Fetch distinct topics
    topics = await quizzes_col.distinct("topic")
    if not topics:
        return await callback.answer("No quizzes found.", show_alert=True)
    
    kb = [[InlineKeyboardButton(t, callback_data=f"del_topic:{t}")] for t in topics]
    kb.append([InlineKeyboardButton("❌ Cancel", callback_data="cancel_admin")])
    await callback.edit_message_text("Select a topic to delete questions from:", reply_markup=InlineKeyboardMarkup(kb))

@Client.on_callback_query(filters.regex("^del_topic:(.*)"))
async def show_delete_questions(client: Client, callback: CallbackQuery):
    topic = callback.matches[0].group(1)
    # Fetching first 20 for simplicity (You can expand this with pagination pages later)
    cursor = quizzes_col.find({"topic": topic}).limit(20)
    questions = await cursor.to_list(length=20)
    
    text = f"**Questions for {topic}** (First 20):\n\n"
    for q in questions:
        q_preview = q["content"] if q["type"] == "text" else "[Photo Question]"
        text += f"Q: {q_preview[:30]}...\nCommand: `/delete_question {str(q['_id'])}`\n\n"
        
    await callback.message.reply(text)
    await callback.answer()

@Client.on_message(filters.command("delete_question"))
async def delete_specific_question(client: Client, message: Message):
    try:
        user_id = message.from_user.id
        is_admin = await admins_col.find_one({"user_id": user_id})
        if user_id != OWNER_ID and not is_admin:
            return await message.reply("Unauthorized.")
            
        q_id = message.command[1]
        result = await quizzes_col.delete_one({"_id": ObjectId(q_id)})
        if result.deleted_count > 0:
            await message.reply("✅ Question deleted.")
        else:
            await message.reply("❌ Question not found.")
    except Exception as e:
        await log_error(client, traceback.format_exc())
