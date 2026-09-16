from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Asset, Client, FamilyMember, Goal, RiskFlag, RiskStatus
from app.security import get_current_user, log_action
from app.services.intake import generate_summary
from app.templating import templates

router = APIRouter()


def _login_redirect(request: Request) -> RedirectResponse:
    return RedirectResponse(url=f"/login?next={request.url.path}", status_code=303)


@router.get("/")
def root(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    return RedirectResponse(url="/clients", status_code=303)


@router.get("/clients")
def list_clients(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        return _login_redirect(request)
    clients = db.query(Client).order_by(Client.created_at.desc()).all()
    return templates.TemplateResponse(request, "dashboard.html", {"user": user, "clients": clients})


@router.get("/clients/new")
def new_client_form(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        return _login_redirect(request)
    return templates.TemplateResponse(request, "new_client.html", {"user": user})


@router.post("/clients")
def create_client(
    request: Request,
    name: str = Form(...),
    date_of_birth: str = Form(""),
    marital_status: str = Form(""),
    state: str = Form(""),
    notes: str = Form(""),
    db: Session = Depends(get_db),
):
    user = get_current_user(request, db)
    if not user:
        return _login_redirect(request)
    client = Client(
        name=name,
        date_of_birth=date_of_birth or None,
        marital_status=marital_status or None,
        state=state or None,
        notes=notes or None,
        created_by=user.id,
    )
    db.add(client)
    db.commit()
    db.refresh(client)
    log_action(db, user, "create_client", "client", client.id)
    return RedirectResponse(url=f"/clients/{client.id}", status_code=303)


@router.get("/clients/{client_id}")
def client_detail(request: Request, client_id: int, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        return _login_redirect(request)
    client = db.get(Client, client_id)
    if not client:
        return RedirectResponse(url="/clients", status_code=303)

    risk_flags = (
        db.query(RiskFlag)
        .filter(RiskFlag.client_id == client_id)
        .order_by(RiskFlag.status.asc(), RiskFlag.severity.desc(), RiskFlag.created_at.desc())
        .all()
    )
    open_flag_count = sum(1 for f in risk_flags if f.status == RiskStatus.OPEN)

    return templates.TemplateResponse(
        request,
        "client_detail.html",
        {
            "user": user,
            "client": client,
            "risk_flags": risk_flags,
            "open_flag_count": open_flag_count,
        },
    )


@router.post("/clients/{client_id}/family")
def add_family_member(
    request: Request,
    client_id: int,
    name: str = Form(...),
    relationship: str = Form(...),
    date_of_birth: str = Form(""),
    is_dependent: bool = Form(False),
    notes: str = Form(""),
    db: Session = Depends(get_db),
):
    user = get_current_user(request, db)
    if not user:
        return _login_redirect(request)
    fm = FamilyMember(
        client_id=client_id,
        name=name,
        relationship_=relationship,
        date_of_birth=date_of_birth or None,
        is_dependent=is_dependent,
        notes=notes or None,
    )
    db.add(fm)
    db.commit()
    log_action(db, user, "add_family_member", "client", client_id, detail=name)
    return RedirectResponse(url=f"/clients/{client_id}#family", status_code=303)


@router.post("/clients/{client_id}/assets")
def add_asset(
    request: Request,
    client_id: int,
    category: str = Form(...),
    description: str = Form(...),
    estimated_value: str = Form(""),
    ownership: str = Form(""),
    beneficiary_designation: str = Form(""),
    db: Session = Depends(get_db),
):
    user = get_current_user(request, db)
    if not user:
        return _login_redirect(request)
    value = None
    if estimated_value.strip():
        try:
            value = float(estimated_value)
        except ValueError:
            value = None
    asset = Asset(
        client_id=client_id,
        category=category,
        description=description,
        estimated_value=value,
        ownership=ownership or None,
        beneficiary_designation=beneficiary_designation or None,
    )
    db.add(asset)
    db.commit()
    log_action(db, user, "add_asset", "client", client_id, detail=description)
    return RedirectResponse(url=f"/clients/{client_id}#assets", status_code=303)


@router.post("/clients/{client_id}/goals")
def add_goal(
    request: Request,
    client_id: int,
    description: str = Form(...),
    db: Session = Depends(get_db),
):
    user = get_current_user(request, db)
    if not user:
        return _login_redirect(request)
    db.add(Goal(client_id=client_id, description=description))
    db.commit()
    log_action(db, user, "add_goal", "client", client_id, detail=description)
    return RedirectResponse(url=f"/clients/{client_id}#goals", status_code=303)


@router.post("/clients/{client_id}/summary")
def generate_client_summary_route(request: Request, client_id: int, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        return _login_redirect(request)
    client = db.get(Client, client_id)
    if client:
        generate_summary(db, client, user)
    return RedirectResponse(url=f"/clients/{client_id}#summary", status_code=303)
