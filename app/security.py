from itsdangerous import BadSignature, URLSafeTimedSerializer
from passlib.context import CryptContext
from sqlalchemy.orm import Session
from starlette.requests import Request
from starlette.responses import RedirectResponse

from app.config import settings
from app.models import AuditLog, Role, User

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
serializer = URLSafeTimedSerializer(settings.session_secret_key, salt="session")

SESSION_COOKIE = "estate_session"
SESSION_MAX_AGE = 60 * 60 * 12  # 12 hours


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(password: str, hashed: str) -> bool:
    return pwd_context.verify(password, hashed)


def create_session_cookie(user_id: int) -> str:
    return serializer.dumps({"user_id": user_id})


def read_session_cookie(token: str) -> int | None:
    try:
        data = serializer.loads(token, max_age=SESSION_MAX_AGE)
    except BadSignature:
        return None
    return data.get("user_id")


def get_current_user(request: Request, db: Session) -> User | None:
    token = request.cookies.get(SESSION_COOKIE)
    if not token:
        return None
    user_id = read_session_cookie(token)
    if not user_id:
        return None
    return db.get(User, user_id)


def require_login(request: Request, db: Session) -> User | RedirectResponse:
    """Returns the current user, or a redirect response if not authenticated.

    Callers must check `isinstance(result, RedirectResponse)` before use.
    """
    user = get_current_user(request, db)
    if user is None:
        return RedirectResponse(url=f"/login?next={request.url.path}", status_code=303)
    return user


def require_attorney(user: User) -> bool:
    return user.role == Role.ATTORNEY


def log_action(
    db: Session,
    user: User | None,
    action: str,
    entity_type: str,
    entity_id: int | None = None,
    detail: str | None = None,
) -> None:
    entry = AuditLog(
        user_id=user.id if user else None,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        detail=detail,
    )
    db.add(entry)
    db.commit()
