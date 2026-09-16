import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class Role(str, enum.Enum):
    ATTORNEY = "attorney"
    PARALEGAL = "paralegal"


class DraftStatus(str, enum.Enum):
    DRAFT = "draft"
    UNDER_REVIEW = "under_review"
    APPROVED = "approved"
    FINALIZED = "finalized"


class DocType(str, enum.Enum):
    WILL = "will"
    POA_FINANCIAL = "poa_financial"
    POA_HEALTHCARE = "poa_healthcare"
    HIPAA_AUTHORIZATION = "hipaa_authorization"


class UploadedDocType(str, enum.Enum):
    EXISTING_WILL = "existing_will"
    EXISTING_TRUST = "existing_trust"
    FINANCIAL_STATEMENT = "financial_statement"
    OTHER = "other"


class RiskSeverity(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class RiskCategory(str, enum.Enum):
    MISSING_CLAUSE = "missing_clause"
    CONFLICTING_BENEFICIARY = "conflicting_beneficiary"
    AMBIGUOUS_DISTRIBUTION = "ambiguous_distribution"
    EXECUTION_FORMALITY = "execution_formality"
    OTHER = "other"


class RiskStatus(str, enum.Enum):
    OPEN = "open"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    name: Mapped[str] = mapped_column(String(255))
    role: Mapped[Role] = mapped_column(Enum(Role), default=Role.PARALEGAL)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Client(Base):
    __tablename__ = "clients"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    date_of_birth: Mapped[str | None] = mapped_column(String(32), nullable=True)
    marital_status: Mapped[str | None] = mapped_column(String(64), nullable=True)
    state: Mapped[str | None] = mapped_column(String(64), nullable=True)  # governing jurisdiction
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    family_members: Mapped[list["FamilyMember"]] = relationship(
        back_populates="client", cascade="all, delete-orphan"
    )
    assets: Mapped[list["Asset"]] = relationship(back_populates="client", cascade="all, delete-orphan")
    goals: Mapped[list["Goal"]] = relationship(back_populates="client", cascade="all, delete-orphan")
    documents: Mapped[list["Document"]] = relationship(back_populates="client", cascade="all, delete-orphan")
    drafts: Mapped[list["Draft"]] = relationship(back_populates="client", cascade="all, delete-orphan")
    risk_flags: Mapped[list["RiskFlag"]] = relationship(back_populates="client", cascade="all, delete-orphan")


class FamilyMember(Base):
    __tablename__ = "family_members"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    client_id: Mapped[int] = mapped_column(ForeignKey("clients.id"))
    name: Mapped[str] = mapped_column(String(255))
    relationship_: Mapped[str] = mapped_column("relationship", String(64))
    date_of_birth: Mapped[str | None] = mapped_column(String(32), nullable=True)
    is_dependent: Mapped[bool] = mapped_column(default=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    client: Mapped["Client"] = relationship(back_populates="family_members")


class Asset(Base):
    __tablename__ = "assets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    client_id: Mapped[int] = mapped_column(ForeignKey("clients.id"))
    category: Mapped[str] = mapped_column(String(64))  # real_estate, bank, investment, retirement, business, life_insurance, personal_property, digital
    description: Mapped[str] = mapped_column(String(500))
    estimated_value: Mapped[float | None] = mapped_column(nullable=True)
    ownership: Mapped[str | None] = mapped_column(String(64), nullable=True)  # sole, joint, trust
    beneficiary_designation: Mapped[str | None] = mapped_column(String(500), nullable=True)

    client: Mapped["Client"] = relationship(back_populates="assets")


class Goal(Base):
    __tablename__ = "goals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    client_id: Mapped[int] = mapped_column(ForeignKey("clients.id"))
    description: Mapped[str] = mapped_column(String(1000))

    client: Mapped["Client"] = relationship(back_populates="goals")


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    client_id: Mapped[int] = mapped_column(ForeignKey("clients.id"))
    filename: Mapped[str] = mapped_column(String(255))
    doc_type: Mapped[UploadedDocType] = mapped_column(Enum(UploadedDocType), default=UploadedDocType.OTHER)
    storage_path: Mapped[str] = mapped_column(String(500))
    raw_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    extracted_summary: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON string
    uploaded_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    client: Mapped["Client"] = relationship(back_populates="documents")


class Draft(Base):
    __tablename__ = "drafts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    client_id: Mapped[int] = mapped_column(ForeignKey("clients.id"))
    doc_type: Mapped[DocType] = mapped_column(Enum(DocType))
    content: Mapped[str] = mapped_column(Text)
    status: Mapped[DraftStatus] = mapped_column(Enum(DraftStatus), default=DraftStatus.DRAFT)
    version: Mapped[int] = mapped_column(default=1)
    generated_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    generated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    reviewed_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    client: Mapped["Client"] = relationship(back_populates="drafts")


class RiskFlag(Base):
    __tablename__ = "risk_flags"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    client_id: Mapped[int] = mapped_column(ForeignKey("clients.id"))
    source_type: Mapped[str] = mapped_column(String(32))  # "draft" or "document"
    source_id: Mapped[int] = mapped_column(Integer)
    severity: Mapped[RiskSeverity] = mapped_column(Enum(RiskSeverity), default=RiskSeverity.MEDIUM)
    category: Mapped[RiskCategory] = mapped_column(Enum(RiskCategory), default=RiskCategory.OTHER)
    description: Mapped[str] = mapped_column(Text)
    status: Mapped[RiskStatus] = mapped_column(Enum(RiskStatus), default=RiskStatus.OPEN)
    resolved_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    resolution_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    client: Mapped["Client"] = relationship(back_populates="risk_flags")


class AuditLog(Base):
    __tablename__ = "audit_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    action: Mapped[str] = mapped_column(String(255))
    entity_type: Mapped[str] = mapped_column(String(64))
    entity_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
