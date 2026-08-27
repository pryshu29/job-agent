import logging
from typing import Literal, Optional

from google import genai
from google.genai import types
from pydantic import BaseModel, Field

from config import GEMINI_API_KEY


logger = logging.getLogger("AI_JOB_AGENT")


# ============================================================
# GEMINI CLIENT
# ============================================================

if not GEMINI_API_KEY:
    raise RuntimeError("GEMINI_API_KEY is missing")

client = genai.Client(api_key=GEMINI_API_KEY)

PRIMARY_MODEL = "gemini-3.6-flash"
FALLBACK_MODEL = "gemini-3.5-flash-lite"


# ============================================================
# AGENT RESPONSE SCHEMA
# ============================================================

class ProfileUpdate(BaseModel):
    field: str = Field(
        description="The candidate profile field to update."
    )

    value: str = Field(
        description="The value to store for that field."
    )


class AgentDecision(BaseModel):
    intent: Literal[
        "answer_current_question",
        "add_profile_information",
        "correct_information",
        "ask_related_question",
        "career_question",
        "unrelated_request",
        "general_conversation",
    ]

    profile_updates: list[ProfileUpdate] = Field(
        default_factory=list,
        description=(
            "Useful candidate information explicitly provided "
            "by the user. Only include information relevant to "
            "career, job search, resume, education, skills, "
            "experience, preferences, or applications."
        ),
    )

    needs_clarification: bool = False

    response: str = Field(
        description=(
            "The response the career agent should send to the user. "
            "Keep the response focused on the user's career/job "
            "agent context."
        )
    )

    next_question: Optional[str] = Field(
        default=None,
        description=(
            "The next useful career-related question to ask, "
            "if more information is needed."
        )
    )


# ============================================================
# SYSTEM INSTRUCTION
# ============================================================

SYSTEM_INSTRUCTION = """
You are the AI reasoning layer of an AI Career Agent.

Your job is to understand the user's message in the context of
their career, job search, resume, education, skills, experience,
applications, interviews, opportunities, and career development.

IMPORTANT RULES:

1. Understand context before deciding what the user's message means.

2. NEVER assume that the user's message is automatically an answer
   to the previous question.

3. If the user provides useful career information while answering
   another question, extract BOTH pieces of information.

4. If the user corrects previously provided information, identify
   the correction.

5. If the user asks a related career question, answer it and keep
   the conversation focused on the career-agent task.

6. If the user asks something unrelated to career, jobs, resumes,
   applications, interviews, education, skills, opportunities,
   or career development, do not become a general-purpose chatbot.
   Politely keep the conversation within the career-agent scope.

7. Never invent candidate information.

8. Only extract information explicitly stated or clearly implied
   by the user's message.

9. Do not store passwords, OTPs, API keys, authentication tokens,
   cookies, or other credentials as profile information.

10. Do not treat sensitive authentication information as normal
    candidate profile data.

11. The agent can understand natural language and multiple pieces
    of information in one message.

12. Keep responses concise and conversational.

13. The Python application, not you, controls database updates
    and future actions.

You are currently handling the candidate profile/onboarding stage.
Do not pretend that job searching, resume generation, web searching,
or application submission has happened unless the application
actually performs that operation.
"""


# ============================================================
# AGENT ANALYSIS
# ============================================================

def analyze_message(
    user_message: str,
    current_question: Optional[str] = None,
    current_profile: Optional[dict] = None,
    recent_messages: Optional[list] = None,
) -> AgentDecision:

    logger.info("GEMINI | Starting message analysis")

    profile = current_profile or {}
    history = recent_messages or []

    conversation_context = []

    for item in history:
        role = item.get("role", "unknown")
        message = item.get("message", "")

        conversation_context.append(
            f"{role}: {message}"
        )

    history_text = "\n".join(
        conversation_context
    )

    context = f"""
CURRENT AGENT QUESTION:
{current_question or "No question currently pending."}

CURRENT KNOWN PROFILE:
{profile}

RECENT CONVERSATION:
{history_text or "No previous conversation."}

CURRENT USER MESSAGE:
{user_message}
"""

    models_to_try = [
        PRIMARY_MODEL,
        FALLBACK_MODEL,
    ]

    last_error = None

    for model_name in models_to_try:

        logger.info(
            "GEMINI | Trying model | model=%s",
            model_name,
        )

        try:

            response = client.models.generate_content(
                model=model_name,
                contents=context,
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_INSTRUCTION,
                    response_mime_type="application/json",
                    response_schema=AgentDecision,
                ),
            )

            logger.info(
                "GEMINI | Response received | model=%s",
                model_name,
            )

            if response.parsed:

                decision = response.parsed

            else:

                logger.warning(
                    "GEMINI | Parsed response unavailable | model=%s",
                    model_name,
                )

                decision = AgentDecision.model_validate_json(
                    response.text
                )

            logger.info(
                "AGENT | Intent detected | intent=%s",
                decision.intent,
            )

            logger.info(
                "AGENT | Profile updates detected | count=%s",
                len(decision.profile_updates),
            )

            return decision

        except Exception as exc:

            last_error = exc

            logger.exception(
                "GEMINI | Model failed | model=%s",
                model_name,
            )

    logger.error(
        "GEMINI | All models failed"
    )

    raise last_error
