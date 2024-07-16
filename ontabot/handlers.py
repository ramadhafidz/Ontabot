import logging
import json
import os
from datetime import datetime, timedelta, timezone
import pytz
from telegram import Update
from telegram.ext import ContextTypes


client = None

def GroqClient(groq_client):
    global client
    client = groq_client


with open('config/timezones.json', 'r') as f:
    timezone_mappings = json.load(f)
 
    
chat_histories = {}
user_timezones = {}


def get_greeting_prompt(user_time):
    current_hour = user_time.hour
    current_minute = user_time.minute
    current_time = current_hour * 60 + current_minute

    if 151 <= current_time <= 630:
        return "Give a friendly morning greeting"
    elif 631 <= current_time <= 900:
        return "Give a friendly afternoon greeting"
    elif 901 <= current_time <= 1110:
        return "Give a friendly evening greeting"
    elif 1111 <= current_time < 1350:
        return "Give a friendly night greeting"
    else:
        return "Give a friendly midnight greeting"

    
def trim_chat_history(chat_id, max_length=20):
    if len(chat_histories[chat_id]) > max_length:
        chat_histories[chat_id] = chat_histories[chat_id][-max_length:]

  
# Fungsi untuk mengatur zona waktu pengguna     
async def set_timezone(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.message.chat_id
    try:
        tz_arg = context.args[0].lower() # Mengubah jawaban user menjadi lowecase
        if tz_arg.startswith(('+', '-')):
            offset_hours = int(tz_arg)
            user_timezones[chat_id] = timezone(timedelta(hours=offset_hours))

            await update.message.reply_text(f"Timezone set to UTC{offset_hours:+}")

        else:
            tz_name = timezone_mappings.get(tz_arg, tz_arg)
            tz = pytz.timezone(tz_name)
            user_timezones[chat_id] = tz

            await update.message.reply_text(f"Timezone set to {tz.zone}")

        if chat_id in chat_histories:
            await greet_user(update, context)

    except (IndexError, ValueError, pytz.UnknownTimeZoneError):
        await update.message.reply_text(
            "Usage:\n"
            "/settimezone <offset_hours> or /settimezone <timezone_name>\n\n"
            "Example:\n"
            "/settimezone +7 or /settimezone Asia/Jakarta or /settimezone Jakarta"
        )


# Fungsi untuk menyapa pengguna
async def greet_user(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.message.chat_id

    user_tz = user_timezones.get(chat_id, timezone.utc)
    user_time = datetime.now(user_tz)
    greeting_prompt = get_greeting_prompt(user_time)
    greeting_message = await get_groq_response([{"role": "user", "content": greeting_prompt}])

    await update.message.reply_text(greeting_message, parse_mode='Markdown')
    chat_histories[chat_id].append({"role": "assistant", "content": greeting_message})

    logging.info(f"/start command processed for chat_id {chat_id}. Greeting message sent.")

    
# Fungsi untuk menangani perintah /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.message.chat_id
    chat_histories[chat_id] = []  # Reset chat history

    if chat_id not in user_timezones:
        await update.message.reply_text(
            "Welcome!\n"
            "To get started, please set your timezone using:\n"
            "/settimezone <offset_hours> or\n"
            "/settimezone <timezone_name>\n\n"
            "Example:\n"
            "/settimezone +7 or\n"
            "/settimezone Asia/Jakarta or\n"
            "/settimezone Jakarta"
        )
    else:
        await greet_user(update, context)

   
# Fungsi untuk command /help
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.message.chat_id

    help_text = (
        "You look like you need my help, let me help you. To use this bot, you can use several features with the commands provided.\n\n"
        "The following are the currently available commands:\n"
        "/help - Displays available commands\n"
        "/quote - Get a random motivational quote\n"
    )
    help_message = escape_markdown_v2(help_text)
    await update.message.reply_text(help_message, parse_mode='MarkdownV2')

    chat_histories[chat_id].append({"role": "assistant", "content": help_message})


# Fungsi untuk command /quote
async def quote_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.message.chat_id

    if chat_id not in chat_histories:
        chat_histories[chat_id] = []

    quote_prompt = (
        "Give me a random quote in MarkdownV2 format. Make sure to use \'>\' at the beginning of each quote line without spaces between \'>\' and the quote text."
        "The quote text should also not use \". Do not include any additional text of preface, only the quote in the folowing format:\n"
        ">Quote text\n"
        "- Author\n\n"
        "Quote explanation\n\n"
    )
    quote_message = await get_groq_response([{"role": "user", "content": quote_prompt}])
    quote_message = escape_markdown_v2(quote_message)

    await update.message.reply_text(quote_message, parse_mode='MarkdownV2')
    # await update.message.reply_text(">Helloworld",parse_mode='MarkdownV2')
    
    chat_histories[chat_id].append({"role": "assistant", "content": quote_message})

  
# Fungsi untuk menangani pesan teks
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.message.chat_id

    if chat_id not in user_timezones:
        await update.message.reply_text("Please set your time first useing /settimezone <offset_hours>")
        return

    if chat_id not in chat_histories:
        chat_histories[chat_id] = []

    user_message = update.message.text.lower()
    chat_histories[chat_id].append({"role": "user", "content": user_message})

    bot_response = await get_groq_response(chat_histories[chat_id])
    bot_response = escape_markdown_v2(bot_response)
    await update.message.reply_text(bot_response, parse_mode='MarkdownV2')

    # Menyimpan balasan bot dalam history
    chat_histories[chat_id].append({"role": "assistant", "content": bot_response})

    # Memangkas banyak chat yang disimpan di history
    trim_chat_history(chat_id, max_length=20)


# Fungsi untuk memanggil Api Groq
async def get_groq_response(history: list) -> str:
    try:
        # Tambahkan pesan sistem
        system_message = {
            "role": "assistant",
            "content": "I\'m Ontabot, also known as Onta, a Telegram Bot AI Asisstant."
        }
        full_history = [system_message] + history
        # if not isinstance(history, list):
        #     history = [{"role": "user", "content": history}]
        
        chat_completion = client.chat.completions.create(
            messages=full_history,
            model="mixtral-8x7b-32768",
            # model="llama3-70b-8192",
        )
        return chat_completion.choices[0].message.content

    except Exception as e:
        logging.error(f"Error: {e}. Please check your API key or contact support.")
        return 'Sorry, an error occurred. Please contact the developer for assistance.\nDev: @ramidze'
    

# Menambahkan fungsi untuk parse MarkdownV2
def escape_markdown_v2(text: str) -> str:
    escape_chars = r'\_*[]()~`#+-=|.{}!'
    return ''.join(['\\' + char
        if char in escape_chars else char for char in text
    ])