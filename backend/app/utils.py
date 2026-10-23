from datetime import datetime, timedelta, timezone
from flask import request
from .errors import ApiError
from .extensions import db


def body():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        raise ApiError("Corps JSON invalide")
    return data


def to_int(value, label, minimum=None):
    if isinstance(value, bool):
        raise ApiError(f"{label} invalide")
    try:
        n = int(value)
    except (TypeError, ValueError):
        raise ApiError(f"{label} invalide")
    if minimum is not None and n < minimum:
        raise ApiError(f"{label} doit être supérieur ou égal à {minimum}")
    return n


def text(data, key, label, required=False, maxlen=255):
    v = data.get(key)
    v = v.strip() if isinstance(v, str) else v
    if v in (None, ""):
        if required:
            raise ApiError(f"{label} obligatoire")
        return None
    if not isinstance(v, str):
        raise ApiError(f"{label} invalide")
    if len(v) > maxlen:
        raise ApiError(f"{label} trop long")
    return v


def parse_day(value, end=False):
    if not value:
        return None
    try:
        d = datetime.strptime(value[:10], "%Y-%m-%d").replace(tzinfo=timezone.utc)
    except ValueError:
        raise ApiError("Date invalide (format AAAA-MM-JJ)")
    return d + timedelta(days=1) if end else d


def like(q):
    return f"%{q.strip().replace('%', '').replace('_', '')}%"


def paginate(stmt, serializer):
    page = max(1, to_int(request.args.get("page", 1), "Page"))
    per = min(100, max(1, to_int(request.args.get("per_page", 50), "Taille de page")))
    p = db.paginate(stmt, page=page, per_page=per, max_per_page=100, error_out=False)
    return {"items": [serializer(i) for i in p.items], "total": p.total, "page": p.page, "per_page": p.per_page}


def iso(dt):
    return dt.isoformat() if dt else None
