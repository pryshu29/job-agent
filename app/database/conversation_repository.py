import logging
from datetime import datetime, timezone

from pymongo import DESCENDING

from app.database.connection import (
    get_conversations_collection,
)


logger = logging.getLogger(
    "AI_JOB_AGENT.MONGODB.CONVERSATIONS"
)


def save_message(
    user_id,
    role,
    message,
):

    logger.info(
        "MONGODB | Saving conversation message | "
        "user_id=%s | role=%s",
        user_id,
        role,
    )

    conversations = (
        get_conversations_collection()
    )

    conversations.insert_one(
        {
            "telegram_user_id": user_id,

            "role": role,

            "message": message,

            "created_at": datetime.now(
                timezone.utc
            ),
        }
    )

    logger.info(
        "MONGODB | Conversation message saved | "
        "user_id=%s | role=%s",
        user_id,
        role,
    )


def get_recent_messages(
    user_id,
    limit=20,
):

    logger.info(
        "MONGODB | Loading recent conversation | "
        "user_id=%s | limit=%s",
        user_id,
        limit,
    )

    conversations = (
        get_conversations_collection()
    )

    messages = list(
        conversations.find(
            {
                "telegram_user_id": user_id
            }
        )
        .sort(
            "created_at",
            DESCENDING,
        )
        .limit(limit)
    )

    messages.reverse()

    logger.info(
        "MONGODB | Recent conversation loaded | "
        "user_id=%s | count=%s",
        user_id,
        len(messages),
    )

    return messages