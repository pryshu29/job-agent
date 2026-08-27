import logging

from pymongo import MongoClient

from config import MONGODB_URI


logger = logging.getLogger("AI_JOB_AGENT")


if not MONGODB_URI:
    raise RuntimeError("MONGODB_URI is missing")


logger.info("MONGODB | Creating MongoDB client")

client = MongoClient(
    MONGODB_URI,
    serverSelectionTimeoutMS=10000,
)

db = client["job_agent"]

users = db["users"]


def check_database_connection():
    logger.info("MONGODB | Sending ping")

    client.admin.command("ping")

    logger.info("MONGODB | Ping successful")

    return True


def get_user(user_id):
    logger.info(
        "MONGODB | Loading user | user_id=%s",
        user_id,
    )

    user = users.find_one(
        {"telegram_user_id": user_id}
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


def create_user(user_id):
    logger.info(
        "MONGODB | Creating user | user_id=%s",
        user_id,
    )

    users.update_one(
        {"telegram_user_id": user_id},
        {
            "$setOnInsert": {
                "telegram_user_id": user_id,
                "profile": {},
                "preferences": {},
                "agent_state": {
                    "workflow": "onboarding",
                    "current_question": None,
                },
            }
        },
        upsert=True,
    )

    logger.info(
        "MONGODB | User ready | user_id=%s",
        user_id,
    )


def update_profile(user_id, updates):
    logger.info(
        "MONGODB | Updating profile | user_id=%s | fields=%s",
        user_id,
        len(updates),
    )

    set_data = {}

    for update in updates:
        field = update.field
        value = update.value

        if not field:
            continue

        set_data[f"profile.{field}"] = value

    if not set_data:
        logger.info(
            "MONGODB | No profile changes | user_id=%s",
            user_id,
        )
        return

    users.update_one(
        {"telegram_user_id": user_id},
        {
            "$set": set_data,
        },
        upsert=True,
    )

    logger.info(
        "MONGODB | Profile updated | user_id=%s | fields=%s",
        user_id,
        len(set_data),
    )


def update_agent_state(
    user_id,
    workflow,
    current_question=None,
):
    logger.info(
        "MONGODB | Updating agent state | user_id=%s",
        user_id,
    )

    users.update_one(
        {"telegram_user_id": user_id},
        {
            "$set": {
                "agent_state.workflow": workflow,
                "agent_state.current_question": current_question,
            }
        },
        upsert=True,
    )

    logger.info(
        "MONGODB | Agent state updated | user_id=%s",
        user_id,
    )
