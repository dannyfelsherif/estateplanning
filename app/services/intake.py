from sqlalchemy.orm import Session

from app import llm
from app.models import Client, User
from app.security import log_action


def build_client_data(client: Client) -> dict:
    """Structured view of everything known about a client, used both to
    render the UI and as the payload sent to the LLM for summaries,
    drafting, and risk analysis."""
    return {
        "name": client.name,
        "date_of_birth": client.date_of_birth,
        "marital_status": client.marital_status,
        "state": client.state,
        "notes": client.notes,
        "family_members": [
            {
                "name": fm.name,
                "relationship": fm.relationship_,
                "date_of_birth": fm.date_of_birth,
                "is_dependent": fm.is_dependent,
                "notes": fm.notes,
            }
            for fm in client.family_members
        ],
        "assets": [
            {
                "category": a.category,
                "description": a.description,
                "estimated_value": a.estimated_value,
                "ownership": a.ownership,
                "beneficiary_designation": a.beneficiary_designation,
            }
            for a in client.assets
        ],
        "goals": [g.description for g in client.goals],
    }


def generate_summary(db: Session, client: Client, user: User) -> str:
    data = build_client_data(client)
    summary = llm.generate_client_summary(data)
    client.summary = summary
    db.commit()
    log_action(db, user, "generate_summary", "client", client.id)
    return summary
