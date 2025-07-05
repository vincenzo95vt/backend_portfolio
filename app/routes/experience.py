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
    dependencies=[Depends(require_login) ]
)

load_dotenv()
MONGO_URI = os.getenv('MONGOCLUSTER')

router = APIRouter()

client = motor.motor_asyncio.AsyncIOMotorClient(MONGO_URI)

templates = Jinja2Templates(directory='app/templates')
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
@router.get('/api/v1/experience')
async def raw_data():
    cursor = collections.experience.find({})
    results = []

    async for doc in cursor:
        doc['_id'] = str(doc['_id'])
        results.append(doc)
    return results


__all__ = ['router']
