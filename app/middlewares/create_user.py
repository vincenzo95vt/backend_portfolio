import bcrypt
from ..db.db import collections 
from getpass import getpass
import asyncio

async def create_user():
    username = input("Introduce el nombre de usuario: ")
    password = getpass("Introduce la contraseña: ")

    # Genera hash seguro
    hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

    await collections.users.insert_one({
        "username": username,
        "password": hashed_password
    })

    print("✅ Usuario creado correctamente")

if __name__ == '__main__':
    asyncio.run(create_user())
