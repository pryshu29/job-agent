import logging

from app.database import (
    get_recent_messages,
    save_message,
)


logger = logging.getLogger(
    "AI_JOB_AGENT.CONVERSATION_SERVICE"
)


def save_user_message(
    user_id,
    message,
):

    logger.info(
        "CONVERSATION_SERVICE | Saving user message | "
        "user_id=%s",
        user_id,
    )

    save_message(
        user_id=user_id,
        role="user",
        message=message,
    )

    logger.info(
        "CONVERSATION_SERVICE | User message saved | "
        "user_id=%s",
        user_id,
    )


def save_assistant_message(
    user_id,
    message,
):

    logger.info(
        "CONVERSATION_SERVICE | Saving assistant message | "
        "user_id=%s",
        user_id,
    )

    save_message(
        user_id=user_id,
        role="assistant",
        message=message,
    )

    logger.info(
        "CONVERSATION_SERVICE | Assistant message saved | "
        "user_id=%s",
        user_id,
    )


def get_recent_conversation(
    user_id,
    limit=20,
):

    logger.info(
        "CONVERSATION_SERVICE | Loading conversation | "
        "user_id=%s | limit=%s",
        user_id,
        limit,
    )

    messages = get_recent_messages(
        user_id=user_id,
        limit=limit,
    )

    logger.info(
        "CONVERSATION_SERVICE | Conversation loaded | "
        "user_id=%s | count=%s",
        user_id,
        len(messages),
    )

    return messages