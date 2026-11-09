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
from app.services import experience_service, split_csv
router = APIRouter()
protected_router = APIRouter(
    dependencies=[Depends(require_login) ]
)

load_dotenv()
MONGO_URI = os.getenv('MONGOCLUSTER')
client = motor.motor_asyncio.AsyncIOMotorClient(MONGO_URI)

templates = Jinja2Templates(directory='app/templates')
@protected_router.get('/edit/experiences', response_class= HTMLResponse)
async def showExperiences(request: Request):
    success = request.query_params.get('success')
    experiences = await experience_service.list()
    return templates.TemplateResponse(request, 'experiences.html',{
        'request': request,
        'experiences': experiences,
        'success': success
    })

@protected_router.get('/edit/experience/{id}', response_class=HTMLResponse)
async def edit_experience(id: str, request:Request):
    experience = await experience_service.find(id)
    return templates.TemplateResponse(request, 'edit_experience.html', {
        'request': request,
        'experience': experience
    })
@protected_router.get('/add/new_experience', response_class=HTMLResponse)
async def add_experience(request: Request):
    return templates.TemplateResponse(request, 'edit_experience.html', {
        'request': request,
        'experience': {}
    })
@protected_router.post('/add/experienceToDDBB')
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
        'tecnologias': split_csv(tecnologias)
    }

    await experience_service.create(data)
    return RedirectResponse(url='/edit/experiences?success=added', status_code=303)
@protected_router.post('/update/experience')
async def update_experience(
    id: str = Form(...),
    empresa: str = Form(...),
    puesto: str = Form(...),
    periodo: str = Form(...),
    descripcion: str = Form(...),
    tecnologias: str = Form(...)
):
    data = {
        'empresa': empresa,
        'periodo': periodo,
        'puesto': puesto,
        'descripcion': descripcion,
        'tecnologias': split_csv(tecnologias)
    }
    await experience_service.update(id, data, missing_ok=True)
    return RedirectResponse(url='/edit/experiences?success=updated', status_code=303)
@protected_router.post('/delete/experience/{id}')
async def delete_experience(id : str):
    await experience_service.delete(id)
    return RedirectResponse(url='/edit/experiences?success=deleted', status_code=303)

__all__ = ['router']
