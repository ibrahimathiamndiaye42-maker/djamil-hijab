from datetime import timedelta
from flask import Blueprint, g, jsonify, request
from sqlalchemy import select, func, or_
from ..auth import login_required, require_permission
from ..constants import DEFAULT_SETTINGS
from ..errors import ApiError
from ..extensions import db
from ..models import (AuditLog, Category, Customer, Inventory, InventoryItem, Payment, Product, Sale, SaleItem,
                      Setting, StockMovement, User, now)
from ..services import audit, numbering, stock
from ..services.settings import get_settings
from ..utils import body, like, paginate, parse_day, text, to_int, iso

bp = Blueprint("control", __name__)


# ---------- inventaires ----------
def inv_dict(i, full=False):
    out = {"id": i.id, "code": i.code, "user": i.user.full_name, "notes": i.notes, "created_at": iso(i.created_at),
           "lines": len(i.items), "gaps": sum(1 for x in i.items if x.diff)}
    if full:
        out["items"] = [gap_dict(x) for x in i.items]
    return out


def gap_dict(x):
    return {"inventory": x.inventory.code, "date": iso(x.inventory.created_at), "user": x.inventory.user.full_name,
            "product_id": x.product_id, "product": x.product.name, "code": x.product.code,
            "theoretical": x.theoretical, "counted": x.counted, "diff": x.diff, "reason": x.reason}


@bp.get("/inventories")
@require_permission("inventories.run", "control.read")
def list_inventories():
    return jsonify(paginate(select(Inventory).order_by(Inventory.created_at.desc()), inv_dict))


@bp.get("/inventories/<int:iid>")
@require_permission("inventories.run", "control.read")
def get_inventory(iid):
    i = db.session.get(Inventory, iid)
    if not i:
        raise ApiError("Inventaire introuvable", 404)
    return jsonify(inv_dict(i, True))


@bp.post("/inventories")
@require_permission("inventories.run")
def create_inventory():
    d = body()
    items = d.get("items") or []
    if not items:
        raise ApiError("Aucun produit compté")
    seen = set()
    inv = Inventory(code=numbering.code("INV"), user_id=g.user.id, notes=text(d, "notes", "Notes", False, 2000))
    db.session.add(inv)
    db.session.flush()
    for it in sorted(items, key=lambda x: to_int(x.get("product_id"), "Produit", 1)):
        pid, counted = to_int(it.get("product_id"), "Produit", 1), to_int(it.get("counted"), "Quantité comptée", 0)
        if pid in seen:
            raise ApiError("Produit compté deux fois")
        seen.add(pid)
        p = stock.lock_product(pid)
        theo, diff = p.stock_qty, counted - p.stock_qty
        reason = text(it, "reason", "Motif", False, 500)
        if diff:
            if not reason:
                raise ApiError(f"Motif obligatoire pour l'écart de « {p.name} » ({diff:+d})")
            stock.apply_movement(pid, "INVENTAIRE", diff, g.user, reason, "inventory", inv.id)
        db.session.add(InventoryItem(inventory_id=inv.id, product_id=pid, theoretical=theo, counted=counted, diff=diff, reason=reason))
    audit.log(g.user, "INVENTAIRE", "inventory", inv.code, {"lignes": len(items)})
    db.session.commit()
    db.session.refresh(inv)
    return jsonify(inv_dict(inv, True)), 201


@bp.get("/control/gaps")
@require_permission("control.read")
def gaps():
    a = request.args
    stmt = select(InventoryItem).join(Inventory).where(InventoryItem.diff != 0)
    if a.get("date_from"):
        stmt = stmt.where(Inventory.created_at >= parse_day(a["date_from"]))
    if a.get("date_to"):
        stmt = stmt.where(Inventory.created_at < parse_day(a["date_to"], end=True))
    if a.get("user_id"):
        stmt = stmt.where(Inventory.user_id == to_int(a["user_id"], "Employé"))
    return jsonify(paginate(stmt.order_by(Inventory.created_at.desc(), InventoryItem.id.desc()), gap_dict))


# ---------- journal d'activité (lecture seule : aucune route d'écriture/suppression) ----------
@bp.get("/audit")
@require_permission("audit.read")
def audit_list():
    a = request.args
    stmt = select(AuditLog)
    if a.get("user_id"):
        stmt = stmt.where(AuditLog.user_id == to_int(a["user_id"], "Utilisateur"))
    if a.get("action"):
        stmt = stmt.where(AuditLog.action == a["action"])
    if a.get("q"):
        stmt = stmt.where(or_(AuditLog.entity_ref.ilike(like(a["q"])), AuditLog.user_name.ilike(like(a["q"]))))
    if a.get("date_from"):
        stmt = stmt.where(AuditLog.created_at >= parse_day(a["date_from"]))
    if a.get("date_to"):
        stmt = stmt.where(AuditLog.created_at < parse_day(a["date_to"], end=True))
    return jsonify(paginate(stmt.order_by(AuditLog.created_at.desc(), AuditLog.id.desc()),
                            lambda l: {"id": l.id, "user": l.user_name, "user_id": l.user_id, "action": l.action,
                                       "entity_type": l.entity_type, "entity_ref": l.entity_ref, "details": l.details,
                                       "created_at": iso(l.created_at)}))


# ---------- tableau de bord & rapports (jours en UTC = heure du Sénégal) ----------
def _sales_agg(since, until=None):
    stmt = select(func.coalesce(func.sum(Sale.total), 0), func.count()).where(Sale.status == "VALIDEE", Sale.created_at >= since)
    if until:
        stmt = stmt.where(Sale.created_at < until)
    r = db.session.execute(stmt).one()
    return int(r[0]), int(r[1])


@bp.get("/dashboard")
@require_permission("reports.read")
def dashboard():
    n = now()
    today = n.replace(hour=0, minute=0, second=0, microsecond=0)
    week, month = today - timedelta(days=today.weekday()), today.replace(day=1)
    rev_today, cnt_today = _sales_agg(today)
    units = db.session.execute(select(func.coalesce(func.sum(SaleItem.qty), 0)).join(Sale).where(Sale.status == "VALIDEE", Sale.created_at >= today)).scalar()
    since30 = today - timedelta(days=29)
    day = func.date(Sale.created_at)
    series = db.session.execute(select(day, func.sum(Sale.total)).where(Sale.status == "VALIDEE", Sale.created_at >= since30).group_by(day).order_by(day)).all()
    top_p = db.session.execute(select(SaleItem.product_name, func.sum(SaleItem.qty).label("q")).join(Sale).where(Sale.status == "VALIDEE", Sale.created_at >= since30)
                               .group_by(SaleItem.product_id, SaleItem.product_name).order_by(func.sum(SaleItem.qty).desc()).limit(5)).all()
    top_c = db.session.execute(select(Category.name, func.sum(SaleItem.qty)).select_from(SaleItem).join(Sale).join(Product, Product.id == SaleItem.product_id)
                               .join(Category, Category.id == Product.category_id).where(Sale.status == "VALIDEE", Sale.created_at >= since30)
                               .group_by(Category.name).order_by(func.sum(SaleItem.qty).desc()).limit(5)).all()
    recent = db.session.execute(select(AuditLog).order_by(AuditLog.created_at.desc()).limit(10)).scalars().all()
    gaps_recent = db.session.execute(select(InventoryItem).join(Inventory).where(InventoryItem.diff != 0).order_by(Inventory.created_at.desc()).limit(5)).scalars().all()
    return jsonify(
        today={"revenue": rev_today, "sales": cnt_today, "units": int(units or 0),
               "new_customers": db.session.execute(select(func.count()).select_from(Customer).where(Customer.created_at >= today)).scalar(),
               "movements": db.session.execute(select(func.count()).select_from(StockMovement).where(StockMovement.created_at >= today)).scalar()},
        low_stock=db.session.execute(select(func.count()).select_from(Product).where(Product.is_active.is_(True), Product.stock_qty > 0, Product.stock_qty <= Product.alert_threshold)).scalar(),
        out_of_stock=db.session.execute(select(func.count()).select_from(Product).where(Product.is_active.is_(True), Product.stock_qty <= 0)).scalar(),
        week_revenue=_sales_agg(week)[0], month_revenue=_sales_agg(month)[0],
        series=[{"day": str(d), "revenue": int(v)} for d, v in series],
        top_products=[{"name": a, "qty": int(b)} for a, b in top_p], top_categories=[{"name": a, "qty": int(b)} for a, b in top_c],
        corrections_30d=db.session.execute(select(func.count()).select_from(StockMovement).where(StockMovement.type == "CORRECTION", StockMovement.created_at >= since30)).scalar(),
        recent_gaps=[{"product": x.product.name, "theoretical": x.theoretical, "counted": x.counted, "diff": x.diff, "user": x.inventory.user.full_name, "date": iso(x.inventory.created_at)} for x in gaps_recent],
        recent_activity=[{"user": l.user_name, "action": l.action, "ref": l.entity_ref, "date": iso(l.created_at)} for l in recent])


@bp.get("/reports/sales")
@require_permission("reports.read")
def report_sales():
    a = request.args
    start = parse_day(a.get("date_from")) or (now().replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=29))
    end = parse_day(a.get("date_to"), end=True) or now() + timedelta(days=1)
    base = (Sale.status == "VALIDEE", Sale.created_at >= start, Sale.created_at < end)
    day = func.date(Sale.created_at)
    return jsonify(
        by_day=[{"day": str(d), "sales": c, "revenue": int(v)} for d, c, v in db.session.execute(select(day, func.count(), func.sum(Sale.total)).where(*base).group_by(day).order_by(day)).all()],
        by_user=[{"user": n, "sales": c, "revenue": int(v)} for n, c, v in db.session.execute(select(User.full_name, func.count(), func.sum(Sale.total)).join(User, User.id == Sale.user_id).where(*base).group_by(User.full_name).order_by(func.sum(Sale.total).desc())).all()],
        by_method=[{"method": m, "amount": int(v)} for m, v in db.session.execute(select(Payment.method, func.sum(Payment.amount)).join(Sale, Sale.id == Payment.sale_id).where(*base).group_by(Payment.method)).all()])


# ---------- paramètres ----------
@bp.get("/settings")
@login_required
def read_settings():
    return jsonify(get_settings())


@bp.patch("/settings")
@require_permission("settings.write")
def write_settings():
    d, changes = body(), {}
    old = get_settings()
    for key, value in d.items():
        if key not in DEFAULT_SETTINGS:
            raise ApiError(f"Paramètre inconnu : {key}")
        if key in ("phones", "payment_methods"):
            if not isinstance(value, list) or not all(isinstance(v, str) and v.strip() for v in value) or (key == "payment_methods" and not value):
                raise ApiError(f"Valeur invalide pour {key}")
            value = [v.strip() for v in value]
        elif not isinstance(value, str):
            raise ApiError(f"Valeur invalide pour {key}")
        row = db.session.get(Setting, key)
        if row:
            row.value = value
        else:
            db.session.add(Setting(key=key, value=value))
        changes[key] = {"avant": old.get(key), "apres": value}
    if changes:
        audit.log(g.user, "PARAMETRES_MODIFIES", "settings", None, changes)
    db.session.commit()
    return jsonify(get_settings())
