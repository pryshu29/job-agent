import logging
import os
from threading import Thread

from flask import Flask
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from config import (
    TELEGRAM_BOT_TOKEN,
    AUTHORIZED_USER_ID,
)

from database import (
    check_database_connection,
    create_indexes,
    create_user,
    get_recent_messages,
    get_user,
    save_message,
    update_agent_state,
    update_profile,
)

from agent import analyze_message


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

# Prevent HTTP libraries from logging Telegram API URLs.
# This also prevents bot tokens from appearing in normal logs.
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)

logging.getLogger("werkzeug").setLevel(logging.WARNING)


# ============================================================
# FLASK HEALTH SERVER
# ============================================================

app = Flask(__name__)


@app.route("/")
def home():

    logger.info(
        "HEALTH | Health check received"
    )

    return "AI Job Agent is alive!"


def run_web():

    port = int(
        os.environ.get(
            "PORT",
            10000,
        )
    )

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
            "AUTH | Missing effective user"
        )

        return False

    user_id = update.effective_user.id

    if user_id != AUTHORIZED_USER_ID:

        logger.warning(
            "AUTH | Unauthorized user rejected | user_id=%s",
            user_id,
        )

        return False

    return True


# ============================================================
# START
# ============================================================

async def start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    logger.info(
        "BOT | /start received"
    )

    if not check_authorization(update):
        return

    user_id = update.effective_user.id

    logger.info(
        "AGENT | Starting user session | user_id=%s",
        user_id,
    )

    try:

        create_user(user_id)

        await update.message.reply_text(
            "👋 Welcome to your AI Career Agent!\n\n"
            "I can help you with:\n"
            "• Career planning\n"
            "• Resume\n"
            "• Job search\n"
            "• Job analysis\n"
            "• Applications\n"
            "• Interview preparation\n"
            "• Certifications\n"
            "• Hackathons and career opportunities\n\n"
            "You can talk naturally. You don't need to "
            "follow a fixed questionnaire."
        )

        logger.info(
            "AGENT | Session initialized | user_id=%s",
            user_id,
        )

    except Exception:

        logger.exception(
            "AGENT | Failed to initialize user | user_id=%s",
            user_id,
        )

        await update.message.reply_text(
            "❌ I couldn't initialize your profile right now. "
            "Please try again."
        )


# ============================================================
# ROUTER RESPONSE
# ============================================================

def build_router_response(
    decision,
) -> str:

    intent = decision.intent

    # --------------------------------------------------------
    # PROFILE
    # --------------------------------------------------------

    if intent == "profile_update":

        response = decision.response

        if decision.next_question:

            response = (
                f"{response}\n\n"
                f"{decision.next_question}"
            )

        return response

    # --------------------------------------------------------
    # RESUME
    # --------------------------------------------------------

    if intent == "resume":

        return (
            "📄 I can work with your resume.\n\n"
            "Resume processing is the next capability we're "
            "connecting. You will be able to send your PDF "
            "directly here, and I'll extract and understand "
            "your career information."
        )

    # --------------------------------------------------------
    # JOB SEARCH
    # --------------------------------------------------------

    if intent == "job_search":

        return (
            "🔎 I understand that you want to search for jobs.\n\n"
            "The job-search engine isn't connected yet. "
            "Once it is connected, I'll search relevant "
            "company career pages and LinkedIn openings "
            "based on your profile and preferences."
        )

    # --------------------------------------------------------
    # JOB ANALYSIS
    # --------------------------------------------------------

    if intent == "job_analysis":

        return (
            "🔍 I understand that you want me to analyze "
            "a specific job opening.\n\n"
            "The job-analysis tool isn't connected yet. "
            "Once connected, I'll be able to analyze the "
            "job description, compare it with your profile "
            "and help prepare a targeted resume."
        )

    # --------------------------------------------------------
    # CAREER RECOMMENDATION
    # --------------------------------------------------------

    if intent == "career_recommendation":

        return decision.response

    # --------------------------------------------------------
    # APPLICATION
    # --------------------------------------------------------

    if intent == "application":

        return (
            "🚀 I understand that you want help with a job "
            "application.\n\n"
            "The application automation layer isn't connected "
            "yet. When we build it, I'll first determine "
            "whether the application can be completed "
            "automatically. If it cannot, I'll provide the "
            "opening URL and the appropriate tailored resume "
            "for you to apply directly."
        )

    # --------------------------------------------------------
    # INTERVIEW
    # --------------------------------------------------------

    if intent == "interview":

        return decision.response

    # --------------------------------------------------------
    # OPPORTUNITY
    # --------------------------------------------------------

    if intent == "opportunity":

        return (
            "🎯 I understand that you're looking for a "
            "career opportunity such as a hackathon, hiring "
            "program, internship, challenge or similar "
            "program.\n\n"
            "The opportunity-search engine isn't connected yet. "
            "We'll add it later."
        )

    # --------------------------------------------------------
    # GENERAL CAREER
    # --------------------------------------------------------

    if intent == "general_career":

        return decision.response

    # --------------------------------------------------------
    # OUT OF SCOPE
    # --------------------------------------------------------

    if intent == "out_of_scope":

        return (
            "I'm focused specifically on helping with your "
            "career, jobs, resume, applications, interviews "
            "and professional opportunities.\n\n"
            "Tell me what you'd like to achieve in your "
            "career and I'll help you with it."
        )

    # --------------------------------------------------------
    # FALLBACK
    # --------------------------------------------------------

    return decision.response


# ============================================================
# TEXT MESSAGE
# ============================================================

async def handle_message(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    if not update.effective_user:

        logger.warning(
            "BOT | Message without user"
        )

        return

    user_id = update.effective_user.id

    logger.info(
        "BOT | Text message received | user_id=%s",
        user_id,
    )

    if not check_authorization(update):
        return

    if not update.message or not update.message.text:

        logger.warning(
            "BOT | Empty text message | user_id=%s",
            user_id,
        )

        return

    user_message = update.message.text

    try:

        # ====================================================
        # LOAD USER
        # ====================================================

        user = get_user(user_id)

        if not user:

            logger.info(
                "AGENT | User missing; creating profile | "
                "user_id=%s",
                user_id,
            )

            create_user(user_id)

            user = get_user(user_id)

        profile = (
            user.get("profile", {})
            if user
            else {}
        )

        agent_state = (
            user.get("agent_state", {})
            if user
            else {}
        )

        current_question = agent_state.get(
            "current_question"
        )

        current_task = agent_state.get(
            "current_task"
        )

        active_job_id = agent_state.get(
            "active_job_id"
        )

        # ====================================================
        # LOAD RECENT CONVERSATION
        # ====================================================

        recent_messages = get_recent_messages(
            user_id=user_id,
            limit=20,
        )

        logger.info(
            "AGENT | Context loaded | "
            "user_id=%s | history_count=%s",
            user_id,
            len(recent_messages),
        )

        # ====================================================
        # GEMINI
        # ====================================================

        logger.info(
            "AGENT | Sending message for analysis | "
            "user_id=%s",
            user_id,
        )

        decision = analyze_message(
            user_message=user_message,
            current_question=current_question,
            current_profile=profile,
            recent_messages=recent_messages,
        )

        # ====================================================
        # SAVE USER MESSAGE
        # ====================================================

        save_message(
            user_id=user_id,
            role="user",
            message=user_message,
        )

        # ====================================================
        # UPDATE PROFILE
        # ====================================================

        if decision.profile_updates:

            logger.info(
                "PROFILE | Applying AI-detected updates | "
                "user_id=%s | count=%s",
                user_id,
                len(decision.profile_updates),
            )

            update_profile(
                user_id,
                decision.profile_updates,
            )

        # ====================================================
        # ROUTE INTENT
        # ====================================================

        logger.info(
            "ROUTER | Routing intent | "
            "user_id=%s | intent=%s",
            user_id,
            decision.intent,
        )

        response_text = build_router_response(
            decision
        )

        # ====================================================
        # UPDATE AGENT STATE
        # ====================================================

        update_agent_state(
            user_id=user_id,
            workflow="career_agent",
            current_question=decision.next_question,
            current_task=current_task,
            active_job_id=active_job_id,
        )

        # ====================================================
        # SEND RESPONSE
        # ====================================================

        await update.message.reply_text(
            response_text
        )

        # ====================================================
        # SAVE ASSISTANT RESPONSE
        # ====================================================

        save_message(
            user_id=user_id,
            role="assistant",
            message=response_text,
        )

        logger.info(
            "AGENT | Response sent | "
            "user_id=%s | intent=%s",
            user_id,
            decision.intent,
        )

    except Exception:

        logger.exception(
            "AGENT | Failed to process message | "
            "user_id=%s",
            user_id,
        )

        try:

            await update.message.reply_text(
                "❌ I had trouble processing that message. "
                "Please try again."
            )

        except Exception:

            logger.exception(
                "BOT | Failed to send error response | "
                "user_id=%s",
                user_id,
            )


# ============================================================
# ERROR HANDLER
# ============================================================

async def error_handler(
    update: object,
    context: ContextTypes.DEFAULT_TYPE,
):

    logger.error(
        "BOT | Unhandled exception",
        exc_info=context.error,
    )


# ============================================================
# MAIN
# ============================================================

def main():

    logger.info(
        "SYSTEM | Starting AI Job Agent"
    )

    # ========================================================
    # CONFIGURATION
    # ========================================================

    logger.info(
        "CONFIG | Validating environment"
    )

    if not TELEGRAM_BOT_TOKEN:

        raise RuntimeError(
            "TELEGRAM_BOT_TOKEN is missing"
        )

    if not AUTHORIZED_USER_ID:

        raise RuntimeError(
            "AUTHORIZED_USER_ID is missing"
        )

    logger.info(
        "CONFIG | Environment validation successful"
    )

    # ========================================================
    # MONGODB
    # ========================================================

    logger.info(
        "MONGODB | Checking connection"
    )

    check_database_connection()

    logger.info(
        "MONGODB | Connection successful"
    )

    create_indexes()

    logger.info(
        "MONGODB | Indexes ready"
    )

    # ========================================================
    # FLASK
    # ========================================================

    web_thread = Thread(
        target=run_web,
        daemon=True,
        name="flask-health-server",
    )

    web_thread.start()

    logger.info(
        "WEB | Health server started"
    )

    # ========================================================
    # TELEGRAM
    # ========================================================

    logger.info(
        "TELEGRAM | Creating application"
    )

    application = (
        Application.builder()
        .token(TELEGRAM_BOT_TOKEN)
        .build()
    )

    # ========================================================
    # HANDLERS
    # ========================================================

    application.add_handler(
        CommandHandler(
            "start",
            start,
        )
    )

    application.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            handle_message,
        )
    )

    application.add_error_handler(
        error_handler
    )

    logger.info(
        "TELEGRAM | Handlers registered"
    )

    # ========================================================
    # POLLING
    # ========================================================

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
            "SYSTEM | AI Job Agent stopped"
        )

        raise
