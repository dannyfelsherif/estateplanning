"""Bootstrap the database and create the first attorney account if none exists.

Run once after configuring .env:
    python scripts/seed.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import settings
from app.db import SessionLocal, init_db
from app.models import Role, User
from app.security import hash_password


def main():
    init_db()
    db = SessionLocal()
    try:
        existing = db.query(User).count()
        if existing:
            print(f"Database already has {existing} user(s); skipping admin creation.")
            return

        admin = User(
            email=settings.admin_email.lower().strip(),
            hashed_password=hash_password(settings.admin_password),
            name=settings.admin_name,
            role=Role.ATTORNEY,
        )
        db.add(admin)
        db.commit()
        print(f"Created attorney account: {admin.email}")
        print("Log in at /login with the credentials from your .env file, then change the password.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
