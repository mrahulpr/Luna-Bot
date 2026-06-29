import os
import sys
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CommandHandler, CallbackQueryHandler, ContextTypes

OWNER_ID = int(os.getenv("OWNER_ID"))
LOG_CHAT_ID = int(os.getenv("LOG_CHAT_ID"))

async def run_sh(cmd: str) -> tuple:
    """Executes shell commands asynchronously to allow parallel bot commanding."""
    proc = await asyncio.create_subprocess_shell(
        cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )
    stdout, stderr = await proc.communicate()
    return stdout.decode().strip(), stderr.decode().strip(), proc.returncode

async def update_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Checks for new git commits without applying them immediately."""
    if update.effective_user.id != OWNER_ID:
        return
        
    await run_sh("git fetch")
    out, err, rc = await run_sh("git log HEAD..@{u} --oneline")
    
    if not out:
        await update.message.reply_text("✅ No changes. System is up to date.")
        return
        
    # Inject new colored buttons natively supported by modern Telegram clients
    keyboard = [
        [
            InlineKeyboardButton("Update", callback_data="up_yes", style="primary"),
            InlineKeyboardButton("Cancel", callback_data="up_no", style="danger")
        ]
    ]
    markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f"🆕 **New Updates Found!**\n\n`{out}`\n\nDeploy these changes?",
        reply_markup=markup,
        parse_mode="Markdown"
    )

async def update_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Processes the inline button click event."""
    query = update.callback_query
    if query.from_user.id != OWNER_ID:
        await query.answer("Unauthorized.", show_alert=True)
        return
        
    await query.answer()
    
    if query.data == "up_no":
        await query.edit_message_text("❌ Update cancelled.")
        return
        
    status = await query.edit_message_text("🔄 Deploying updates...")
    
    # Store old hash state for fallback mechanism
    old_hash, _, _ = await run_sh("git rev-parse HEAD")
    
    _, pull_err, pull_rc = await run_sh("git pull")
    if pull_rc != 0:
        await status.edit_text(f"❌ Git pull failed:\n`{pull_err}`")
        return
        
    await status.edit_text("📦 Installing requirements...")
    
    _, pip_err, pip_rc = await run_sh(f"{sys.executable} -m pip install -r requirements.txt --break-system-packages")
    
    # Rollback trigger
    if pip_rc != 0:
        error_msg = f"❌ Dependency failure. Reverting to `{old_hash[:7]}`...\n\n`{pip_err}`"
        await status.edit_text(error_msg, parse_mode="Markdown")
        await context.bot.send_message(LOG_CHAT_ID, error_msg, parse_mode="Markdown")
        await run_sh(f"git reset --hard {old_hash}")
        return
        
    await status.edit_text("✅ Update successful. Rebooting...")
    
    # Restarts python script
    os.execl(sys.executable, sys.executable, *sys.argv)

def setup(application) -> None:
    """Registers commands and callback interactions."""
    application.add_handler(CommandHandler("update", update_cmd))
    application.add_handler(CallbackQueryHandler(update_callback, pattern="^up_"))
