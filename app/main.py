from fastapi import FastAPI
from app.routes import education_router, project_router, experience_router, about_router, core_router
from app.routes.apis import router as apis_router
from dotenv import load_dotenv
from starlette.middleware.sessions import SessionMiddleware
import os
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

origins = [
    "http://localhost:3000",               # React local
    "http://127.0.0.1:3000",               # Alternativa local
    "http://localhost:5173",              # Si usas Vite
    "https://vinnievasta.com",            # Tu dominio real (ajústalo)
    "https://www.vinnievasta.com",        # Con www por si acaso
    "https://backend-portfolio-iqkc.onrender.com",  # El subdominio de Render
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,  # Usa ["*"] si quieres permitir todos temporalmente
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

load_dotenv()
secret_key = os.getenv('CLAVESECRETA')

app.add_middleware(SessionMiddleware, secret_key=secret_key)
app.include_router(apis_router)
app.include_router(education_router)
app.include_router(experience_router)
app.include_router(project_router)
app.include_router(about_router)
app.include_router(core_router)
