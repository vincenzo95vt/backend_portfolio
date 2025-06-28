from fastapi import FastAPI
from starlette.middleware.sessions import SessionMiddleware
from app.middlewares.session import auth_middleware
from dotenv import load_dotenv
import os

load_dotenv()

app = FastAPI()

#SEGUIR AÑADIENDO MIDDLEWARE MIRAR EN LA CONVERSACION DE CHATGPT  'BACKEND SENCILLO CON FASTAPI'
