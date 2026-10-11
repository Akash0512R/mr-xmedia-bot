
import os
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
PORT = int(os.environ.get("PORT", "10000"))

app = Flask(__name__)
telegram_app = Application.builder().token(TOKEN).build()


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Welcome to Mr Xmedia! 📥\n"
        "Send me a supported public media URL to get started."
    )


async def handle_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text.strip()

    if not url.startswith(("https://", "http://")):
        await update.message.reply_text("Please send a valid URL.")
        return

    await update.message.reply_text(
        "Link received! ✅\n"
        "Downloader support will be added in the next step."
    )


telegram_app.add_handler(CommandHandler("start", start))
telegram_app.add_handler(
    MessageHandler(filters.TEXT & ~filters.COMMAND, handle_link)
)


@app.route("/", methods=["GET"])
def home():
    return "Mr Xmedia is running!", 200


@app.route("/webhook", methods=["POST"])
async def webhook():
    if request.headers.get("X-Telegram-Bot-Api-Secret-Token") != os.environ["WEBHOOK_SECRET"]:
        return "Forbidden", 403

    data = request.get_json(silent=True)
    if not data:
        return "Bad request", 400

    update = Update.de_json(data, telegram_app.bot)
    await telegram_app.process_update(update)
    return "OK", 200


async def initialize_bot():
    await telegram_app.initialize()
    await telegram_app.start()
    await telegram_app.bot.set_webhook(
        url=f"{WEBHOOK_URL}/webhook",
        secret_token=os.environ["WEBHOOK_SECRET"],
        allowed_updates=["message"],
    )


import asyncio

asyncio.run(initialize_bot())
