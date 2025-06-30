from fastapi import FastAPI
from starlette.middleware.sessions import SessionMiddleware
from app.middlewares.session import auth_middleware
from dotenv import load_dotenv
import os

load_dotenv()
secret_key = os.getenv('CLAVESECRETA')


app = FastAPI()

app.add_middleware(SessionMiddleware, secretkey= secret_key)
