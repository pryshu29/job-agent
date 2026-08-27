import logging
from datetime import datetime, timezone

from pymongo import DESCENDING, MongoClient

from config import MONGODB_URI


logger = logging.getLogger("AI_JOB_AGENT")


# ============================================================
# MONGODB CONNECTION
# ============================================================

if not MONGODB_URI:
    raise RuntimeError("MONGODB_URI is missing")


logger.info("MONGODB | Creating MongoDB client")


client = MongoClient(
    MONGODB_URI,
    serverSelectionTimeoutMS=10000,
)


db = client["job_agent"]

users = db["users"]

conversations = db["conversations"]


# ============================================================
# DATABASE CONNECTION
# ============================================================

def check_database_connection():

    logger.info(
        "MONGODB | Sending ping"
    )

    client.admin.command("ping")

    logger.info(
        "MONGODB | Ping successful"
    )

    return True


# ============================================================
# INDEXES
# ============================================================

def create_indexes():

    logger.info(
        "MONGODB | Creating indexes"
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


# ============================================================
# USER
# ============================================================

def create_user(user_id):

    logger.info(
        "MONGODB | Creating user | user_id=%s",
        user_id,
    )

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


def get_user(user_id):

    logger.info(
        "MONGODB | Loading user | user_id=%s",
        user_id,
    )

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


# ============================================================
# PROFILE
# ============================================================

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


# ============================================================
# RESUME PROFILE
# ============================================================

def save_resume_profile(
    user_id,
    resume_profile,
    filename,
):

    logger.info(
        "MONGODB | Saving extracted resume profile | "
        "user_id=%s | filename=%s",
        user_id,
        filename,
    )

    profile_data = resume_profile.model_dump(
        exclude_none=True
    )

    profile_updates = {}

    for field, value in profile_data.items():

        if value is None:
            continue

        if value == "":
            continue

        if value == []:
            continue

        profile_updates[
            f"profile.{field}"
        ] = value

    update_data = {
        "resume.uploaded": True,
        "resume.filename": filename,
        "resume.updated_at": datetime.now(
            timezone.utc
        ),
    }

    update_data.update(
        profile_updates
    )

    users.update_one(
        {
            "telegram_user_id": user_id
        },
        {
            "$set": update_data
        },
        upsert=True,
    )

    logger.info(
        "MONGODB | Resume profile saved | "
        "user_id=%s | profile_fields=%s",
        user_id,
        len(profile_updates),
    )


# ============================================================
# AGENT STATE
# ============================================================

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


# ============================================================
# CONVERSATION MEMORY
# ============================================================

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
