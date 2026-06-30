# plugins/startquiz.py
import asyncio
import traceback
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, Message
from pyrogram.enums import ChatMemberStatus
from shared import quizzes_col, settings_col, admins_col, ACTIVE_QUIZZES, OWNER_ID, log_error

async def is_authorized(client, chat_id, user_id, original_sender_id):
    """Check if user is owner, original sender, or group admin."""
    if user_id == original_sender_id or user_id == OWNER_ID:
        return True
    
    is_admin_db = await admins_col.find_one({"user_id": user_id})
    if is_admin_db:
        return True
        
    try:
        member = await client.get_chat_member(chat_id, user_id)
        if member.status in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]:
            return True
    except:
        pass
    return False

@Client.on_callback_query(filters.regex(r"^start_quiz:(\d+)$"))
async def show_topics(client: Client, callback: CallbackQuery):
    try:
        original_sender = int(callback.matches[0].group(1))
        user_id = callback.from_user.id
        
        # Verify Permissions
        if not await is_authorized(client, callback.message.chat.id, user_id, original_sender):
            return await callback.answer("You don't have permission to use these buttons.", show_alert=True)
            
        topics = await quizzes_col.distinct("topic")
        if not topics:
            return await callback.answer("No topics available yet!", show_alert=True)
            
        kb = [[InlineKeyboardButton(t, callback_data=f"run_quiz:{t}")] for t in topics]
        kb.append([InlineKeyboardButton("❌ Cancel", callback_data="cancel_quiz")])
        
        await callback.edit_message_text("Select a Topic to start the quiz:", reply_markup=InlineKeyboardMarkup(kb))
    except Exception as e:
        await log_error(client, traceback.format_exc())

@Client.on_callback_query(filters.regex("^cancel_quiz$"))
async def cancel_quiz(client: Client, callback: CallbackQuery):
    await callback.edit_message_text("Quiz cancelled.")

@Client.on_callback_query(filters.regex(r"^run_quiz:(.*)"))
async def start_quiz_loop(client: Client, callback: CallbackQuery):
    try:
        topic = callback.matches[0].group(1)
        chat_id = callback.message.chat.id
        
        # Fetch all questions for topic
        cursor = quizzes_col.find({"topic": topic})
        questions = await cursor.to_list(length=None)
        
        if not questions:
            return await callback.answer("No questions in this topic.", show_alert=True)
            
        # Initialize quiz state for this chat
        ACTIVE_QUIZZES[chat_id] = {
            "topic": topic,
            "questions": questions,
            "current_index": 0,
            "waiting_for_next": False
        }
        
        await callback.edit_message_text(f"🚀 Starting Quiz: **{topic}**!")
        await post_question(client, chat_id)
        
    except Exception as e:
        await log_error(client, traceback.format_exc())

async def post_question(client: Client, chat_id: int):
    try:
        state = ACTIVE_QUIZZES.get(chat_id)
        if not state: return
        
        index = state["current_index"]
        if index >= len(state["questions"]):
            await client.send_message(chat_id, f"🎉 **Quiz Finished!** All questions for {state['topic']} are done.")
            del ACTIVE_QUIZZES[chat_id]
            return
            
        question = state["questions"][index]
        caption = "👇 **Send the Correct answer below** 👇"
        
        if question["type"] == "photo":
            await client.send_photo(chat_id, photo=question["content"], caption=caption)
        else:
            await client.send_message(chat_id, f"❓ **Question:**\n{question['content']}\n\n{caption}")
            
    except Exception as e:
        await log_error(client, traceback.format_exc())

# Watch messages for correct answers
@Client.on_message(filters.group & filters.text, group=1)
async def check_answer(client: Client, message: Message):
    chat_id = message.chat.id
    if chat_id not in ACTIVE_QUIZZES:
        return
        
    state = ACTIVE_QUIZZES[chat_id]
    current_q = state["questions"][state["current_index"]]
    
    # Check if answer matches (case-insensitive)
    if message.text.strip().lower() == current_q["answer"].strip().lower():
        try:
            # React with heart
            await message.react("❤️")
            
            # If the timer for the next question hasn't started yet, start it
            if not state["waiting_for_next"]:
                state["waiting_for_next"] = True
                asyncio.create_task(schedule_next(client, chat_id))
        except Exception as e:
            await log_error(client, traceback.format_exc())

async def schedule_next(client: Client, chat_id: int):
    """Waits for the specified interval, then posts the next question."""
    try:
        # Fetch interval from settings, default to 30s
        setting = await settings_col.find_one({"key": "quiz_interval"})
        interval = setting["value"] if setting else 30
        
        await asyncio.sleep(interval)
        
        # Advance index and post
        state = ACTIVE_QUIZZES.get(chat_id)
        if state:
            state["current_index"] += 1
            state["waiting_for_next"] = False
            await post_question(client, chat_id)
    except Exception as e:
        await log_error(client, traceback.format_exc())
