from fastapi import APIRouter, Request, Form, Depends
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from fastapi.responses import RedirectResponse
from fastapi.responses import JSONResponse
from bson import ObjectId
import motor.motor_asyncio
from typing import Optional
from app.db.db import collections
from app.db.db import db
from dotenv import load_dotenv
import os
from app.middlewares.session import require_login

protected_router = APIRouter(
    dependencies=[Depends(require_login)]
)

load_dotenv()
MONGO_URI = os.getenv('MONGOCLUSTER')

router = APIRouter()

client = motor.motor_asyncio.AsyncIOMotorClient(MONGO_URI)

templates = Jinja2Templates(directory='app/templates')


@protected_router.get('/show/allProjects', response_class= HTMLResponse)
async def show_all_projects(request: Request):
    success = request.query_params.get('success')
    projects = await collections.projects.find({}).to_list(length=None)
    return templates.TemplateResponse('projects.html',{
        'request': request,
        'projects': projects,
        'success': success
    })

@protected_router.get('/show/editProject/{id}')
async def show_project(id: str, request: Request):
    project = await collections.projects.find_one({'_id': ObjectId(id)})
    return templates.TemplateResponse('edit_project.html',{
        'request': request,
        'project': project
    })

@protected_router.post('/update/project/{id}')
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

@protected_router.post('/add/new_project')
async def add_new_project(
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
    await collections.projects.insert_one(data)
    return RedirectResponse('/show/allProjects?success=added', status_code=303)
@protected_router.get('/show/newProject', response_class=HTMLResponse)
def show_new_project(request: Request):
    return templates.TemplateResponse('edit_project.html', {
        'request': request,
        'project': {}
    })

@protected_router.post('/delete/project/{id}')
async def delete_project(id: str):
    await collections.projects.delete_one({'_id': ObjectId(id)})
    return RedirectResponse('/show/allProjects?success=deleted', status_code=303)



__all__ = ['router']
