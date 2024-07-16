import logging
import os
import pytz
from groq import Groq
from datetime import datetime, timedelta, timezone
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from ontabot.handlers import set_timezone, start, help_command, quote_command, handle_message, GroqClient
from dotenv import load_dotenv

# Memuat variabel environtment
load_dotenv()

# Token API
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
GROQ_API_KEY = os.getenv('GROQ_API_KEY')

# Konfigurasi logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s\n',
    level=logging.INFO
)


# Fungsi utama untuk menjalankan bot
def main():
    if not TELEGRAM_TOKEN:
        raise ValueError("TELEGRAM_TOKEN environtment variable not set")
    if not GROQ_API_KEY:
        raise ValueError("GROQ_API_KEY environtment variable not set")

    # Inisialisasi client Groq
    client = Groq(api_key=GROQ_API_KEY)
    GroqClient(client) # Pass client ke handler
    
    # Masukkan token API bot Anda di sini
    application = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    # Menambahkan handler untuk perintah /start
    application.add_handler(CommandHandler('start', start))

    # Menambahkan handler untuk perintah /help
    application.add_handler(CommandHandler('help', help_command))

    # Menambahkan handler untuk perintah /quote
    application.add_handler(CommandHandler('quote', quote_command))

    # Menambahkan handler untuk perintah /settimezone
    application.add_handler(CommandHandler('settimezone', set_timezone))

    # Menambahkan handler untuk pesan teks
    application.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND, handle_message
    ))

    # Jalankan bot
    application.run_polling()


if __name__ == '__main__':
    main()
