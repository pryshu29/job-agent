import logging

from flask import Flask
from threading import Thread

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

from config import TELEGRAM_BOT_TOKEN, AUTHORIZED_USER_ID
from database import check_database_connection


logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)


app = Flask(__name__)


@app.route("/")
def home():
    return "AI Job Agent is alive!"


def run_web():
    import os

    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)


def check_authorization(update: Update) -> bool:
    if not update.effective_user:
        return False

    return update.effective_user.id == AUTHORIZED_USER_ID


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not check_authorization(update):
        return

    await update.message.reply_text(
        "🤖 AI Job Agent is online!"
    )


def main():
    if not TELEGRAM_BOT_TOKEN:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is missing")

    if not AUTHORIZED_USER_ID:
        raise RuntimeError("AUTHORIZED_USER_ID is missing")

    if not check_database_connection():
        raise RuntimeError("MongoDB connection failed")

    web_thread = Thread(target=run_web, daemon=True)
    web_thread.start()

    application = (
        Application.builder()
        .token(TELEGRAM_BOT_TOKEN)
        .build()
    )

    application.add_handler(
        CommandHandler("start", start)
    )

    print("MongoDB connected successfully.")
    print("AI Job Agent is starting...")

    application.run_polling(
        drop_pending_updates=True
    )


if __name__ == "__main__":
    main()
