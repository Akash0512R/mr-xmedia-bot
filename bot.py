
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

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

TOKEN = os.environ["BOT_TOKEN"]
WEBHOOK_URL = os.environ.get("WEBHOOK_URL", "").rstrip("/")
WEBHOOK_SECRET = os.environ["WEBHOOK_SECRET"]

PORT = int(os.environ.get("PORT", "10000"))

app = Flask(__name__)

loop = asyncio.new_event_loop()
telegram_app = Application.builder().token(TOKEN).build()

bot_ready = threading.Event()


async def start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    if update.message:
        await update.message.reply_text(
            "Welcome to Mr Xmedia! 📥\n\n"
            "Send me a public media URL to get started."
        )


async def handle_link(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    if not update.message or not update.message.text:
        return

    url = update.message.text.strip()

    if not url.startswith(("https://", "http://")):
        await update.message.reply_text(
            "Please send a valid HTTP or HTTPS URL."
        )
        return

    await update.message.reply_text(
        "Link received! ✅\n\n"
        "Actual media downloading and quality selection "
        "will be added next."
    )


telegram_app.add_handler(
    CommandHandler("start", start)
)

telegram_app.add_handler(
    MessageHandler(
        filters.TEXT & ~filters.COMMAND,
        handle_link,
    )
)


async def initialize_bot():
    await telegram_app.initialize()
    await telegram_app.start()

    if WEBHOOK_URL:
        await telegram_app.bot.set_webhook(
            url=f"{WEBHOOK_URL}/webhook",
            secret_token=WEBHOOK_SECRET,
            allowed_updates=["message"],
        )
        logging.info("Telegram webhook configured.")
    else:
        logging.warning(
            "WEBHOOK_URL is empty. "
            "Add it in Render environment variables."
        )

    bot_ready.set()


def run_telegram_loop():
    asyncio.set_event_loop(loop)

    try:
        loop.run_until_complete(initialize_bot())
        loop.run_forever()
    except Exception:
        logging.exception("Telegram bot startup failed.")


threading.Thread(
    target=run_telegram_loop,
    daemon=True,
).start()


@app.route("/", methods=["GET"])
def home():
    return "Mr Xmedia is running!", 200


@app.route("/health", methods=["GET"])
def health():
    if bot_ready.is_set():
        return "OK", 200
    return "Starting", 503


@app.route("/webhook", methods=["POST"])
def webhook():
    if not bot_ready.is_set():
        return "Bot is starting", 503

    provided_secret = request.headers.get(
        "X-Telegram-Bot-Api-Secret-Token", ""
    )

    if provided_secret != WEBHOOK_SECRET:
        return "Forbidden", 403

    data = request.get_json(silent=True)

    if not data:
        return "Bad request", 400

    try:
        update = Update.de_json(data, telegram_app.bot)

        future = asyncio.run_coroutine_threadsafe(
            telegram_app.process_update(update),
            loop,
        )

        # Report unexpected processing failures in server logs.
        def log_result(completed_future):
            try:
                completed_future.result()
            except Exception:
                logging.exception("Failed to process Telegram update.")

        future.add_done_callback(log_result)

        return "OK", 200

    except Exception:
        logging.exception("Webhook handling failed.")
        return "Internal server error", 500
