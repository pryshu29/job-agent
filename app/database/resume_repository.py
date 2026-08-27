import logging
from datetime import datetime, timezone

from app.database.connection import (
    get_users_collection,
)


logger = logging.getLogger(
    "AI_JOB_AGENT.MONGODB.RESUME"
)


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

    users = get_users_collection()

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