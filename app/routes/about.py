from fastapi import APIRouter, Request, Form, Depends
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from fastapi.responses import RedirectResponse
from fastapi.responses import JSONResponse
from bson import ObjectId
import motor.motor_asyncio
from typing import Optional
from app.middlewares.session import require_login
from app.db.db import collections
from app.db.db import db
from dotenv import load_dotenv
import os

load_dotenv()
MONGO_URI = os.getenv('MONGOCLUSTER')

router = APIRouter()

client = motor.motor_asyncio.AsyncIOMotorClient(MONGO_URI)

protected_router = APIRouter(
    dependencies=[Depends(require_login)]
)

templates = Jinja2Templates(directory='app/templates')
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

@router.get('/api/v1/about_me')
async def raw_data():
    cursor = collections.aboutMe.find({})
    results = []

    async for doc in cursor:
        doc['_id'] = str(doc['_id'])
        results.append(doc)
    return results

__all__ = ['router']
