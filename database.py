from pymongo import MongoClient

from config import MONGODB_URI


client = MongoClient(MONGODB_URI)

database = client["job_agent"]

users_collection = database["users"]


def check_database_connection():
    client.admin.command("ping")
    return True
