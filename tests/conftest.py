import os
import tempfile
import uuid

_TMP_DIR = tempfile.mkdtemp()
os.environ["DATABASE_URL"] = f"sqlite:///{_TMP_DIR}/test.db"
os.environ["UPLOAD_DIR"] = f"{_TMP_DIR}/uploads"
os.environ["SESSION_SECRET_KEY"] = "test-secret-key"
os.environ["ANTHROPIC_API_KEY"] = ""  # force mock LLM mode for deterministic tests

import pytest  # noqa: E402

from app.db import SessionLocal, init_db  # noqa: E402
from app.models import Client, Role, User  # noqa: E402
from app.security import hash_password  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def _init_db():
    init_db()


@pytest.fixture
def db_session():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def attorney_user(db_session):
    user = User(
        email=f"attorney-{uuid.uuid4().hex[:8]}@test.local",
        hashed_password=hash_password("password123"),
        name="Test Attorney",
        role=Role.ATTORNEY,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def sample_client(db_session):
    client = Client(name="Jane Doe", state="California", marital_status="Married")
    db_session.add(client)
    db_session.commit()
    db_session.refresh(client)
    return client
