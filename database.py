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


def save_preferences(user_id, data):
    logger.info(
        "MONGODB | Updating user preferences | user_id=%s",
        user_id,
    )

    users.update_one(
        {"telegram_user_id": user_id},
        {
            "$set": {
                "telegram_user_id": user_id,
                "job_preferences": data,
                "onboarding_completed": True,
            }
        },
        upsert=True,
    )

    logger.info(
        "MONGODB | User preferences updated | user_id=%s",
        user_id,
    )
