from fastapi import APIRouter, Request, Form, Response, Depends, HTTPException, status
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from fastapi.responses import RedirectResponse
from fastapi.responses import JSONResponse
from app.middlewares.session import require_login
from bson import ObjectId
import motor.motor_asyncio
from typing import Optional
from app.db.db import collections
from app.services import about_service, education_service, experience_service, projects_service
from dotenv import load_dotenv
import os
from starlette.middleware.sessions import SessionMiddleware
import bcrypt 

load_dotenv()
MONGO_URI = os.getenv('MONGOCLUSTER')
secret_key = os.getenv('CLAVESECRETA')
router = APIRouter()

client = motor.motor_asyncio.AsyncIOMotorClient(MONGO_URI)

@router.get("/logout")
def logout(request: Request):
    request.session.clear()  # 🔒 Borra todos los datos de sesión
    return RedirectResponse(url="/login", status_code=302)


@router.get('/login')
def show_login(request: Request):
    return templates.TemplateResponse(request, 'login.html', {
        'request': request
    })

@router.post('/login')
async def do_login(request: Request, response: Response, username: str = Form(...), password: str = Form(...)):
    user = await collections.users.find_one({"username": username})

    if user and bcrypt.checkpw(password.encode('utf-8'), user['password'].encode('utf-8')):
        request.session["username"] = username
        return RedirectResponse(url='/dashboard', status_code=303)
    else:
        return templates.TemplateResponse(request, 'login.html', {
            'request': request,  
            'error': '❌ Credenciales incorrectas'
        })

templates = Jinja2Templates(directory='app/templates')
@router.get('/', response_class=HTMLResponse)
def home(request: Request):
    return templates.TemplateResponse(request, "welcome.html", {"request": request})



# ACCEDEMOS AL PANEL DE CONTROL
@router.get('/dashboard', response_class=HTMLResponse)
async def dashboard(resquest: Request, user= Depends(require_login)):
    projects = await projects_service.list()
    experience = await experience_service.list()
    education = await education_service.list()
    about_me = await about_service.get()
    data = {
        'projects': projects,
        'experience': experience,
        'education': education,
        'about_me': about_me,
    }
    return templates.TemplateResponse(resquest, "dashboard.html", {
        "request": resquest,
        'data': data
    })

# COMENZAMOS A CREAR LAS APIS PARA ACCEDER A ELLAS



__all__ = ['router']