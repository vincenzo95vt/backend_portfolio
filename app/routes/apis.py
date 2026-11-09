from fastapi import APIRouter, Request, Form, Depends
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from fastapi.responses import RedirectResponse
from fastapi.responses import JSONResponse
from bson import ObjectId
import motor.motor_asyncio
from typing import Optional
from app.db.db import collections
from app.services import about_service, education_service, experience_service, projects_service
from app.db.db import db
from dotenv import load_dotenv
import os

load_dotenv()
MONGO_URI = os.getenv('MONGOCLUSTER')
client = motor.motor_asyncio.AsyncIOMotorClient(MONGO_URI)
router = APIRouter()
templates = Jinja2Templates(directory='app/templates')

@router.get('/api/v1', response_class=HTMLResponse)
async def api_index(request: Request):
    return templates.TemplateResponse(request, 'api_index.html', {
        'request': request
    })
@router.get('/api/v1/about_me')
async def about_data():
    return await about_service.list()

@router.get('/api/v1/education')
async def education_data():
    return await education_service.list()
@router.get('/api/v1/experience')
async def experience_data():
    return await experience_service.list()

@router.get('/api/v1/projects')
async def projects_data():
    return await projects_service.list()

__all__ = ['router']