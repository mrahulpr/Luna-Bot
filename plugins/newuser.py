import os
from telegram import Update
from telegram.ext import TypeHandler, ContextTypes
from telegram.helpers import escape_markdown

async def track_new_users(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if not user:
        return

    # Retrieve or initialize the known users set in bot_data
    known_users = context.bot_data.setdefault("known_users", set())
    
    if user.id in known_users:
        return

    # Mark user as known
    known_users.add(user.id)

    log_chat_id = os.getenv("LOG_CHAT_ID")
    if not log_chat_id:
        return
    
    # Format user details using MarkdownV2
    details = [
        r"\#NewUser Detected 🚨",
        f"*ID:* `{user.id}`",
        f"*First Name:* {escape_markdown(user.first_name, version=2)}",
    ]
    
    if user.last_name:
        details.append(f"*Last Name:* {escape_markdown(user.last_name, version=2)}")
    if user.username:
        details.append(f"*Username:* @{escape_markdown(user.username, version=2)}")
    if user.language_code:
        details.append(f"*Language:* {escape_markdown(user.language_code, version=2)}")
    if user.is_premium:
        details.append(f"*Premium:* Yes 🌟")

    text = "\n".join(details)

    try:
        # Attempt to fetch the user's profile photo
        photos = await context.bot.get_user_profile_photos(user.id, limit=1)
        
        if photos.total_count > 0:
            # Send the largest version of the first profile photo
            photo_file_id = photos.photos[0][-1].file_id
            await context.bot.send_photo(
                chat_id=log_chat_id,
                photo=photo_file_id,
                caption=text,
                parse_mode="MarkdownV2"
            )
        else:
            # Fallback to text message if no photo exists
            await context.bot.send_message(
                chat_id=log_chat_id,
                text=text,
                parse_mode="MarkdownV2"
            )
    except Exception:
        # Prevent logging errors from breaking the update flow
        pass

def setup(application) -> None:
    # Group -1 ensures this runs before standard handlers (which default to group 0)
    application.add_handler(TypeHandler(Update, track_new_users), group=-1)
