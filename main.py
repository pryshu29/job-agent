import logging
import os
import tempfile
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
)

from database import (
    check_database_connection,
    create_indexes,
    create_user,
    get_recent_messages,
    get_user,
    save_message,
    save_resume_profile,
    update_agent_state,
    update_profile,
)

from agent import (
    analyze_message,
    extract_resume_profile,
)

from resume_parser import (
    extract_resume_text,
)


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


logger = logging.getLogger(
    "AI_JOB_AGENT"
)


# Do not expose Telegram API URLs/tokens in logs.
logging.getLogger(
    "httpx"
).setLevel(logging.WARNING)

logging.getLogger(
    "httpcore"
).setLevel(logging.WARNING)

logging.getLogger(
    "werkzeug"
).setLevel(logging.WARNING)


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
# USER SESSION
# ============================================================

def ensure_user(
    user_id,
):

    logger.info(
        "USER | Checking user session | "
        "user_id=%s",
        user_id,
    )

    user = get_user(
        user_id
    )

    if not user:

        logger.info(
            "USER | New user detected; creating profile | "
            "user_id=%s",
            user_id,
        )

        create_user(
            user_id
        )

        user = get_user(
            user_id
        )

    logger.info(
        "USER | User session ready | "
        "user_id=%s",
        user_id,
    )

    return user


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

    if not update.effective_user:

        logger.warning(
            "BOT | /start without effective user"
        )

        return

    user_id = update.effective_user.id

    logger.info(
        "AGENT | Starting user session | "
        "user_id=%s",
        user_id,
    )

    try:

        ensure_user(
            user_id
        )

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
            "follow a fixed questionnaire.\n\n"
            "📄 You can also send your resume PDF "
            "directly in this chat."
        )

        logger.info(
            "AGENT | Session initialized | "
            "user_id=%s",
            user_id,
        )

    except Exception:

        logger.exception(
            "AGENT | Failed to initialize user | "
            "user_id=%s",
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

    if intent == "profile_update":

        response = decision.response

        if decision.next_question:

            response = (
                f"{response}\n\n"
                f"{decision.next_question}"
            )

        return response

    if intent == "resume":

        return (
            "📄 Please send your resume as a PDF "
            "document here. I'll extract the information "
            "and add it to your career profile."
        )

    if intent == "job_search":

        return (
            "🔎 I understand that you want to search "
            "for jobs.\n\n"
            "The job-search engine isn't connected yet. "
            "We'll connect company career pages and "
            "LinkedIn job searching next."
        )

    if intent == "job_analysis":

        return (
            "🔍 I understand that you want to analyze "
            "a specific job opening.\n\n"
            "The job-analysis engine isn't connected yet. "
            "We'll add URL and job-description analysis next."
        )

    if intent == "career_recommendation":

        return decision.response

    if intent == "application":

        return (
            "🚀 I understand that you want help applying "
            "for a job.\n\n"
            "The application automation layer isn't "
            "connected yet."
        )

    if intent == "interview":

        return decision.response

    if intent == "opportunity":

        return (
            "🎯 I understand that you're looking for "
            "career opportunities such as hackathons, "
            "internships, hiring programs or challenges.\n\n"
            "The opportunity-search engine isn't connected "
            "yet."
        )

    if intent == "general_career":

        return decision.response

    if intent == "out_of_scope":

        return (
            "I'm focused on helping with your career, "
            "jobs, resume, applications, interviews and "
            "professional opportunities.\n\n"
            "Tell me what you'd like to achieve in your "
            "career."
        )

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
        "BOT | Text message received | "
        "user_id=%s",
        user_id,
    )

    if not update.message or not update.message.text:

        logger.warning(
            "BOT | Empty text message | "
            "user_id=%s",
            user_id,
        )

        return

    user_message = update.message.text

    try:

        user = ensure_user(
            user_id
        )

        profile = (
            user.get(
                "profile",
                {}
            )
            if user
            else {}
        )

        agent_state = (
            user.get(
                "agent_state",
                {}
            )
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

        save_message(
            user_id=user_id,
            role="user",
            message=user_message,
        )

        if decision.profile_updates:

            logger.info(
                "PROFILE | Applying AI-detected updates | "
                "user_id=%s | count=%s",
                user_id,
                len(
                    decision.profile_updates
                ),
            )

            update_profile(
                user_id,
                decision.profile_updates,
            )

        logger.info(
            "ROUTER | Routing intent | "
            "user_id=%s | intent=%s",
            user_id,
            decision.intent,
        )

        response_text = build_router_response(
            decision
        )

        update_agent_state(
            user_id=user_id,
            workflow="career_agent",
            current_question=decision.next_question,
            current_task=current_task,
            active_job_id=active_job_id,
        )

        await update.message.reply_text(
            response_text
        )

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
# PDF RESUME HANDLER
# ============================================================

async def handle_resume_document(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    if not update.effective_user:

        logger.warning(
            "RESUME | Document without user"
        )

        return

    user_id = update.effective_user.id

    logger.info(
        "BOT | Document received | user_id=%s",
        user_id,
    )

    if not update.message or not update.message.document:

        logger.warning(
            "RESUME | Missing document | "
            "user_id=%s",
            user_id,
        )

        return

    document = update.message.document

    filename = (
        document.file_name
        or "resume.pdf"
    )

    logger.info(
        "RESUME | Document metadata received | "
        "user_id=%s | filename=%s | size=%s",
        user_id,
        filename,
        document.file_size,
    )

    if not filename.lower().endswith(
        ".pdf"
    ):

        await update.message.reply_text(
            "❌ Please send your resume as a PDF file."
        )

        logger.warning(
            "RESUME | Unsupported document type | "
            "user_id=%s",
            user_id,
        )

        return

    temporary_path = None

    try:

        ensure_user(
            user_id
        )

        await update.message.reply_text(
            "📄 I received your resume. "
            "I'm reading it now..."
        )

        # ====================================================
        # DOWNLOAD
        # ====================================================

        logger.info(
            "RESUME | Requesting Telegram file | "
            "user_id=%s",
            user_id,
        )

        telegram_file = await context.bot.get_file(
            document.file_id
        )

        with tempfile.NamedTemporaryFile(
            suffix=".pdf",
            delete=False,
        ) as temporary_file:

            temporary_path = (
                temporary_file.name
            )

        logger.info(
            "RESUME | Downloading PDF temporarily | "
            "user_id=%s",
            user_id,
        )

        await telegram_file.download_to_drive(
            custom_path=temporary_path
        )

        logger.info(
            "RESUME | PDF downloaded | "
            "user_id=%s",
            user_id,
        )

        # ====================================================
        # EXTRACT TEXT
        # ====================================================

        resume_text = extract_resume_text(
            temporary_path
        )

        logger.info(
            "RESUME | Text extraction completed | "
            "user_id=%s | characters=%s",
            user_id,
            len(resume_text),
        )

        # ====================================================
        # GEMINI
        # ====================================================

        logger.info(
            "RESUME | Sending extracted resume "
            "to Gemini | user_id=%s",
            user_id,
        )

        resume_profile = extract_resume_profile(
            resume_text
        )

        logger.info(
            "RESUME | Gemini profile extraction completed | "
            "user_id=%s",
            user_id,
        )

        # ====================================================
        # MONGODB
        # ====================================================

        save_resume_profile(
            user_id=user_id,
            resume_profile=resume_profile,
            filename=filename,
        )

        # ====================================================
        # CONVERSATION
        # ====================================================

        save_message(
            user_id=user_id,
            role="user",
            message=(
                f"[Resume uploaded: {filename}]"
            ),
        )

        # ====================================================
        # RESPONSE
        # ====================================================

        skills_count = len(
            resume_profile.skills
        )

        experience_count = len(
            resume_profile.experience
        )

        education_count = len(
            resume_profile.education
        )

        response_text = (
            "✅ I've reviewed your resume.\n\n"
            f"📌 Skills found: {skills_count}\n"
            f"💼 Experience entries: {experience_count}\n"
            f"🎓 Education entries: {education_count}\n\n"
            "I've added the extracted information to "
            "your career profile.\n\n"
            "You can now tell me additional information, "
            "correct anything I extracted, or tell me "
            "what type of job you're targeting."
        )

        await update.message.reply_text(
            response_text
        )

        save_message(
            user_id=user_id,
            role="assistant",
            message=response_text,
        )

        update_agent_state(
            user_id=user_id,
            workflow="career_agent",
            current_question=None,
            current_task=None,
            active_job_id=None,
        )

        logger.info(
            "RESUME | Resume processing completed | "
            "user_id=%s",
            user_id,
        )

    except Exception:

        logger.exception(
            "RESUME | Failed to process resume | "
            "user_id=%s",
            user_id,
        )

        await update.message.reply_text(
            "❌ I couldn't process that resume.\n\n"
            "Please make sure it is a readable PDF "
            "and try again."
        )

    finally:

        # ====================================================
        # DELETE TEMPORARY FILE
        # ====================================================

        if temporary_path:

            try:

                if os.path.exists(
                    temporary_path
                ):

                    os.remove(
                        temporary_path
                    )

                    logger.info(
                        "RESUME | Temporary PDF deleted | "
                        "user_id=%s",
                        user_id,
                    )

            except Exception:

                logger.exception(
                    "RESUME | Failed to delete temporary PDF | "
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
    # COMMANDS
    # ========================================================

    application.add_handler(
        CommandHandler(
            "start",
            start,
        )
    )

    # ========================================================
    # PDF DOCUMENT
    # ========================================================

    application.add_handler(
        MessageHandler(
            filters.Document.PDF,
            handle_resume_document,
        )
    )

    # ========================================================
    # TEXT
    # ========================================================

    application.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            handle_message,
        )
    )

    # ========================================================
    # ERROR HANDLER
    # ========================================================

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