import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import CommandHandler, CallbackQueryHandler, ContextTypes

# --- Constants & Text (Transcribed from Screenshots) ---

# Make sure to have a folder named 'assets' in your root directory containing 'welcome.jpg'
PHOTO_PATH = "assets/welcome.jpg"

def get_welcome_text(first_name: str, user_id: int) -> str:
    """Generates the welcome text with proper MarkdownV2 escaping."""
    # Escaping periods, exclamation marks, etc. is required in MarkdownV2.
    return (
        f"Hi 👋 [{first_name}](tg://user?id={user_id})\n"
        "Welcome 😁, glad to meet you here, iam a simple group "
        "management bot to help to manage telegram groups and "
        "Currently iam in initial stages of its development use below buttons "
        "to navigate along with my features ❤️\\."
    )

ABOUT_TEXT = (
    "*About Me 🤩*\n"
    "\\> 🤖 *Bot Name* : [*\\- Luna Bot \\-*](https://t.me/Taskieebot)\n"
    "\\> 👨‍💻 *Daddy* : [*\\- Rahul P R \\-*](https://t.me/rahulp_r)\n"
    "\\> 💻 *Total Users* : *1* || \\[ Only You 🥺 \\] ||\n"
    "\\> 🔢 *Version* : *v1\\.0\\.7 \\[ Beta \\]*\n"
    "\\> ☂️ *Server* : *Paid Alla 😐*\n"
    "\\> 💿 *Storage* : *5 GB 🥶*\n\n"
    "[*©️ Webotz*](https://t.me/webotz)"
)

HELP_TEXT = (
    "*📖 Help Menu*\n\n"
    "*/start* \\- Launch the bot\\.\n"
    "*/help* \\- Show help menu\\.\n"
    "*/ping* \\- To get information about Speed\\.\n"
    "*/hack* \\- To make an hack someone\\.\n"
    "*/id* \\- To Get id of a Chat\\.\n"
    "*/reacts* \\- Auto Reaction to Messages\\."
)

# --- Keyboards ---

def get_main_keyboard() -> InlineKeyboardMarkup:
    """Returns the main inline keyboard with About and Help buttons."""
    keyboard = [
        [
            InlineKeyboardButton("😉 About Me", callback_data="start_about"),
            InlineKeyboardButton("Help 🍀", callback_data="start_help")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_back_keyboard() -> InlineKeyboardMarkup:
    """Returns a keyboard with a single Back button."""
    keyboard = [
        [InlineKeyboardButton("🔙 Back", callback_data="start_back")]
    ]
    return InlineKeyboardMarkup(keyboard)

# --- Handlers ---

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles the /start command."""
    user = update.effective_user
    welcome_text = get_welcome_text(user.first_name, user.id)
    keyboard = get_main_keyboard()

    if os.path.exists(PHOTO_PATH):
        with open(PHOTO_PATH, 'rb') as photo:
            await context.bot.send_photo(
                chat_id=update.effective_chat.id,
                photo=photo,
                caption=welcome_text,
                parse_mode=ParseMode.MARKDOWN_V2,
                reply_markup=keyboard
            )
    else:
        # Fallback if photo is missing so the bot doesn't crash
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=welcome_text,
            parse_mode=ParseMode.MARKDOWN_V2,
            reply_markup=keyboard
        )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles the /help command directly."""
    await update.message.reply_text(
        text=HELP_TEXT,
        parse_mode=ParseMode.MARKDOWN_V2,
        reply_markup=get_back_keyboard()
    )

async def start_callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles button clicks for the start menu."""
    query = update.callback_query
    await query.answer()  # Stop the loading spinner on the button

    user = update.effective_user
    
    if query.data == "start_about":
        # Edit caption if it's a photo, or text if it's a normal message fallback
        if query.message.photo:
            await query.edit_message_caption(
                caption=ABOUT_TEXT,
                parse_mode=ParseMode.MARKDOWN_V2,
                reply_markup=get_back_keyboard()
            )
        else:
            await query.edit_message_text(
                text=ABOUT_TEXT,
                parse_mode=ParseMode.MARKDOWN_V2,
                reply_markup=get_back_keyboard()
            )

    elif query.data == "start_help":
        if query.message.photo:
            await query.edit_message_caption(
                caption=HELP_TEXT,
                parse_mode=ParseMode.MARKDOWN_V2,
                reply_markup=get_back_keyboard()
            )
        else:
            await query.edit_message_text(
                text=HELP_TEXT,
                parse_mode=ParseMode.MARKDOWN_V2,
                reply_markup=get_back_keyboard()
            )

    elif query.data == "start_back":
        welcome_text = get_welcome_text(user.first_name, user.id)
        if query.message.photo:
            await query.edit_message_caption(
                caption=welcome_text,
                parse_mode=ParseMode.MARKDOWN_V2,
                reply_markup=get_main_keyboard()
            )
        else:
            await query.edit_message_text(
                text=welcome_text,
                parse_mode=ParseMode.MARKDOWN_V2,
                reply_markup=get_main_keyboard()
            )

# --- Plugin Setup ---

def setup(application) -> None:
    """Registers the handlers with the application."""
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CallbackQueryHandler(start_callbacks, pattern="^start_"))
