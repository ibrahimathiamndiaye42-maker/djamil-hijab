from flask import Blueprint, g, jsonify
from sqlalchemy import select, func
from werkzeug.security import check_password_hash, generate_password_hash
from ..auth import login_required, make_token, require_permission, user_dict
from ..constants import PERMISSIONS
from ..errors import ApiError
from ..extensions import db
from ..models import Permission, Role, User, now
from ..services import audit
from ..utils import body, text

bp = Blueprint("auth_users", __name__)


@bp.post("/auth/login")
def login():
    d = body()
    username = (d.get("username") or "").strip().lower()
    u = db.session.execute(select(User).where(func.lower(User.username) == username)).scalar_one_or_none()
    if not u or not u.is_active or not check_password_hash(u.password_hash, d.get("password") or ""):
        raise ApiError("Identifiants incorrects", 401)
    u.last_login = now()
    audit.log(u, "CONNEXION", "user", u.username)
    db.session.commit()
    return jsonify(token=make_token(u), user=user_dict(u))


@bp.get("/auth/me")
@login_required
def me():
    return jsonify(user_dict(g.user))


@bp.post("/auth/change-password")
@login_required
def change_password():
    d = body()
    if not check_password_hash(g.user.password_hash, d.get("old_password") or ""):
        raise ApiError("Ancien mot de passe incorrect", 400)
    new = d.get("new_password") or ""
    if len(new) < 8:
        raise ApiError("Le mot de passe doit contenir au moins 8 caractères")
    g.user.password_hash = generate_password_hash(new)
    audit.log(g.user, "MOT_DE_PASSE_MODIFIE", "user", g.user.username)
    db.session.commit()
    return jsonify(ok=True)


def _apply_perms(u, codes):
    codes = [c for c in (codes or []) if c in PERMISSIONS]
    u.extra_permissions = list(db.session.execute(select(Permission).where(Permission.code.in_(codes))).scalars()) if codes else []


@bp.get("/permissions")
@require_permission("users.manage")
def permissions():
    return jsonify([{"code": c, "label": l} for c, l in PERMISSIONS.items()])


@bp.get("/users")
@require_permission("users.manage")
def list_users():
    users = db.session.execute(select(User).order_by(User.full_name)).scalars().all()
    return jsonify([user_dict(u) for u in users])


@bp.post("/users")
@require_permission("users.manage")
def create_user():
    d = body()
    username = text(d, "username", "Identifiant", True, 60).lower()
    full_name = text(d, "full_name", "Nom complet", True, 120)
    password = d.get("password") or ""
    if len(password) < 8:
        raise ApiError("Le mot de passe doit contenir au moins 8 caractères")
    role_name = d.get("role", "EMPLOYE")
    role = db.session.execute(select(Role).where(Role.name == role_name)).scalar_one_or_none()
    if not role:
        raise ApiError("Rôle invalide")
    if db.session.execute(select(User.id).where(func.lower(User.username) == username)).first():
        raise ApiError("Cet identifiant existe déjà", 409)
    u = User(username=username, full_name=full_name, role=role, password_hash=generate_password_hash(password))
    _apply_perms(u, d.get("permissions"))
    db.session.add(u)
    audit.log(g.user, "EMPLOYE_CREE", "user", username, {"role": role_name, "permissions": d.get("permissions") or []})
    db.session.commit()
    return jsonify(user_dict(u)), 201


@bp.patch("/users/<int:uid>")
@require_permission("users.manage")
def update_user(uid):
    d = body()
    u = db.session.get(User, uid)
    if not u:
        raise ApiError("Utilisateur introuvable", 404)
    changes = {}
    if "full_name" in d:
        u.full_name = text(d, "full_name", "Nom complet", True, 120)
    if "role" in d and d["role"] != u.role.name:
        role = db.session.execute(select(Role).where(Role.name == d["role"])).scalar_one_or_none()
        if not role:
            raise ApiError("Rôle invalide")
        changes["role"] = [u.role.name, role.name]
        u.role = role
    if "is_active" in d:
        active = bool(d["is_active"])
        if not active and u.id == g.user.id:
            raise ApiError("Vous ne pouvez pas désactiver votre propre compte")
        changes["is_active"] = [u.is_active, active]
        u.is_active = active
    if "permissions" in d:
        old = sorted(p.code for p in u.extra_permissions)
        _apply_perms(u, d["permissions"])
        changes["permissions"] = [old, sorted(d["permissions"] or [])]
    if d.get("password"):
        if len(d["password"]) < 8:
            raise ApiError("Le mot de passe doit contenir au moins 8 caractères")
        u.password_hash = generate_password_hash(d["password"])
        changes["password"] = "réinitialisé"
    db.session.flush()
    if not db.session.execute(select(func.count()).select_from(User).join(Role).where(Role.name == "ADMIN", User.is_active.is_(True))).scalar():
        db.session.rollback()
        raise ApiError("Il doit rester au moins un administrateur actif")
    audit.log(g.user, "UTILISATEUR_MODIFIE", "user", u.username, changes)
    db.session.commit()
    return jsonify(user_dict(u))
