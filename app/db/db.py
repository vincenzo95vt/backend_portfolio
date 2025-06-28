# db.py
import os
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

load_dotenv()

MONGO_URI = os.getenv("MONGOCLUSTER")
client = AsyncIOMotorClient(MONGO_URI)
db = client["Portfolio_backend"]

class Collections:
    projects = db["Projects"]
    experience = db["Experience"]
    education = db["Education"]
    aboutMe = db["About_me"]
    users = db["Users"]

collections = Collections()
