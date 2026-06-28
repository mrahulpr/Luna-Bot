import os
import telebot

# Read the token from the environment variable
BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')

if not BOT_TOKEN:
    raise ValueError("Error: TELEGRAM_BOT_TOKEN environment variable not set!")

bot = telebot.TeleBot(BOT_TOKEN)

# Respond to /start and /help commands
@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    bot.reply_to(message, "Hello! Your bot is running perfectly on your AWS VPS.")

# Echo back any other text message
@bot.message_handler(func=lambda message: True)
def echo_all(message):
    bot.reply_to(message, f"You said: {message.text}")

# Keep the bot checking for updates continuously
print("Bot is starting up...")
bot.infinity_polling()
