import logging

from google import genai
from google.genai import types

from app.config import GEMINI_API_KEY


logger = logging.getLogger(
    "AI_JOB_AGENT.GEMINI"
)


if not GEMINI_API_KEY:

    raise RuntimeError(
        "GEMINI_API_KEY is missing"
    )


client = genai.Client(
    api_key=GEMINI_API_KEY
)


PRIMARY_MODEL = "gemini-3.6-flash"

FALLBACK_MODEL = "gemini-3.5-flash-lite"


def generate_content(
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