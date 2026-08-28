import logging


from app.database import (
    create_user,
    get_user,
)


logger = logging.getLogger(
    "AI_JOB_AGENT.USER_SERVICE"
)


def ensure_user(
    user_id,
):

    logger.info(
        "USER_SERVICE | Ensuring user exists | "
        "user_id=%s",
        user_id,
    )

    user = get_user(
        user_id
    )

    if user:

        logger.info(
            "USER_SERVICE | Existing user found | "
            "user_id=%s",
            user_id,
        )

        return user

    logger.info(
        "USER_SERVICE | Creating new user | "
        "user_id=%s",
        user_id,
    )

    create_user(
        user_id
    )

    user = get_user(
        user_id
    )

    if not user:

        logger.error(
            "USER_SERVICE | User creation failed | "
            "user_id=%s",
            user_id,
        )

        raise RuntimeError(
            "Unable to create user."
        )

    logger.info(
        "USER_SERVICE | User ready | "
        "user_id=%s",
        user_id,
    )

    return user