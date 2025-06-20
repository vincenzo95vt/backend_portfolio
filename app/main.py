from fastapi import FastAPI
from fastapi.requests import Request 
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from fastapi import Form
from fastapi.responses import RedirectResponse
from fastapi.responses import JSONResponse
import motor.motor_asyncio
from app.db import collections
from app.db import db
from dotenv import load_dotenv
import os
load_dotenv()
MONGO_URI = os.getenv('MONGOCLUSTER')

app = FastAPI()

client = motor.motor_asyncio.AsyncIOMotorClient(MONGO_URI)



templates = Jinja2Templates(directory='app/templates')
# ACCEDEMOS AL PANEL DE CONTROL
@app.get('/', response_class=HTMLResponse)
async def dashboard(resquest: Request):
    projects = await collections.projects.find({}).to_list(length=None)
    experience = await collections.experience.find({}).to_list(length=None)
    education = await collections.education.find({}).to_list(length=None)
    about_me = await collections.aboutMe.find_one({})
    data = {
        'projects': projects,
        'experience': experience,
        'education': education,
        'about_me': about_me
    }
    return templates.TemplateResponse("dashboard.html", {
        "request": resquest,
        'data': data
    })
# COMENZAMOS A CREAR LAS APIS PARA ACCEDER A ELLAS
@app.get('/api/allData')
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

#API PARA PROYECTOS

@app.get('/api/projects')
async def raw_data():
    cursor = collections.projects.find({})
    results = []

    async for doc in cursor:
        doc['_id'] = str(doc['_id'])
        results.append(doc)
    return results
#API PARA EDUCACION

@app.get('/api/education')
async def raw_data():
    cursor = collections.education.find({})
    results = []

    async for doc in cursor:
        doc['_id'] = str(doc['_id'])
        results.append(doc)
    return results

#API PARA SOBRE MI

@app.get('/api/about_me')
async def raw_data():
    cursor = collections.aboutMe.find({})
    results = []

    async for doc in cursor:
        doc['_id'] = str(doc['_id'])
        results.append(doc)
    return results

#API PARA EXPERIENCIA
@app.get('/api/experience')
async def raw_data():
    cursor = collections.experience.find({})
    results = []

    async for doc in cursor:
        doc['_id'] = str(doc['_id'])
        results.append(doc)
    return results
    
    
