import asyncio
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CommandHandler, CallbackQueryHandler, ContextTypes

# Retrieve the owner ID from the environment
OWNER_ID = int(os.getenv("OWNER_ID", "0"))

async def hack(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Simulates a fake hacking sequence on the user being replied to."""
    if not update.message.reply_to_message:
        return await update.message.reply_text(
            "⚠️ You must reply to someone's message to use this command\\.", 
            parse_mode="MarkdownV2"
        )

    target = update.message.reply_to_message.from_user
    bot = context.bot
    me = await bot.get_me()

    if target.id == me.id:
        return await update.message.reply_text(
            "🤖 I don't hack myself\\.\\.\\. nice try 😂", 
            parse_mode="MarkdownV2"
        )
    
    if target.id == OWNER_ID:
        return await update.message.reply_text("🫣 I will hack my owner... please don't tell him!")

    msg = await update.message.reply_text(
        "```\n> Initializing hack sequence...\n```", 
        parse_mode="MarkdownV2"
    )
    
    last_text = msg.text

    animation = [
        "Scanning target...",
        "Target locked.",
        "Connecting to secured server...",
        "Bypassing firewall 1...",
        "Bypassing firewall 2...",
        "Bypassing firewall 3...",
        "Installing payload... 10% 🟩⬜⬜⬜⬜⬜⬜⬜⬜⬜",
        "Installing payload... 25% 🟩🟩⬜⬜⬜⬜⬜⬜⬜⬜",
        "Installing payload... 67% 🟩🟩🟩🟩🟩🟩⬜⬜⬜⬜",
        "Installing payload... 91% 🟩🟩🟩🟩🟩🟩🟩🟩🟩⬜",
        "Installing payload... 100% 🟩🟩🟩🟩🟩🟩🟩🟩🟩🟩",
        "Uploading payload...",
        "Finalizing connection...",
        "Generating exploit link...",
        "Target successfully hacked!",
    ]

    buffer = []
    for line in animation:
        buffer.append(line)
        if len(buffer) > 4:
            buffer.pop(0)

        text_to_send = "```\n" + "\n".join(f"> {l}" for l in buffer) + "\n```"
        
        if text_to_send != last_text:
            try:
                await msg.edit_text(text_to_send, parse_mode='MarkdownV2')
                last_text = text_to_send
            except Exception:
                pass
        
        await asyncio.sleep(1.2)

    await msg.edit_text(
        "> Target compromised\\. Click below to access the panel\\.",
        reply_markup=InlineKeyboardMarkup(
            # Removed invalid Discord 'style' argument
            [[InlineKeyboardButton("🕵️ View Hacked File", url="https://t.me/c/1478246163/16150/16152")]]
        ),
        parse_mode="MarkdownV2"
    )

async def hack_help_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Callback function for the help menu button."""
    query = update.callback_query
    await query.answer()
    
    # Removed invalid Discord 'style' argument
    keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="help")]]
    text = (
        "💻 *Hack Plugin*\n\n"
        "Simulates a fake hacking sequence as a prank\\.\n\n"
        "*Usage:*\n"
        "`/hack` – Reply to a user's message to initiate a fake hack\\."
    )
    await query.edit_message_text(
        text, 
        parse_mode="MarkdownV2", 
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

def setup(app) -> None:
    """Adds the command and callback handlers to the application."""
    app.add_handler(CommandHandler("hack", hack))
    app.add_handler(CallbackQueryHandler(hack_help_callback, pattern="^plugin::hack$"))
