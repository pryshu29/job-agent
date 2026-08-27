import logging
from datetime import datetime, timezone

from app.database.connection import (
    get_users_collection,
)


logger = logging.getLogger(
    "AI_JOB_AGENT.MONGODB.USERS"
)


def create_user(
    user_id,
):

    logger.info(
        "MONGODB | Creating user | user_id=%s",
        user_id,
    )

    users = get_users_collection()

    users.update_one(
        {
            "telegram_user_id": user_id
        },
        {
            "$setOnInsert": {
                "telegram_user_id": user_id,

                "profile": {},

                "preferences": {},

                "resume": {
                    "uploaded": False,
                    "filename": None,
                    "updated_at": None,
                },

                "agent_state": {
                    "workflow": "onboarding",
                    "current_question": None,
                    "current_task": None,
                    "active_job_id": None,
                },

                "created_at": datetime.now(
                    timezone.utc
                ),
            }
        },
        upsert=True,
    )

    logger.info(
        "MONGODB | User ready | user_id=%s",
        user_id,
    )


def get_user(
    user_id,
):

    logger.info(
        "MONGODB | Loading user | user_id=%s",
        user_id,
    )

    users = get_users_collection()

    user = users.find_one(
        {
            "telegram_user_id": user_id
        }
    )

    if user:

        logger.info(
            "MONGODB | User found | user_id=%s",
            user_id,
        )

    else:

        logger.info(
            "MONGODB | User not found | user_id=%s",
            user_id,
        )

    return user


def update_profile(
    user_id,
    updates,
):

    logger.info(
        "MONGODB | Updating profile | "
        "user_id=%s | fields=%s",
        user_id,
        len(updates),
    )

    set_data = {}

    for update in updates:

        field = update.field
        value = update.value

        if not field:
            continue

        set_data[
            f"profile.{field}"
        ] = value

    if not set_data:

        logger.info(
            "MONGODB | No profile changes | "
            "user_id=%s",
            user_id,
        )

        return

    users = get_users_collection()

    users.update_one(
        {
            "telegram_user_id": user_id
        },
        {
            "$set": set_data
        },
        upsert=True,
    )

    logger.info(
        "MONGODB | Profile updated | "
        "user_id=%s | fields=%s",
        user_id,
        len(set_data),
    )


def update_agent_state(
    user_id,
    workflow,
    current_question=None,
    current_task=None,
    active_job_id=None,
):

    logger.info(
        "MONGODB | Updating agent state | "
        "user_id=%s",
        user_id,
    )

    users = get_users_collection()

    users.update_one(
        {
            "telegram_user_id": user_id
        },
        {
            "$set": {
                "agent_state.workflow": workflow,

                "agent_state.current_question": (
                    current_question
                ),

                "agent_state.current_task": (
                    current_task
                ),

                "agent_state.active_job_id": (
                    active_job_id
                ),
            }
        },
        upsert=True,
    )

    logger.info(
        "MONGODB | Agent state updated | "
        "user_id=%s",
        user_id,
    )