import logging
import os
from threading import Thread

from flask import Flask
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from config import TELEGRAM_BOT_TOKEN, AUTHORIZED_USER_ID
from database import check_database_connection, save_preferences

logging.basicConfig(level=logging.INFO)

ROLE, LOCATION, SALARY = range(3)

app = Flask(__name__)

@app.route("/")
def home():
    return "AI Job Agent Running"

def run_web():
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))

def authorized(update: Update):
    return (
        update.effective_user
        and update.effective_user.id == AUTHORIZED_USER_ID
    )

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not authorized(update):
        return ConversationHandler.END

    await update.message.reply_text(
        "👋 Welcome to AI Job Agent!\n\n"
        "I'll help you find jobs, optimize resumes and prepare applications.\n\n"
        "First question:\n"
        "💼 What role are you looking for?"
    )
    return ROLE

async def role(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["role"] = update.message.text

    await update.message.reply_text(
        "📍 Great!\nWhich locations do you prefer?"
    )
    return LOCATION

async def location(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["location"] = update.message.text

    await update.message.reply_text(
        "💰 What's your minimum expected salary? (Example: 12 LPA)"
    )
    return SALARY

async def salary(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["salary"] = update.message.text

    save_preferences(
        update.effective_user.id,
        {
            "role": context.user_data["role"],
            "location": context.user_data["location"],
            "salary": context.user_data["salary"],
        },
    )

    await update.message.reply_text(
        "✅ Your job profile has been created!\n\n"
        f"Role: {context.user_data['role']}\n"
        f"Location: {context.user_data['location']}\n"
        f"Salary: {context.user_data['salary']}\n\n"
        "Next we'll build your resume profile."
    )

    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Onboarding cancelled.")
    return ConversationHandler.END

def main():
    check_database_connection()

    Thread(target=run_web, daemon=True).start()

    app_bot = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    conversation = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            ROLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, role)],
            LOCATION: [MessageHandler(filters.TEXT & ~filters.COMMAND, location)],
            SALARY: [MessageHandler(filters.TEXT & ~filters.COMMAND, salary)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    app_bot.add_handler(conversation)

    app_bot.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
