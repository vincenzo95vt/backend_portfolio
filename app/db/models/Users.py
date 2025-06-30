import bcrypt
from db import collections
from getpass import getpass
import asyncio

async def create_user():
    username = input("Introduce el nombre de usuario: ")
    password = getpass("Introduce la contraseña: ")
    hashed_password = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

    await collections.users.insert_one({
        "username": username,
        "password": hashed_password
    })
    print("✅ Usuario creado correctamente")

async def get_user_by_username(username: str):
    return await collections.users.find_one({"username": username})

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(plain_password.encode(), hashed_password.encode())

if __name__ == "__main__":
    asyncio.run(create_user())
