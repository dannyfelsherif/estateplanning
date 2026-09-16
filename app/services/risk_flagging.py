import json
import re

from sqlalchemy.orm import Session

from app import llm
from app.models import Client, Document, Draft, RiskCategory, RiskFlag, RiskSeverity, RiskStatus, User
from app.security import log_action
from app.services.intake import build_client_data

AMBIGUOUS_PATTERNS = [
    r"\bTBD\b",
    r"\betc\.\b",
    r"\band/or\b",
    r"\bsome of\b",
    r"\bas appropriate\b",
]


def _save_flags(db: Session, client_id: int, source_type: str, source_id: int, flags: list[dict]) -> list[RiskFlag]:
    # Re-running a check refreshes open findings but preserves flags an
    # attorney has already acknowledged or resolved (audit history).
    db.query(RiskFlag).filter(
        RiskFlag.source_type == source_type,
        RiskFlag.source_id == source_id,
        RiskFlag.status == RiskStatus.OPEN,
    ).delete()

    saved = []
    for f in flags:
        try:
            category = RiskCategory(f.get("category", "other"))
        except ValueError:
            category = RiskCategory.OTHER
        try:
            severity = RiskSeverity(f.get("severity", "medium"))
        except ValueError:
            severity = RiskSeverity.MEDIUM
        flag = RiskFlag(
            client_id=client_id,
            source_type=source_type,
            source_id=source_id,
            category=category,
            severity=severity,
            description=f.get("description", "Unspecified issue."),
            status=RiskStatus.OPEN,
        )
        db.add(flag)
        saved.append(flag)
    db.commit()
    return saved


def _rule_checks_draft(content: str, client_data: dict) -> list[dict]:
    flags = []

    if "[ATTORNEY INPUT NEEDED" in content:
        flags.append({
            "category": "missing_clause",
            "severity": "high",
            "description": "Draft contains one or more '[ATTORNEY INPUT NEEDED]' placeholders that must be resolved before this can proceed.",
        })

    leftover = re.findall(r"\[[A-Z0-9 /'\-]{3,60}\]", content)
    if leftover:
        sample = ", ".join(sorted(set(leftover))[:5])
        flags.append({
            "category": "missing_clause",
            "severity": "medium",
            "description": f"Draft still contains unfilled template placeholders (e.g. {sample}). Verify all required fields were captured in intake.",
        })

    dependents = [fm for fm in client_data.get("family_members", []) if fm.get("is_dependent")]
    if dependents and ("[GUARDIAN NAME]" in content or "GUARDIAN" not in content.upper()):
        flags.append({
            "category": "missing_clause",
            "severity": "high",
            "description": "Client has one or more dependent family members but the draft does not name a guardian.",
        })

    for asset in client_data.get("assets", []):
        beneficiary = (asset.get("beneficiary_designation") or "").strip()
        if beneficiary:
            first_token = beneficiary.split()[0]
            if len(first_token) > 2 and first_token not in content:
                flags.append({
                    "category": "conflicting_beneficiary",
                    "severity": "medium",
                    "description": (
                        f"Asset '{asset.get('description')}' lists beneficiary designation "
                        f"'{beneficiary}' in intake, but that name does not appear in the draft text — "
                        "verify it was carried through correctly."
                    ),
                })

    for pattern in AMBIGUOUS_PATTERNS:
        if re.search(pattern, content, re.IGNORECASE):
            flags.append({
                "category": "ambiguous_distribution",
                "severity": "low",
                "description": f"Draft contains ambiguous language matching pattern '{pattern}'. Consider more precise wording.",
            })

    if "WITNESS" not in content.upper() and "SIGNATURE" not in content.upper():
        flags.append({
            "category": "execution_formality",
            "severity": "high",
            "description": "Draft appears to be missing a witness/signature execution block.",
        })

    return flags


def check_draft(db: Session, draft: Draft, user: User, client_data: dict | None = None) -> list[RiskFlag]:
    client = db.get(Client, draft.client_id)
    if client_data is None:
        client_data = build_client_data(client)

    flags = _rule_checks_draft(draft.content, client_data)
    flags.extend(llm.analyze_risks(draft.content, client_data))

    saved = _save_flags(db, draft.client_id, "draft", draft.id, flags)
    log_action(db, user, "risk_check", "draft", draft.id, detail=f"{len(saved)} open flags")
    return saved


def check_document(db: Session, document: Document, user: User) -> list[RiskFlag]:
    client = db.get(Client, document.client_id)
    client_data = build_client_data(client)

    flags: list[dict] = []
    extracted = {}
    if document.extracted_summary:
        try:
            extracted = json.loads(document.extracted_summary)
        except json.JSONDecodeError:
            extracted = {}

    for issue in extracted.get("potential_issues", []) or []:
        flags.append({"category": "other", "severity": "medium", "description": str(issue)})

    doc_beneficiary_names = {
        (b.get("name") or "").strip()
        for b in (extracted.get("beneficiaries") or [])
        if isinstance(b, dict) and b.get("name")
    }
    current_beneficiary_names = {
        (a.get("beneficiary_designation") or "").strip()
        for a in client_data.get("assets", [])
        if a.get("beneficiary_designation")
    }
    if doc_beneficiary_names and current_beneficiary_names:
        overlap = any(
            doc_name.split()[0] in cur_name
            for doc_name in doc_beneficiary_names
            for cur_name in current_beneficiary_names
            if doc_name
        )
        if not overlap:
            flags.append({
                "category": "conflicting_beneficiary",
                "severity": "high",
                "description": (
                    "Beneficiaries named in this legacy document do not match any beneficiary "
                    "designation currently on file for this client's assets — verify whether this "
                    "reflects an intentional change or a conflict that needs to be resolved."
                ),
            })

    if document.raw_text:
        flags.extend(llm.analyze_risks(document.raw_text, {**client_data, "uploaded_document_type": document.doc_type.value}))

    saved = _save_flags(db, document.client_id, "document", document.id, flags)
    log_action(db, user, "risk_check", "document", document.id, detail=f"{len(saved)} open flags")
    return saved
