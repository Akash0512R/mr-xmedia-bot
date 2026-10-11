
import os
import asyncio
import threading
import logging
from flask import Flask, request
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

logging.basicConfig(level=logging.INFO)

TOKEN = os.environ["BOT_TOKEN"]
WEBHOOK_URL = os.environ["WEBHOOK_URL"].rstrip("/")
WEBHOOK_SECRET = os.environ["WEBHOOK_SECRET"]

app = Flask(__name__)
loop = asyncio.new_event_loop()
telegram_app = Application.builder().token(TOKEN).build()


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Welcome to Mr Xmedia! 📥\n"
        "Send me a public media URL to get started."
    )


async def handle_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text.strip()
    if not url.startswith(("https://", "http://")):
        await update.message.reply_text("Please send a valid URL.")
        return

    await update.message.reply_text(
        "Link received! ✅\nDownloader support is coming next."
    )


telegram_app.add_handler(CommandHandler("start", start))
telegram_app.add_handler(
    MessageHandler(filters.TEXT & ~filters.COMMAND, handle_link)
)


def run_telegram_loop():
    asyncio.set_event_loop(loop)
    loop.run_until_complete(telegram_app.initialize())
    loop.run_until_complete(telegram_app.start())
    loop.run_until_complete(
        telegram_app.bot.set_webhook(
            url=f"{WEBHOOK_URL}/webhook",
            secret_token=WEBHOOK_SECRET,
            allowed_updates=["message"],
        )
    )
    loop.run_forever()


threading.Thread(target=run_telegram_loop, daemon=True).start()


@app.route("/", methods=["GET"])
def home():
    return "Mr Xmedia is running!", 200


@app.route("/webhook", methods=["POST"])
def webhook():
    if request.headers.get(
        "X-Telegram-Bot-Api-Secret-Token"
    ) != WEBHOOK_SECRET:
        return "Forbidden", 403

    data = request.get_json(silent=True)
    if not data:
        return "Bad request", 400

    update = Update.de_json(data, telegram_app.bot)
    asyncio.run_coroutine_threadsafe(
        telegram_app.process_update(update), loop
    )
    return "OK", 200
