from fastapi import FastAPI
from starlette.middleware.sessions import SessionMiddleware
from app.middlewares.session import auth_middleware
from dotenv import load_dotenv
import os

app = FastAPI()

