import os
import sys
import subprocess
from telegram import Update
from telegram.ext import CommandHandler, ContextTypes
from main import OWNER_ID

async def update_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Fetches updates from git and restarts the bot process."""
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text("⚠️ Unauthorized. This command is restricted to the bot owner.")
        return

    status_message = await update.message.reply_text("🔄 Pulling latest commits from GitHub...")
    
    try:
        # Run git pull command
        pull_output = subprocess.run(["git", "pull"], capture_output=True, text=True, check=True)
        await status_message.edit_text(
            f"✅ **Git Pull Execution:**\n```{pull_output.stdout}```\nRebooting bot instance...", 
            parse_mode="Markdown"
        )
        
        # Clear terminal wrappers and restart the python file process
        os.execl(sys.executable, sys.executable, *sys.argv)
        
    except Exception as error:
        await status_message.edit_text("❌ Update routine failed. Traceback forwarded to logs.")
        # Re-raise the exception so it propagates directly into the universal error handler
        raise error

def setup(application) -> None:
    """Registers handlers to the main application workflow."""
    application.add_handler(CommandHandler("update", update_command))
