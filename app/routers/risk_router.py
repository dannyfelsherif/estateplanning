from datetime import datetime

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import RiskFlag, RiskStatus
from app.security import get_current_user, log_action, require_attorney

router = APIRouter()


def _login_redirect(request: Request) -> RedirectResponse:
    return RedirectResponse(url=f"/login?next={request.url.path}", status_code=303)


def _back_url(flag: RiskFlag) -> str:
    if flag.source_type == "draft":
        return f"/drafts/{flag.source_id}"
    return f"/documents/{flag.source_id}"


@router.post("/risk-flags/{flag_id}/resolve")
def resolve_flag(
    request: Request,
    flag_id: int,
    resolution_note: str = Form(""),
    db: Session = Depends(get_db),
):
    user = get_current_user(request, db)
    if not user:
        return _login_redirect(request)
    flag = db.get(RiskFlag, flag_id)
    if not flag:
        return RedirectResponse(url="/clients", status_code=303)
    if not require_attorney(user):
        return RedirectResponse(url=_back_url(flag), status_code=303)

    flag.status = RiskStatus.RESOLVED
    flag.resolved_by = user.id
    flag.resolved_at = datetime.utcnow()
    flag.resolution_note = resolution_note or None
    db.commit()
    log_action(db, user, "resolve_risk_flag", "risk_flag", flag.id)

    return RedirectResponse(url=_back_url(flag), status_code=303)


@router.post("/risk-flags/{flag_id}/acknowledge")
def acknowledge_flag(request: Request, flag_id: int, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        return _login_redirect(request)
    flag = db.get(RiskFlag, flag_id)
    if not flag:
        return RedirectResponse(url="/clients", status_code=303)

    flag.status = RiskStatus.ACKNOWLEDGED
    db.commit()
    log_action(db, user, "acknowledge_risk_flag", "risk_flag", flag.id)

    return RedirectResponse(url=_back_url(flag), status_code=303)
