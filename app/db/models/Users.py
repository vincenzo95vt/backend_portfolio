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

asyncio.run(create_user())
