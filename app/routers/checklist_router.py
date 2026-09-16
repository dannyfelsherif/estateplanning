from pathlib import Path

from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.db import get_db
from app.security import get_current_user
from app.templating import templates

router = APIRouter()

CHECKLIST_PATH = Path(__file__).resolve().parent.parent.parent / "docs" / "SECURITY_CHECKLIST.md"


@router.get("/checklist")
def checklist(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse(url=f"/login?next={request.url.path}", status_code=303)
    content = CHECKLIST_PATH.read_text() if CHECKLIST_PATH.exists() else "Checklist not found."
    return templates.TemplateResponse(request, "checklist.html", {"user": user, "content": content})
