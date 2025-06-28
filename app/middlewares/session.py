from fastapi import Request, Response
from fastapi.responses import RedirectResponse

async def auth_middleware(request: Request, call_next):
    if request.irl.path in ['/login'] or request.path.startswith('/static'):
        return await call_next(request)
    
    if not request.session.get('user'):
        return RedirectResponse(url='/login', status_code=303)
    
    response = await call_next(request)
    return response