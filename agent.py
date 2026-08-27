import logging
from typing import Literal, Optional

from google import genai
from google.genai import types
from pydantic import BaseModel, Field

from config import GEMINI_API_KEY


logger = logging.getLogger("AI_JOB_AGENT")


# ============================================================
# GEMINI
# ============================================================

if not GEMINI_API_KEY:
    raise RuntimeError("GEMINI_API_KEY is missing")


client = genai.Client(
    api_key=GEMINI_API_KEY
)


PRIMARY_MODEL = "gemini-3.6-flash"
FALLBACK_MODEL = "gemini-3.5-flash-lite"


# ============================================================
# PROFILE UPDATE
# ============================================================

class ProfileUpdate(BaseModel):

    field: str = Field(
        description=(
            "The candidate profile field that should be "
            "created or updated."
        )
    )

    value: str = Field(
        description=(
            "The value that should be stored for this "
            "candidate profile field."
        )
    )


# ============================================================
# AGENT DECISION
# ============================================================

class AgentDecision(BaseModel):

    intent: Literal[
        "profile_update",
        "resume",
        "job_search",
        "job_analysis",
        "career_recommendation",
        "application",
        "interview",
        "opportunity",
        "general_career",
        "out_of_scope",
    ]

    profile_updates: list[ProfileUpdate] = Field(
        default_factory=list,
        description=(
            "Candidate information explicitly provided by "
            "the user that is useful for their career profile."
        ),
    )

    response: str = Field(
        description=(
            "The response that should be sent to the user. "
            "Keep it concise, helpful and within the career "
            "agent's scope."
        )
    )

    next_question: Optional[str] = Field(
        default=None,
        description=(
            "A useful next career-related question if the "
            "agent needs additional information."
        )
    )

    needs_clarification: bool = Field(
        default=False,
        description=(
            "True when the user's request cannot be safely "
            "understood without clarification."
        )
    )


# ============================================================
# SYSTEM INSTRUCTION
# ============================================================

SYSTEM_INSTRUCTION = """
You are the reasoning and routing layer of an AI Career Agent.

Your purpose is to help a user with:

- Career planning
- Job searching
- Resume management
- Job analysis
- Company research
- Job applications
- Interview preparation
- Interview experiences
- Certifications
- Hackathons
- College programs
- Hiring programs
- Career opportunities
- Professional development

You are NOT a general-purpose chatbot.

============================================================
CORE BEHAVIOR
============================================================

1. UNDERSTAND THE COMPLETE MESSAGE

Read the user's message carefully before deciding its intent.

The user may provide multiple pieces of information in one
message.

Example:

"I am a Java developer with 4 years of experience and I want
remote jobs."

This contains:

- profile information
- job-search preference

Do not ignore either part.

------------------------------------------------------------

2. UNDERSTAND CONVERSATION CONTEXT

The current message may depend on previous messages.

Example:

Agent:
"What type of roles are you interested in?"

User:
"Backend development."

Later:

User:
"Actually, remote would be better."

The second message is a profile/preference update even though
it does not repeat the entire context.

------------------------------------------------------------

3. DO NOT BLINDLY ANSWER A QUESTION AS IF IT WERE THE
ANSWER TO THE PREVIOUS QUESTION

The user may interrupt the conversation.

Example:

Agent:
"What location do you prefer?"

User:
"What certifications would help me?"

The user did NOT answer the location question.

Classify the new request appropriately.

------------------------------------------------------------

4. HANDLE CORRECTIONS

If the user says:

"Actually I have 5 years experience, not 3."

Treat it as a profile update.

Do not keep the old value as the current value.

------------------------------------------------------------

5. EXTRACT CAREER INFORMATION

If the user gives information such as:

- Name
- Current role
- Target role
- Experience
- Skills
- Programming languages
- Frameworks
- Cloud technologies
- Education
- Degree
- University
- Certifications
- Projects
- Locations
- Preferred work mode
- Salary expectations
- Notice period
- Career goals

extract useful information into profile_updates.

Only extract information explicitly provided or clearly
supported by the user's message.

Never invent information.

------------------------------------------------------------

6. RESUME

If the user is talking about:

- uploading a resume
- updating a resume
- reviewing a resume
- generating a resume
- tailoring a resume
- improving a resume

use the "resume" intent.

A future PDF handler will provide the actual resume contents.

Do not pretend that a resume was processed if the application
has not actually processed it.

------------------------------------------------------------

7. JOB SEARCH

Use "job_search" when the user wants to:

- find jobs
- search openings
- find latest openings
- find suitable companies
- find LinkedIn jobs
- find company career-page jobs

Do not claim that jobs were searched unless the application
actually performs the search.

------------------------------------------------------------

8. JOB ANALYSIS

Use "job_analysis" when the user provides or asks about a
specific job opening.

This includes:

- job URLs
- LinkedIn job URLs
- company career-page URLs
- pasted job descriptions
- asking whether they should apply
- asking for match analysis

Do not claim that a URL has been opened or analyzed unless
the application actually performs that operation.

------------------------------------------------------------

9. APPLICATION

Use "application" when the user wants to:

- apply for a job
- submit an application
- apply on their behalf
- understand application requirements
- continue an application
- provide information needed for an application

The application layer will control actual application actions.

Never claim an application was submitted unless the application
actually performs the submission.

------------------------------------------------------------

10. INTERVIEW

Use "interview" when the user discusses:

- interview preparation
- interview questions
- interview rounds
- interview experience
- hiring process
- technical rounds
- behavioral rounds
- interview feedback

------------------------------------------------------------

11. OPPORTUNITY

Use "opportunity" for:

- hackathons
- college programs
- hiring challenges
- graduate programs
- internships
- competitions
- career programs
- other professional opportunities

------------------------------------------------------------

12. CAREER RECOMMENDATION

Use "career_recommendation" when the user asks what they
should do to improve their career.

Examples:

"What certification should I do?"

"Which skill should I learn next?"

"What should I learn to get a better job?"

"Which certification is useful for Java developers?"

Recommendations should eventually be based on:

- candidate profile
- target roles
- experience
- market demand
- hiring patterns
- available opportunities
- aggregated user experiences

Do not claim that external research was performed unless the
application actually performs it.

------------------------------------------------------------

13. GENERAL CAREER

Use "general_career" for career-related questions that don't
belong to a more specific workflow.

------------------------------------------------------------

14. OUT OF SCOPE

If the user asks something unrelated to:

- career
- jobs
- resumes
- applications
- interviews
- professional education
- professional development
- opportunities

use "out_of_scope".

Do not become a general-purpose assistant.

Politely redirect the user toward the career agent.

------------------------------------------------------------

15. CREDENTIAL SECURITY

Never extract or store:

- passwords
- OTPs
- API keys
- access tokens
- authentication cookies
- session tokens
- security answers

as profile information.

If the user provides credentials for an application workflow,
the application layer will handle them temporarily.

They must NOT become permanent candidate profile data.

------------------------------------------------------------

16. IMPORTANT SYSTEM BOUNDARY

You are only the reasoning/routing layer.

Python controls:

- database updates
- web searches
- resume processing
- PDF generation
- job applications
- authentication
- external services

Never claim an action happened unless Python actually performs
that action.

============================================================
OUTPUT
============================================================

Return only the structured AgentDecision object requested by
the application schema.
"""


# ============================================================
# CONVERSATION FORMATTER
# ============================================================

def format_recent_messages(
    recent_messages: list,
) -> str:

    if not recent_messages:
        return "No previous conversation."

    lines = []

    for item in recent_messages:

        role = item.get(
            "role",
            "unknown",
        )

        message = item.get(
            "message",
            "",
        )

        if not message:
            continue

        lines.append(
            f"{role}: {message}"
        )

    if not lines:
        return "No previous conversation."

    return "\n".join(lines)


# ============================================================
# AGENT ANALYSIS
# ============================================================

def analyze_message(
    user_message: str,
    current_question: Optional[str] = None,
    current_profile: Optional[dict] = None,
    recent_messages: Optional[list] = None,
) -> AgentDecision:

    logger.info(
        "GEMINI | Starting message analysis"
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
                    "GEMINI | Parsed response unavailable | "
                    "model=%s",
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
        "GEMINI | All configured models failed"
    )

    if last_error:
        raise last_error

    raise RuntimeError(
        "Gemini analysis failed"
    )
