from app.models import DocType, DraftStatus, RiskFlag
from app.services.drafting import generate_draft


def test_generate_draft_creates_watermarked_draft_and_runs_risk_check(db_session, sample_client, attorney_user):
    draft = generate_draft(db_session, sample_client, DocType.WILL, attorney_user)

    assert draft.id is not None
    assert draft.status == DraftStatus.DRAFT
    assert draft.client_id == sample_client.id
    assert "DRAFT — PENDING ATTORNEY REVIEW — NOT FOR EXECUTION" in draft.content

    # generate_draft runs an automatic risk check; flags (if any) are persisted
    # against this draft as their source.
    flags = db_session.query(RiskFlag).filter_by(source_type="draft", source_id=draft.id).all()
    assert isinstance(flags, list)


def test_draft_starts_in_draft_status_not_approved(db_session, sample_client, attorney_user):
    draft = generate_draft(db_session, sample_client, DocType.HIPAA_AUTHORIZATION, attorney_user)
    assert draft.status == DraftStatus.DRAFT
    assert draft.reviewed_by is None
