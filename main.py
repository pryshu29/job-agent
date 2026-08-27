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


# ============================================================
# LOGGING
# ============================================================

LOG_FORMAT = (
    "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
)

logging.basicConfig(
    format=LOG_FORMAT,
    level=logging.INFO,
)

logger = logging.getLogger("AI_JOB_AGENT")

# Prevent HTTP client logs from exposing URLs containing tokens.
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)

# Reduce Flask/Werkzeug noise.
logging.getLogger("werkzeug").setLevel(logging.WARNING)


# ============================================================
# CONVERSATION STATES
# ============================================================

ROLE, LOCATION, SALARY = range(3)


# ============================================================
# FLASK HEALTH SERVER
# ============================================================

app = Flask(__name__)


@app.route("/")
def home():
    logger.info("HEALTH | Health check received")
    return "AI Job Agent is alive!"


def run_web():
    port = int(os.environ.get("PORT", 10000))

    logger.info(
        "WEB | Starting health server | port=%s",
        port,
    )

    app.run(
        host="0.0.0.0",
        port=port,
        debug=False,
        use_reloader=False,
    )


# ============================================================
# AUTHORIZATION
# ============================================================

def check_authorization(update: Update) -> bool:
    if not update.effective_user:
        logger.warning(
            "AUTH | Message received without effective user"
        )
        return False

    user_id = update.effective_user.id

    if user_id != AUTHORIZED_USER_ID:
        logger.warning(
            "AUTH | Unauthorized user rejected | user_id=%s",
            user_id,
        )
        return False

    logger.info(
        "AUTH | User authorized | user_id=%s",
        user_id,
    )

    return True


# ============================================================
# START COMMAND
# ============================================================

async def start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    logger.info("BOT | /start received")

    if not check_authorization(update):
        return ConversationHandler.END

    user_id = update.effective_user.id

    logger.info(
        "ONBOARDING | Starting onboarding | user_id=%s",
        user_id,
    )

    await update.message.reply_text(
        "👋 Welcome to AI Job Agent!\n\n"
        "I'll help you find jobs, optimize resumes "
        "and prepare applications.\n\n"
        "First question:\n"
        "💼 What role are you looking for?"
    )

    logger.info(
        "ONBOARDING | Waiting for role | user_id=%s",
        user_id,
    )

    return ROLE


# ============================================================
# ROLE
# ============================================================

async def role(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    user_id = update.effective_user.id

    logger.info(
        "ONBOARDING | Role received | user_id=%s",
        user_id,
    )

    context.user_data["role"] = update.message.text

    await update.message.reply_text(
        "📍 Great!\nWhich locations do you prefer?"
    )

    logger.info(
        "ONBOARDING | Waiting for location | user_id=%s",
        user_id,
    )

    return LOCATION


# ============================================================
# LOCATION
# ============================================================

async def location(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    user_id = update.effective_user.id

    logger.info(
        "ONBOARDING | Location received | user_id=%s",
        user_id,
    )

    context.user_data["location"] = update.message.text

    await update.message.reply_text(
        "💰 What's your minimum expected salary?"
        "\nExample: 12 LPA"
    )

    logger.info(
        "ONBOARDING | Waiting for salary | user_id=%s",
        user_id,
    )

    return SALARY


# ============================================================
# SALARY
# ============================================================

async def salary(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    user_id = update.effective_user.id

    logger.info(
        "ONBOARDING | Salary received | user_id=%s",
        user_id,
    )

    context.user_data["salary"] = update.message.text

    preferences = {
        "role": context.user_data["role"],
        "location": context.user_data["location"],
        "salary": context.user_data["salary"],
    }

    logger.info(
        "PROFILE | Saving preferences | user_id=%s",
        user_id,
    )

    try:
        save_preferences(
            user_id,
            preferences,
        )

        logger.info(
            "MONGODB | Preferences saved | user_id=%s",
            user_id,
        )

    except Exception:
        logger.exception(
            "MONGODB | Failed to save preferences | user_id=%s",
            user_id,
        )

        await update.message.reply_text(
            "❌ I couldn't save your profile right now. "
            "Please try again."
        )

        return ConversationHandler.END

    await update.message.reply_text(
        "✅ Your job profile has been created!\n\n"
        f"Role: {preferences['role']}\n"
        f"Location: {preferences['location']}\n"
        f"Salary: {preferences['salary']}\n\n"
        "Next we'll build your resume profile."
    )

    logger.info(
        "ONBOARDING | Completed successfully | user_id=%s",
        user_id,
    )

    return ConversationHandler.END


# ============================================================
# CANCEL
# ============================================================

async def cancel(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    user_id = (
        update.effective_user.id
        if update.effective_user
        else "unknown"
    )

    logger.info(
        "ONBOARDING | Cancelled | user_id=%s",
        user_id,
    )

    await update.message.reply_text(
        "Onboarding cancelled."
    )

    return ConversationHandler.END


# ============================================================
# GLOBAL ERROR HANDLER
# ============================================================

async def error_handler(
    update: object,
    context: ContextTypes.DEFAULT_TYPE,
):
    logger.exception(
        "BOT | Unhandled exception",
        exc_info=context.error,
    )


# ============================================================
# MAIN
# ============================================================

def main():

    logger.info("SYSTEM | Starting AI Job Agent")

    # --------------------------------------------------------
    # Environment validation
    # --------------------------------------------------------

    logger.info("CONFIG | Checking required environment variables")

    if not TELEGRAM_BOT_TOKEN:
        logger.critical(
            "CONFIG | TELEGRAM_BOT_TOKEN is missing"
        )
        raise RuntimeError(
            "TELEGRAM_BOT_TOKEN is missing"
        )

    if not AUTHORIZED_USER_ID:
        logger.critical(
            "CONFIG | AUTHORIZED_USER_ID is missing"
        )
        raise RuntimeError(
            "AUTHORIZED_USER_ID is missing"
        )

    logger.info(
        "CONFIG | Required environment variables are present"
    )

    # --------------------------------------------------------
    # MongoDB
    # --------------------------------------------------------

    logger.info("MONGODB | Testing database connection")

    try:
        check_database_connection()

        logger.info(
            "MONGODB | Connection successful"
        )

    except Exception:
        logger.exception(
            "MONGODB | Connection failed"
        )
        raise

    # --------------------------------------------------------
    # Flask
    # --------------------------------------------------------

    logger.info(
        "WEB | Starting background health server"
    )

    web_thread = Thread(
        target=run_web,
        daemon=True,
        name="flask-health-server",
    )

    web_thread.start()

    logger.info(
        "WEB | Health server thread started"
    )

    # --------------------------------------------------------
    # Telegram
    # --------------------------------------------------------

    logger.info(
        "TELEGRAM | Building Telegram application"
    )

    application = (
        Application.builder()
        .token(TELEGRAM_BOT_TOKEN)
        .build()
    )

    logger.info(
        "TELEGRAM | Application created"
    )

    # --------------------------------------------------------
    # Conversation handler
    # --------------------------------------------------------

    conversation = ConversationHandler(
        entry_points=[
            CommandHandler(
                "start",
                start,
            )
        ],
        states={
            ROLE: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    role,
                )
            ],
            LOCATION: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    location,
                )
            ],
            SALARY: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    salary,
                )
            ],
        },
        fallbacks=[
            CommandHandler(
                "cancel",
                cancel,
            )
        ],
    )

    application.add_handler(
        conversation
    )

    application.add_error_handler(
        error_handler
    )

    logger.info(
        "TELEGRAM | Handlers registered"
    )

    # --------------------------------------------------------
    # Start polling
    # --------------------------------------------------------

    logger.info(
        "TELEGRAM | Starting polling"
    )

    application.run_polling(
        drop_pending_updates=True
    )


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    try:
        main()

    except Exception:
        logger.exception(
            "SYSTEM | AI Job Agent stopped because of an error"
        )
        raise
