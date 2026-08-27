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
        default_factory=list
    )

    response: str = Field()

    next_question: Optional[str] = Field(
        default=None
    )

    needs_clarification: bool = Field(
        default=False
    )


# ============================================================
# RESUME PROFILE
# ============================================================

class ResumeProfile(BaseModel):

    name: Optional[str] = None

    email: Optional[str] = None

    phone: Optional[str] = None

    location: Optional[str] = None

    headline: Optional[str] = None

    professional_summary: Optional[str] = None

    skills: list[str] = Field(
        default_factory=list
    )

    experience: list[str] = Field(
        default_factory=list
    )

    education: list[str] = Field(
        default_factory=list
    )

    projects: list[str] = Field(
        default_factory=list
    )

    certifications: list[str] = Field(
        default_factory=list
    )

    achievements: list[str] = Field(
        default_factory=list
    )

    links: list[str] = Field(
        default_factory=list
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

1. Understand the complete user message.

The user may provide multiple pieces of information in one
message.

Extract all useful career information that the user explicitly
provides.

2. Use conversation context.

The current message may depend on previous messages.

3. Do not assume that a user's response answers the previous
question.

If the user changes the subject to another career-related
request, handle the new request.

4. Handle corrections.

If the user corrects information, use the corrected value.

5. Never invent candidate information.

Only extract information explicitly provided by the user or
supported by the supplied resume.

6. Resume-related requests use the "resume" intent.

7. Job-search requests use "job_search".

8. Specific job opening or job URL requests use "job_analysis".

9. Application requests use "application".

10. Interview-related requests use "interview".

11. Hackathons, internships, hiring programs and similar
opportunities use "opportunity".

12. Career improvement and certification requests use
"career_recommendation".

13. Other career questions use "general_career".

14. Completely unrelated requests use "out_of_scope".

============================================================
SECURITY
============================================================

Never store the following as profile information:

- Passwords
- OTPs
- API keys
- Access tokens
- Authentication cookies
- Session tokens
- Security answers

Credentials used during an application workflow must be handled
temporarily by the application layer.

============================================================
SYSTEM BOUNDARY
============================================================

You are the reasoning layer.

Python controls:

- Database operations
- Web searches
- Resume processing
- PDF generation
- Job applications
- Authentication
- External services

Never claim that an external action occurred unless the
application actually performed that action.
"""


# ============================================================
# RESUME SYSTEM INSTRUCTION
# ============================================================

RESUME_SYSTEM_INSTRUCTION = """
You are an expert resume information extraction system.

Extract structured candidate information from the supplied
resume text.

IMPORTANT RULES:

1. Only extract information actually present in the resume.

2. Never invent:
   - Skills
   - Experience
   - Education
   - Certifications
   - Projects
   - Achievements
   - Job titles
   - Employers
   - Dates

3. Preserve the meaning of the resume.

4. Do not improve or rewrite the resume at this stage.

5. If a field is not present, return null or an empty list.

6. Skills should contain individual recognizable skills.

7. Experience should preserve the important information from
   each experience entry.

8. Education should preserve degree, institution and relevant
   dates when available.

9. Projects should preserve project names and meaningful
   technologies/details.

10. Certifications should contain certifications explicitly
    listed.

11. Achievements should contain achievements explicitly listed.

12. Links should contain publicly provided links such as:
    - LinkedIn
    - GitHub
    - Portfolio
    - Personal website

Return only the structured ResumeProfile object.
"""


# ============================================================
# RECENT CONVERSATION FORMATTER
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
# GENERIC GEMINI REQUEST
# ============================================================

def generate_with_fallback(
    contents,
    system_instruction,
    response_schema,
):

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
                contents=contents,
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    response_mime_type="application/json",
                    response_schema=response_schema,
                ),
            )

            logger.info(
                "GEMINI | Response received | model=%s",
                model_name,
            )

            if response.parsed:

                return response.parsed

            logger.warning(
                "GEMINI | Parsed response unavailable | "
                "model=%s",
                model_name,
            )

            return response_schema.model_validate_json(
                response.text
            )

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
        "Gemini request failed."
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
