import logging

from pymongo import MongoClient

from app.config import MONGODB_URI


logger = logging.getLogger(
    "AI_JOB_AGENT.MONGODB"
)


if not MONGODB_URI:
    raise RuntimeError(
        "MONGODB_URI is missing"
    )


client = MongoClient(
    MONGODB_URI,
    serverSelectionTimeoutMS=10000,
)


db = client["job_agent"]


def get_database():
    return db


def get_users_collection():
    return db["users"]


def get_conversations_collection():
    return db["conversations"]


def check_database_connection():

    logger.info(
        "MONGODB | Sending ping"
    )

    client.admin.command(
        "ping"
    )

    logger.info(
        "MONGODB | Ping successful"
    )

    return True


def create_indexes():

    logger.info(
        "MONGODB | Creating indexes"
    )

    users = get_users_collection()

    conversations = (
        get_conversations_collection()
    )

    users.create_index(
        "telegram_user_id",
        unique=True,
    )

    conversations.create_index(
        [
            (
                "telegram_user_id",
                1,
            ),
            (
                "created_at",
                -1,
            ),
        ]
    )

    logger.info(
        "MONGODB | Index creation completed"
    )