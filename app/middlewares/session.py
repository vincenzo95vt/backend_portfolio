from fastapi import Request, HTTPException, status
from fastapi.responses import RedirectResponse


def require_login(request: Request):
    user = request.session.get("user")
    if not user:
        raise HTTPException(status_code=status.HTTP_302_FOUND, headers={"Location": "/login"})
    return user