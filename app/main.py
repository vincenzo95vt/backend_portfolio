from fastapi import FastAPI
from app.routes import education_router, project_router, experience_router, about_router, core_router
from dotenv import load_dotenv
from starlette.middleware.sessions import SessionMiddleware
import os

app = FastAPI()
load_dotenv()
secret_key = os.getenv('CLAVESECRETA')

app.add_middleware(SessionMiddleware, secret_key=secret_key)

app.include_router(education_router)
app.include_router(experience_router)
app.include_router(project_router)
app.include_router(about_router)
app.include_router(core_router)
