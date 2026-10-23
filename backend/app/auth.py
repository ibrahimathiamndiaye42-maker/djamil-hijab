from datetime import datetime, timedelta, timezone
from functools import wraps
import jwt
from flask import request, g, current_app
from .errors import ApiError
from .extensions import db
from .models import User


def make_token(user):
    now = datetime.now(timezone.utc)
    payload = {"sub": str(user.id), "iat": now,
               "exp": now + timedelta(minutes=current_app.config["JWT_EXPIRES_MIN"])}
    return jwt.encode(payload, current_app.config["SECRET_KEY"], algorithm="HS256")


def _load_user():
    header = request.headers.get("Authorization", "")
    if not header.startswith("Bearer "):
        raise ApiError("Authentification requise", 401)
    try:
        data = jwt.decode(header[7:], current_app.config["SECRET_KEY"], algorithms=["HS256"])
        user = db.session.get(User, int(data["sub"]))
    except (jwt.PyJWTError, ValueError, KeyError):
        raise ApiError("Session invalide ou expirée", 401)
    if not user or not user.is_active:
        raise ApiError("Compte désactivé ou introuvable", 401)
    return user


def login_required(fn):
    @wraps(fn)
    def wrapper(*a, **kw):
        g.user = _load_user()
        return fn(*a, **kw)
    return wrapper


def require_permission(*codes):
    """Autorise si l'utilisateur possède AU MOINS UNE des permissions listées (contrôle côté serveur)."""
    def deco(fn):
        @wraps(fn)
        def wrapper(*a, **kw):
            g.user = _load_user()
            have = set(g.user.permission_codes())
            if not have.intersection(codes):
                raise ApiError("Accès refusé : permission insuffisante", 403)
            return fn(*a, **kw)
        return wrapper
    return deco


def has_perm(code):
    return code in g.user.permission_codes()


def user_dict(u):
    return {"id": u.id, "username": u.username, "full_name": u.full_name, "role": u.role.name,
            "is_active": u.is_active, "permissions": u.permission_codes(),
            "extra_permissions": sorted(p.code for p in u.extra_permissions),
            "last_login": u.last_login.isoformat() if u.last_login else None}
