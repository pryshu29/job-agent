from pymongo import MongoClient
from config import MONGODB_URI

client = MongoClient(MONGODB_URI)
db = client["job_agent"]

users = db["users"]

def check_database_connection():
    client.admin.command("ping")
    return True

def save_preferences(user_id, data):
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
