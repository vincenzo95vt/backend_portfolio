from fastapi import Request, Response
from fastapi.responses import RedirectResponse

async def auth_middleware(request: Request, call_next):
    protected_paths = ['/dashboard', '/edit', '/delete', '/add', '/show']
    if any(request.url.path.startswith(path) for path in protected_paths):
        username = request.cookies.get("username")
        if not username:
            return RedirectResponse(url="/login", status_code=303)

    response = await call_next(request)
    return response
