import logging


LOGGER_NAME = "AI_JOB_AGENT"


LOG_FORMAT = (
    "%(asctime)s | "
    "%(levelname)s | "
    "%(name)s | "
    "%(message)s"
)


def configure_logging():

    logging.basicConfig(
        level=logging.INFO,
        format=LOG_FORMAT,
        force=True,
    )

    # ========================================================
    # EXTERNAL LIBRARY LOGGING
    # ========================================================
    #
    # HTTP libraries can log request URLs.
    # Telegram API URLs may contain the bot token.
    #
    # Therefore we intentionally suppress their INFO logs.
    #

    logging.getLogger(
        "httpx"
    ).setLevel(logging.WARNING)

    logging.getLogger(
        "httpcore"
    ).setLevel(logging.WARNING)

    # Flask access logs are not required at INFO level.
    logging.getLogger(
        "werkzeug"
    ).setLevel(logging.WARNING)

    # ========================================================
    # APPLICATION LOGGER
    # ========================================================

    logger = logging.getLogger(
        LOGGER_NAME
    )

    logger.info(
        "LOGGING | Logging configured"
    )

    return logger


def get_logger(
    name=None,
):

    if name:

        return logging.getLogger(
            name
        )

    return logging.getLogger(
        LOGGER_NAME
    )