from fastapi import FastAPI
from app.routes import education_router, project_router, experience_router, about_router, core_router

app = FastAPI()

app.include_router(education_router)
app.include_router(experience_router)
app.include_router(project_router)
app.include_router(about_router)
app.include_router(core_router)

