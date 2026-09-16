from datetime import datetime

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Client, Draft, DraftStatus, DocType, RiskFlag
from app.security import get_current_user, log_action, require_attorney
from app.services.drafting import generate_draft
from app.services.risk_flagging import check_draft
from app.templating import templates

router = APIRouter()

ALLOWED_TRANSITIONS = {
    DraftStatus.DRAFT: {DraftStatus.UNDER_REVIEW},
    DraftStatus.UNDER_REVIEW: {DraftStatus.APPROVED, DraftStatus.DRAFT},
    DraftStatus.APPROVED: {DraftStatus.FINALIZED, DraftStatus.UNDER_REVIEW},
    DraftStatus.FINALIZED: set(),
}

ATTORNEY_ONLY_TARGETS = {DraftStatus.APPROVED, DraftStatus.FINALIZED}


def _login_redirect(request: Request) -> RedirectResponse:
    return RedirectResponse(url=f"/login?next={request.url.path}", status_code=303)


@router.post("/clients/{client_id}/drafts")
def create_draft(request: Request, client_id: int, doc_type: str = Form(...), db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        return _login_redirect(request)
    client = db.get(Client, client_id)
    if not client:
        return RedirectResponse(url="/clients", status_code=303)
    try:
        parsed_type = DocType(doc_type)
    except ValueError:
        return RedirectResponse(url=f"/clients/{client_id}", status_code=303)

    draft = generate_draft(db, client, parsed_type, user)
    return RedirectResponse(url=f"/drafts/{draft.id}", status_code=303)


@router.get("/drafts/{draft_id}")
def draft_detail(request: Request, draft_id: int, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        return _login_redirect(request)
    draft = db.get(Draft, draft_id)
    if not draft:
        return RedirectResponse(url="/clients", status_code=303)

    risk_flags = (
        db.query(RiskFlag)
        .filter(RiskFlag.source_type == "draft", RiskFlag.source_id == draft_id)
        .order_by(RiskFlag.status.asc(), RiskFlag.severity.desc())
        .all()
    )
    next_statuses = sorted(ALLOWED_TRANSITIONS.get(draft.status, set()), key=lambda s: s.value)

    return templates.TemplateResponse(
        request,
        "draft_detail.html",
        {
            "user": user,
            "draft": draft,
            "risk_flags": risk_flags,
            "next_statuses": next_statuses,
            "attorney_only_targets": ATTORNEY_ONLY_TARGETS,
        },
    )


@router.post("/drafts/{draft_id}/status")
def update_draft_status(request: Request, draft_id: int, target: str = Form(...), db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        return _login_redirect(request)
    draft = db.get(Draft, draft_id)
    if not draft:
        return RedirectResponse(url="/clients", status_code=303)

    try:
        target_status = DraftStatus(target)
    except ValueError:
        return RedirectResponse(url=f"/drafts/{draft_id}", status_code=303)

    if target_status not in ALLOWED_TRANSITIONS.get(draft.status, set()):
        return RedirectResponse(url=f"/drafts/{draft_id}", status_code=303)

    if target_status in ATTORNEY_ONLY_TARGETS and not require_attorney(user):
        return RedirectResponse(url=f"/drafts/{draft_id}", status_code=303)

    draft.status = target_status
    if target_status in (DraftStatus.APPROVED, DraftStatus.FINALIZED):
        draft.reviewed_by = user.id
        draft.reviewed_at = datetime.utcnow()
    db.commit()
    log_action(db, user, "draft_status_change", "draft", draft.id, detail=target_status.value)

    return RedirectResponse(url=f"/drafts/{draft_id}", status_code=303)


@router.post("/drafts/{draft_id}/risk-check")
def rerun_draft_risk_check(request: Request, draft_id: int, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        return _login_redirect(request)
    draft = db.get(Draft, draft_id)
    if draft:
        check_draft(db, draft, user)
    return RedirectResponse(url=f"/drafts/{draft_id}", status_code=303)
