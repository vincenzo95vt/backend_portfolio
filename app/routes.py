from fastapi import APIRouter, Request, Form
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from fastapi.responses import RedirectResponse
from fastapi.responses import JSONResponse
from bson import ObjectId
import motor.motor_asyncio
from typing import Optional
from app.db import collections
from app.db import db
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

#API PARA PROYECTOS

@router.get('/api/projects')
async def raw_data():
    cursor = collections.projects.find({})
    results = []

    async for doc in cursor:
        doc['_id'] = str(doc['_id'])
        results.append(doc)
    return results
#API PARA EDUCACION

@router.get('/api/education')
async def raw_data():
    cursor = collections.education.find({})
    results = []

    async for doc in cursor:
        doc['_id'] = str(doc['_id'])
        results.append(doc)
    return results

#API PARA SOBRE MI

@router.get('/api/about_me')
async def raw_data():
    cursor = collections.aboutMe.find({})
    results = []

    async for doc in cursor:
        doc['_id'] = str(doc['_id'])
        results.append(doc)
    return results

#API PARA EXPERIENCIA
@router.get('/api/experience')
async def raw_data():
    cursor = collections.experience.find({})
    results = []

    async for doc in cursor:
        doc['_id'] = str(doc['_id'])
        results.append(doc)
    return results
    
#API PARA HACER UPDATE DE SOBRE MI
@router.get('/aboutMe/edit', response_class= HTMLResponse)
async def edit_aboutMe(request: Request):
    about = await collections.aboutMe.find_one({})
    return templates.TemplateResponse('about_edit.html',{
        'request': request,
        'about': about
    })
@router.post('/update/aboutMe')
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

@router.get('/edit/experiences', response_class= HTMLResponse)
async def showExperiences(request: Request):
    success = request.query_params.get('success')
    experiences = await collections.experience.find().to_list(length=None)
    return templates.TemplateResponse('experiences.html',{
        'request': request,
        'experiences': experiences,
        'success': success
    })

@router.get('/edit/experience/{id}', response_class=HTMLResponse)
async def edit_experience(id: str, request:Request):
    experience = await collections.experience.find_one({'_id': ObjectId(id)})
    return templates.TemplateResponse('edit_experience.html', {
        'request': request,
        'experience': experience
    })
@router.get('/add/new_experience', response_class=HTMLResponse)
async def add_experience(request: Request):
    return templates.TemplateResponse('edit_experience.html', {
        'request': request,
        'experience': {}
    })
@router.post('/add/experienceToDDBB')
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
    return RedirectResponse(url='/edit/experiences?success=added', status_code=303)
@router.post('/update/experience')
async def update_experience(
    id: str = Form(...),
    empresa: str = Form(...),
    puesto: str = Form(...),
    descripcion: str = Form(...),
    tecnologias: str = Form(...)
):
    data = {
        'empresa': empresa,
        'puesto': puesto,
        'descripcion': descripcion,
        'tecnologias': [t.strip() for t in tecnologias.split(',')]
    }
    await collections.experience.update_one(
        {'_id': ObjectId(id)},
        {'$set': data})
    return RedirectResponse(url='/edit/experiences?success=updated', status_code=303)
@router.post('/delete/experience/{id}')
async def delete_experience(id : str):
    await collections.experience.delete_one({'_id': ObjectId(id)})
    return RedirectResponse(url='/edit/experiences?success=deleted', status_code=303)

@router.get('/show/education', response_class=Request)
async def show_education(request: Request):
    success = request.query_params.get('success')
    educations = await collections.education.find({}).to_list(length=None)
    if not educations:
        educations = []
    return templates.TemplateResponse('educations.html', {
        'request': request,
        'education': educations,
        'success': success
    })

@router.get('/show/updateEducation/{id}', response_class= HTMLResponse)
async def show_update_experience(id: str, request: Request):
    education = await collections.education.find_one({'_id': ObjectId(id)})
    return templates.TemplateResponse('edit_education.html', {
        'request': request,
        'education': education
    })

@router.post('/update/education/{id}')
async def update_education(
    id: str,
    titulo: str = Form(...),
    institucion: str = Form(...),
    descripcion: str = Form(...),
    inicio: str = Form(...),
    fin: str = Form(...),
    estado: str = Form(None),
    ):
    data = {
        'titulo' : titulo,
        'institucion' : institucion,
        'descripcion' : descripcion,
        'inicio' : inicio,
        'fin' : fin
    }
    if estado is not None:
        data['estado'] = estado
    await collections.education.update_one({'_id': ObjectId(id)}, {'$set': data})
    return RedirectResponse('/show/education?success=updated', status_code=303)

@router.get('/show/add_new_education', response_class= HTMLResponse)
async def show_add_new_education(request: Request):
    return templates.TemplateResponse('edit_education.html', {
        'request': request,
        'education': {}
    })

@router.post('/add/new_education')
async def add_new_education(
    titulo: str = Form(...),
    institucion: str = Form(...),
    descripcion: str = Form(...),
    inicio: str = Form(...),
    fin: str = Form(...),
    estado: str = Form(None),
    ):
    data = {
         'titulo' : titulo,
        'institucion' : institucion,
        'descripcion' : descripcion,
        'inicio' : inicio,
        'fin' : fin
    }
    if estado is not None:
        data['estado'] = estado
    await collections.education.insert_one(data)
    return RedirectResponse('/show/education?success=added', status_code=303)

@router.post('/delete/education/{id}')
async def delete_education(id: str):
    await collections.education.delete_one({'_id': ObjectId(id)})
    return RedirectResponse('/show/education?success=deleted', status_code=303)

@router.get('/show/allProjects', response_class= HTMLResponse)
async def show_all_projects(request: Request):
    success = request.query_params.get('success')
    projects = await collections.projects.find({}).to_list(length=None)
    return templates.TemplateResponse('projects.html',{
        'request': request,
        'projects': projects,
        'success': success
    })

@router.get('/show/editProject/{id}')
async def show_project(id: str, request: Request):
    project = await collections.projects.find_one({'_id': ObjectId(id)})
    return templates.TemplateResponse('edit_project.html',{
        'request': request,
        'project': project
    })

@router.post('/update/project/{id}')
async def update_project(
    id: str,
    nombre: str = Form(...),
    descripcion: str = Form(...),
    tecnologias: str = Form(...),
    link: str = Form(...),
    github: str = Form(...),
    githubBackend: str = Form(...),
    backendOffline: Optional[str] = Form(None)
):
    data = {
        'nombre': nombre,
        'descripcion': descripcion,
        'tecnologias': [t.strip() for t in tecnologias.split(',')],
        'link': link,
        'github': github,
        'githubBackend': githubBackend,
        'backendOffline': backendOffline
    }
    await collections.projects.update_one({'_id': ObjectId(id)}, {'$set': data})
    return RedirectResponse('/show/allProjects?success=updated', status_code=303)

    
__all__ = ['router']