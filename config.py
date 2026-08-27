import os


TELEGRAM_BOT_TOKEN = os.environ.get(
    "TELEGRAM_BOT_TOKEN"
)

GEMINI_API_KEY = os.environ.get(
    "GEMINI_API_KEY"
)

MONGODB_URI = os.environ.get(
    "MONGODB_URI"
)

raw_user_id = os.environ.get(
    "AUTHORIZED_USER_ID",
    "0",
)

AUTHORIZED_USER_ID = (
    int(raw_user_id)
    if raw_user_id.isdigit()
    else 0
)
