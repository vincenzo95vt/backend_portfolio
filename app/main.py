from contextlib import asynccontextmanager

from fastapi import FastAPI
from app.routes import education_router, project_router, experience_router, about_router, core_router
from app.routes.apis import router as apis_router
from dotenv import load_dotenv
from starlette.middleware.sessions import SessionMiddleware
import os
from fastapi.middleware.cors import CORSMiddleware

load_dotenv()
secret_key = os.getenv('CLAVESECRETA')

from app.mcp import build_mcp_app  # noqa: E402  (después de load_dotenv)

# Servidor MCP (None si faltan las variables OAuth: en ese caso no se monta).
mcp_app = build_mcp_app()


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("🔥 Servidor arrancado")
    if mcp_app is None:
        yield
    else:
        # Starlette no ejecuta la lifespan de las apps montadas: la encadenamos.
        async with mcp_app.lifespan(app):
            print("🤖 Servidor MCP disponible en /mcp")
            yield


app = FastAPI(lifespan=lifespan)

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

# Se monta en "/" y al final: FastAPI resuelve antes todas sus rutas y lo que no
# coincide pasa a la app MCP. Así quedan /mcp y, en la raíz, los endpoints OAuth
# que exige claude.ai (/.well-known/*, /authorize, /token, /register, /auth/callback).
if mcp_app is not None:
    app.mount("/", mcp_app)
