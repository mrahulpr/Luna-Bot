import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import CommandHandler, CallbackQueryHandler, ContextTypes

PHOTO_PATH = "assets/welcome.jpg"
TEXT_FILE = "buttonmessage.txt"

def load_texts() -> dict:
    """Reads the buttonmessage.txt file and parses sections."""
    texts = {"welcome": "Welcome!", "about": "About info missing.", "help": "Help info missing."}
    
    if not os.path.exists(TEXT_FILE):
        return texts

    with open(TEXT_FILE, "r", encoding="utf-8") as f:
        content = f.read()

    sections = content.split("===")
    current_section = None

    for part in sections:
        part = part.strip()
        if part in ["WELCOME", "ABOUT", "HELP"]:
            current_section = part.lower()
        elif current_section and part:
            texts[current_section] = part
            current_section = None

    return texts

def get_main_keyboard() -> InlineKeyboardMarkup:
    """Returns the main inline keyboard."""
    keyboard = [
        [
            InlineKeyboardButton("😉 About Me", callback_data="start_about"),
            InlineKeyboardButton("Help 🍀", callback_data="start_help")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_back_keyboard() -> InlineKeyboardMarkup:
    """Returns a keyboard with a single Back button."""
    return InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="start_back")]])

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles the /start command."""
    user = update.effective_user
    texts = load_texts()
    
    # Inject user mention into the welcome text
    mention = f"[{user.first_name}](tg://user?id={user.id})"
    welcome_text = texts["welcome"].replace("{name}", mention)
    
    keyboard = get_main_keyboard()

    if os.path.exists(PHOTO_PATH):
        with open(PHOTO_PATH, 'rb') as photo:
            await update.message.reply_photo(
                photo=photo,
                caption=welcome_text,
                parse_mode=ParseMode.MARKDOWN_V2,
                reply_markup=keyboard,
                reply_to_message_id=update.message.message_id
            )
    else:
        await update.message.reply_text(
            text=welcome_text,
            parse_mode=ParseMode.MARKDOWN_V2,
            reply_markup=keyboard,
            reply_to_message_id=update.message.message_id
        )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles the /help command directly."""
    texts = load_texts()
    await update.message.reply_text(
        text=texts["help"],
        parse_mode=ParseMode.MARKDOWN_V2,
        reply_markup=get_back_keyboard(),
        reply_to_message_id=update.message.message_id
    )

async def start_callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles button clicks for the start menu."""
    query = update.callback_query
    await query.answer()

    texts = load_texts()
    
    if query.data == "start_about":
        text_content = texts["about"]
        markup = get_back_keyboard()
    elif query.data == "start_help":
        text_content = texts["help"]
        markup = get_back_keyboard()
    elif query.data == "start_back":
        user = update.effective_user
        mention = f"[{user.first_name}](tg://user?id={user.id})"
        text_content = texts["welcome"].replace("{name}", mention)
        markup = get_main_keyboard()
    else:
        return

    if query.message.photo:
        await query.edit_message_caption(
            caption=text_content,
            parse_mode=ParseMode.MARKDOWN_V2,
            reply_markup=markup
        )
    else:
        await query.edit_message_text(
            text=text_content,
            parse_mode=ParseMode.MARKDOWN_V2,
            reply_markup=markup
        )

def setup(application) -> None:
    """Registers handlers."""
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CallbackQueryHandler(start_callbacks, pattern="^start_"))
