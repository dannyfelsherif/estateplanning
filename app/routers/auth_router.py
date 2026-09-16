from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import User
from app.security import SESSION_COOKIE, create_session_cookie, verify_password
from app.templating import templates

router = APIRouter()


@router.get("/login")
def login_form(request: Request, next: str = "/clients"):
    return templates.TemplateResponse(request, "login.html", {"next": next, "error": None})


@router.post("/login")
def login_submit(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    next: str = Form("/clients"),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.email == email.lower().strip()).first()
    if not user or not verify_password(password, user.hashed_password):
        return templates.TemplateResponse(
            request, "login.html", {"next": next, "error": "Invalid email or password."}, status_code=401
        )
    response = RedirectResponse(url=next or "/clients", status_code=303)
    response.set_cookie(
        SESSION_COOKIE,
        create_session_cookie(user.id),
        httponly=True,
        samesite="lax",
        max_age=60 * 60 * 12,
    )
    return response


@router.get("/logout")
def logout():
    response = RedirectResponse(url="/login", status_code=303)
    response.delete_cookie(SESSION_COOKIE)
    return response
