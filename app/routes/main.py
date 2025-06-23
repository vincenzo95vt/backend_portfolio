from fastapi import APIRouter, Request, Form
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from fastapi.responses import RedirectResponse
from fastapi.responses import JSONResponse
from bson import ObjectId
import motor.motor_asyncio
from typing import Optional
from app.db.db import collections
from dotenv import load_dotenv
import os

load_dotenv()
MONGO_URI = os.getenv('MONGOCLUSTER')

router = APIRouter()

client = motor.motor_asyncio.AsyncIOMotorClient(MONGO_URI)



templates = Jinja2Templates(directory='app/templates')
#ACCEDEMOS AL INICIO O BIENVENIDA
@router.get('/', response_class=HTMLResponse)
def home(request: Request):
    return templates.TemplateResponse("welcome.html", {"request": request})



# ACCEDEMOS AL PANEL DE CONTROL
@router.get('/dashboard', response_class=HTMLResponse)
async def dashboard(resquest: Request):
    projects = await collections.projects.find({}).to_list(length=None)
    experience = await collections.experience.find({}).to_list(length=None)
    education = await collections.education.find({}).to_list(length=None)
    about_me = await collections.aboutMe.find_one({})
    data = {
        'projects': projects,
        'experience': experience,
        'education': education,
        'about_me': about_me,
    }
    return templates.TemplateResponse("dashboard.html", {
        "request": resquest,
        'data': data
    })
# COMENZAMOS A CREAR LAS APIS PARA ACCEDER A ELLAS


@router.get('/api/v1', response_class=HTMLResponse)
async def api_index(request: Request):
    return templates.TemplateResponse('api_index.html', {
        'request': request
    })

__all__ = ['router']