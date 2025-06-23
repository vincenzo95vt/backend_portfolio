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
@router.get('/api/allData')
async def all_data():
    result = {}

    collection_list = ['Projects', 'Experience', 'Education', 'About_me']

    for name in collection_list:
        col = db[name]
        docs = await col.find().to_list(length=None)
        for doc in docs:
            doc['_id'] = str(doc['_id'])
        result[name] = docs

    return JSONResponse(content=result)

__all__ = ['router']