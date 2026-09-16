import json
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, Request, UploadFile
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.config import settings
from app.db import get_db
from app.models import Document, RiskFlag, UploadedDocType
from app.security import get_current_user, log_action
from app.services.document_parser import process_document
from app.services.risk_flagging import check_document
from app.templating import templates

router = APIRouter()


def _login_redirect(request: Request) -> RedirectResponse:
    return RedirectResponse(url=f"/login?next={request.url.path}", status_code=303)


@router.post("/clients/{client_id}/documents")
async def upload_document(
    request: Request,
    client_id: int,
    doc_type: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    user = get_current_user(request, db)
    if not user:
        return _login_redirect(request)

    try:
        parsed_type = UploadedDocType(doc_type)
    except ValueError:
        parsed_type = UploadedDocType.OTHER

    client_dir = Path(settings.upload_dir) / f"client_{client_id}"
    client_dir.mkdir(parents=True, exist_ok=True)
    safe_name = Path(file.filename or "upload").name
    storage_path = client_dir / safe_name
    contents = await file.read()
    storage_path.write_bytes(contents)

    document = Document(
        client_id=client_id,
        filename=safe_name,
        doc_type=parsed_type,
        storage_path=str(storage_path),
        uploaded_by=user.id,
    )
    db.add(document)
    db.commit()
    db.refresh(document)
    log_action(db, user, "upload_document", "document", document.id, detail=safe_name)

    process_document(db, document, user)
    check_document(db, document, user)

    return RedirectResponse(url=f"/documents/{document.id}", status_code=303)


@router.get("/documents/{document_id}")
def document_detail(request: Request, document_id: int, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        return _login_redirect(request)
    document = db.get(Document, document_id)
    if not document:
        return RedirectResponse(url="/clients", status_code=303)

    extracted = {}
    if document.extracted_summary:
        try:
            extracted = json.loads(document.extracted_summary)
        except json.JSONDecodeError:
            extracted = {"parse_error": True, "raw": document.extracted_summary}

    risk_flags = (
        db.query(RiskFlag)
        .filter(RiskFlag.source_type == "document", RiskFlag.source_id == document_id)
        .order_by(RiskFlag.status.asc(), RiskFlag.severity.desc())
        .all()
    )

    return templates.TemplateResponse(
        request,
        "document_detail.html",
        {"user": user, "document": document, "extracted": extracted, "risk_flags": risk_flags},
    )


@router.post("/documents/{document_id}/risk-check")
def rerun_document_risk_check(request: Request, document_id: int, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        return _login_redirect(request)
    document = db.get(Document, document_id)
    if document:
        check_document(db, document, user)
    return RedirectResponse(url=f"/documents/{document_id}", status_code=303)
