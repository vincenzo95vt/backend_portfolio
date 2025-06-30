from fastapi import Request, HTTPException
from fastapi.responses import RedirectResponse

def login_required(request: Request):
    username = request.cookies.get("username")
    if not username:
        return RedirectResponse(url="/login", status_code=303)
    return True
