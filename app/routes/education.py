
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
from app.services import education_service
from app.routes.forms import apply_orden_on_create, form_orden, orden_update_args
load_dotenv()
MONGO_URI = os.getenv('MONGOCLUSTER')

router = APIRouter()

client = motor.motor_asyncio.AsyncIOMotorClient(MONGO_URI)
templates = Jinja2Templates(directory='app/templates')

protected_router = APIRouter(
    dependencies=[Depends(require_login)]
)
@protected_router.get('/show/education', response_class=HTMLResponse)
async def show_education(request: Request):
    success = request.query_params.get('success')
    educations = await education_service.list()
    if not educations:
        educations = []
    return templates.TemplateResponse(request, 'educations.html', {
        'request': request,
        'education': educations,
        'success': success
    })

@protected_router.get('/show/updateEducation/{id}', response_class= HTMLResponse)
async def show_update_experience(id: str, request: Request):
    education = await education_service.find(id)
    return templates.TemplateResponse(request, 'edit_education.html', {
        'request': request,
        'education': education
    })

@protected_router.post('/update/education/{id}')
async def update_education(
    id: str,
    titulo: str = Form(...),
    institucion: str = Form(...),
    descripcion: str = Form(...),
    inicio: str = Form(...),
    fin: str = Form(...),
    estado: str = Form(None),
    orden: Optional[str] = Form(None),
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
    await education_service.update(id, data, missing_ok=True, **orden_update_args(data, form_orden(orden)))
    return RedirectResponse('/show/education?success=updated', status_code=303)

@protected_router.get('/show/add_new_education', response_class= HTMLResponse)
async def show_add_new_education(request: Request):
    return templates.TemplateResponse(request, 'edit_education.html', {
        'request': request,
        'education': {}
    })

@protected_router.post('/add/new_education')
async def add_new_education(
    titulo: str = Form(...),
    institucion: str = Form(...),
    descripcion: str = Form(...),
    inicio: str = Form(...),
    fin: str = Form(...),
    estado: str = Form(None),
    orden: Optional[str] = Form(None),
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
    await education_service.create(apply_orden_on_create(data, form_orden(orden)))
    return RedirectResponse('/show/education?success=added', status_code=303)

@protected_router.post('/delete/education/{id}')
async def delete_education(id: str):
    await education_service.delete(id)
    return RedirectResponse('/show/education?success=deleted', status_code=303)



__all__ = ['router']
