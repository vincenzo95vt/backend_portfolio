from fastapi import FastAPI
from app.routes import education_router, project_router, experience_router, about_router, core_router
from app.routes.apis import router as apis_router
from dotenv import load_dotenv
from starlette.middleware.sessions import SessionMiddleware
import os
from fastapi.middleware.cors import CORSMiddleware

load_dotenv()
secret_key = os.getenv('CLAVESECRETA')

app = FastAPI()

origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:5174",
    "https://vinnievasta.com",
    "https://www.vinnievasta.com",
    "https://backend-portfolio-iqkc.onrender.com",
]

# SessionMiddleware debe añadirse antes que CORSMiddleware
# porque Starlette ejecuta los middlewares en orden inverso al que se añaden
app.add_middleware(SessionMiddleware, secret_key=secret_key)
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(apis_router)
app.include_router(education_router)
app.include_router(experience_router)
app.include_router(project_router)
app.include_router(about_router)
app.include_router(core_router)
