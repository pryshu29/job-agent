import logging
from typing import Optional

from app.agent.context import (
    format_recent_messages,
)

from app.agent.prompts import (
    RESUME_SYSTEM_INSTRUCTION,
    SYSTEM_INSTRUCTION,
)

from app.ai import (
    generate_content,
)

from app.models import (
    AgentDecision,
    ResumeProfile,
)


logger = logging.getLogger(
    "AI_JOB_AGENT"
)


# ============================================================
# GENERIC GEMINI REQUEST
# ============================================================

def generate_with_fallback(
    contents,
    system_instruction,
    response_schema,
):

    return generate_content(
        contents=contents,
        system_instruction=system_instruction,
        response_schema=response_schema,
    )


# ============================================================
# MESSAGE ANALYSIS
# ============================================================

def analyze_message(
    user_message: str,
    current_question: Optional[str] = None,
    current_profile: Optional[dict] = None,
    recent_messages: Optional[list] = None,
) -> AgentDecision:

    logger.info(
        "AGENT | Starting message analysis"
    )

    profile = current_profile or {}

    history = format_recent_messages(
        recent_messages or []
    )

    context = f"""
CURRENT AGENT QUESTION:
{current_question or "No question currently pending."}

CURRENT KNOWN PROFILE:
{profile}

RECENT CONVERSATION:
{history}

CURRENT USER MESSAGE:
{user_message}
"""

    logger.info(
        "AGENT | Sending context for analysis | "
        "history_messages=%s | profile_fields=%s | "
        "has_current_question=%s",
        len(recent_messages or []),
        len(profile),
        bool(current_question),
    )

    decision = generate_with_fallback(
        contents=context,
        system_instruction=SYSTEM_INSTRUCTION,
        response_schema=AgentDecision,
    )

    logger.info(
        "AGENT | Intent detected | intent=%s",
        decision.intent,
    )

    logger.info(
        "AGENT | Profile updates detected | count=%s",
        len(decision.profile_updates),
    )

    logger.info(
        "AGENT | Clarification required | value=%s",
        decision.needs_clarification,
    )

    if decision.next_question:

        logger.info(
            "AGENT | Next question generated"
        )

    return decision


# ============================================================
# RESUME EXTRACTION
# ============================================================

def extract_resume_profile(
    resume_text: str,
) -> ResumeProfile:

    logger.info(
        "RESUME | Starting AI resume extraction | "
        "characters=%s",
        len(resume_text),
    )

    if not resume_text.strip():

        logger.warning(
            "RESUME | Empty resume text received"
        )

        raise ValueError(
            "Resume text is empty."
        )

    resume_prompt = f"""
RESUME TEXT:

{resume_text}
"""

    profile = generate_with_fallback(
        contents=resume_prompt,
        system_instruction=RESUME_SYSTEM_INSTRUCTION,
        response_schema=ResumeProfile,
    )

    logger.info(
        "RESUME | AI extraction completed | "
        "skills=%s | experience=%s | education=%s | "
        "projects=%s | certifications=%s",
        len(profile.skills),
        len(profile.experience),
        len(profile.education),
        len(profile.projects),
        len(profile.certifications),
    )

    return profile