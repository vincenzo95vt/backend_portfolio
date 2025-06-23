
from fastapi import APIRouter, Request, Form
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

load_dotenv()
MONGO_URI = os.getenv('MONGOCLUSTER')

router = APIRouter()

client = motor.motor_asyncio.AsyncIOMotorClient(MONGO_URI)
templates = Jinja2Templates(directory='app/templates')


@router.get('/show/education', response_class=HTMLResponse)
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

@router.get('/api/v1/education')
async def raw_data():
    cursor = collections.education.find({})
    results = []

    async for doc in cursor:
        doc['_id'] = str(doc['_id'])
        results.append(doc)
    return results


__all__ = ['router']
