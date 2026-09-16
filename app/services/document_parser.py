import json
from pathlib import Path

from sqlalchemy.orm import Session

from app import llm
from app.models import Document, User
from app.security import log_action


def extract_text(path: str) -> str:
    p = Path(path)
    if p.suffix.lower() == ".pdf":
        from pypdf import PdfReader

        reader = PdfReader(str(p))
        return "\n".join((page.extract_text() or "") for page in reader.pages)
    return p.read_text(errors="ignore")


def process_document(db: Session, document: Document, user: User) -> Document:
    raw_text = extract_text(document.storage_path)
    document.raw_text = raw_text
    summary = llm.summarize_document(raw_text, document.doc_type.value)
    document.extracted_summary = json.dumps(summary, indent=2, default=str)
    db.commit()
    log_action(db, user, "parse_document", "document", document.id)
    return document
