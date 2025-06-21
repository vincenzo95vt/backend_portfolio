from fastapi import FastAPI
from fastapi import Request 
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
#ACCEDEMOS AL INICIO O BIENVENIDA
@app.get('/', response_class=HTMLResponse)
def home(request: Request):
    return templates.TemplateResponse("welcome.html", {"request": request})



# ACCEDEMOS AL PANEL DE CONTROL
@app.get('/dashboard', response_class=HTMLResponse)
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
    
#API PARA HACER UPDATE DE SOBRE MI
@app.get('/aboutMe/edit', response_class= HTMLResponse)
async def edit_aboutMe(request: Request):
    about = await collections.aboutMe.find_one({})
    return templates.TemplateResponse('about_edit.html',{
        'request': request,
        'about': about
    })
@app.post('/update/aboutMe')
async def updateAboutMe(
    nombre: str = Form(...),
    titulo: str = Form(...),
    descripcion: str = Form(...),
    softSkills: str = Form(...),
    hardSkills: str = Form(...),
    idiomas: str = Form(...)
):
    data = {
        'nombre': nombre,
        'titulo': titulo,
        'descripcion': descripcion,
        'softSkills': [s.strip() for s in softSkills.split(',')],
        'hardSkills': [h.strip() for h in hardSkills.split(',')],
        'idiomas': [i.strip() for i in idiomas.split(',')]
    }

    await collections.aboutMe.update_one({}, {'$set': data}, upsert = True)
    return RedirectResponse(url= '/dashboard', status_code=303)

@app.get('/edit/experience', response_class= HTMLResponse)
async def editExperience(request: Request):
    experience = await collections.experience.find().to_list(length=None)
    
    return templates.TemplateResponse('exp_edit.html',{
        'request': request,
        'about': experience
    })

@app.post('/add/experience')
async def addExperience(
    empresa: str = Form(...),
    periodo: str=  Form(...),
    puesto: str = Form(...),
    descripcion: str =  Form(...),
    tecnologias: str =  Form(...)
):
    data = {
        'empresa': empresa,
        'periodo' : periodo,
        'puesto': puesto,
        'descripcion': descripcion,
        'tecnologias': [t.strip() for t in tecnologias.split(',')]
    }

    await collections.experience.insert_one(data)
    return RedirectResponse(url='/dashboard', status_code=303)
    