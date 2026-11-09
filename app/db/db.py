# db.py
import os
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

load_dotenv()

MONGO_URI = os.getenv("MONGOCLUSTER")
# Nombre de la BD configurable para poder probar (p. ej. con MCP Inspector)
# contra una BD separada sin tocar los datos reales.
DB_NAME = os.getenv("MONGO_DB_NAME") or "Portfolio_backend"
client = AsyncIOMotorClient(MONGO_URI)
db = client[DB_NAME]

class Collections:
    projects = db["Projects"]
    experience = db["Experience"]
    education = db["Education"]
    aboutMe = db["About_me"]
    users = db["Users"]

collections = Collections()
