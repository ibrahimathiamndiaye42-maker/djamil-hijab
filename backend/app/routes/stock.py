from datetime import date
from flask import Blueprint, g, jsonify, request
from sqlalchemy import select, func
from ..auth import require_permission
from ..errors import ApiError
from ..extensions import db
from ..models import Product, Purchase, PurchaseItem, StockMovement, Supplier
from ..services import audit, numbering, stock
from ..utils import body, like, paginate, parse_day, text, to_int, iso
from ..constants import MOVEMENT_SIGN

bp = Blueprint("stock", __name__)


def movement_dict(m):
    return {"id": m.id, "code": m.code, "product_id": m.product_id, "product": m.product.name, "product_code": m.product.code,
            "type": m.type, "qty_before": m.qty_before, "qty_delta": m.qty_delta, "qty_after": m.qty_after,
            "reason": m.reason, "source_type": m.source_type, "source_id": m.source_id,
            "user": m.user.full_name, "user_id": m.user_id, "created_at": iso(m.created_at)}


@bp.get("/stock/movements")
@require_permission("stock.read")
def movements():
    a = request.args
    stmt = select(StockMovement)
    if a.get("product_id"):
        stmt = stmt.where(StockMovement.product_id == to_int(a["product_id"], "Produit"))
    if a.get("user_id"):
        stmt = stmt.where(StockMovement.user_id == to_int(a["user_id"], "Utilisateur"))
    if a.get("type"):
        stmt = stmt.where(StockMovement.type == a["type"])
    if a.get("date_from"):
        stmt = stmt.where(StockMovement.created_at >= parse_day(a["date_from"]))
    if a.get("date_to"):
        stmt = stmt.where(StockMovement.created_at < parse_day(a["date_to"], end=True))
    if a.get("q"):
        stmt = stmt.where(StockMovement.code.ilike(like(a["q"])))
    return jsonify(paginate(stmt.order_by(StockMovement.created_at.desc(), StockMovement.id.desc()), movement_dict))


@bp.post("/stock/adjust")
@require_permission("stock.adjust")
def adjust():
    """Mouvement manuel : CORRECTION, PERTE, ENDOMMAGE, RETOUR_CLIENT, RETOUR_FOURNISSEUR (motif obligatoire sauf retour client)."""
    d = body()
    mtype = d.get("type")
    if mtype not in ("CORRECTION", "PERTE", "ENDOMMAGE", "RETOUR_CLIENT", "RETOUR_FOURNISSEUR"):
        raise ApiError("Type de mouvement non autorisé ici")
    pid, qty = to_int(d.get("product_id"), "Produit", 1), to_int(d.get("qty"), "Quantité")
    if MOVEMENT_SIGN[mtype] != 0:
        qty = abs(qty) * MOVEMENT_SIGN[mtype]
    m = stock.apply_movement(pid, mtype, qty, g.user, text(d, "reason", "Motif", mtype != "RETOUR_CLIENT", 500), "manual")
    audit.log(g.user, "CORRECTION_STOCK" if mtype == "CORRECTION" else f"STOCK_{mtype}", "product", m.product.code,
              {"mouvement": m.code, "avant": m.qty_before, "apres": m.qty_after, "motif": m.reason})
    db.session.commit()
    return jsonify(movement_dict(m)), 201


def purchase_dict(p, full=False):
    out = {"id": p.id, "code": p.code, "date": p.arrival_date.isoformat(), "supplier": p.supplier.name if p.supplier else None,
           "supplier_id": p.supplier_id, "total": p.total, "user": p.user.full_name, "notes": p.notes}
    if full:
        out["items"] = [{"product_id": i.product_id, "product": i.product.name, "code": i.product.code,
                         "qty": i.qty, "unit_cost": i.unit_cost} for i in p.items]
    return out


@bp.get("/arrivals")
@require_permission("stock.entry", "stock.read")
def list_arrivals():
    a = request.args
    stmt = select(Purchase)
    if a.get("supplier_id"):
        stmt = stmt.where(Purchase.supplier_id == to_int(a["supplier_id"], "Fournisseur"))
    if a.get("q"):
        stmt = stmt.where(Purchase.code.ilike(like(a["q"])))
    return jsonify(paginate(stmt.order_by(Purchase.arrival_date.desc(), Purchase.id.desc()), purchase_dict))


@bp.get("/arrivals/<int:aid>")
@require_permission("stock.entry", "stock.read")
def get_arrival(aid):
    p = db.session.get(Purchase, aid)
    if not p:
        raise ApiError("Arrivage introuvable", 404)
    return jsonify(purchase_dict(p, True))


@bp.post("/arrivals")
@require_permission("stock.entry")
def create_arrival():
    d = body()
    items = d.get("items") or []
    if not items:
        raise ApiError("Ajoutez au moins un produit")
    try:
        day = date.fromisoformat(d["date"][:10]) if d.get("date") else date.today()
    except ValueError:
        raise ApiError("Date invalide")
    sid = to_int(d["supplier_id"], "Fournisseur", 1) if d.get("supplier_id") else None
    if sid and not db.session.get(Supplier, sid):
        raise ApiError("Fournisseur introuvable", 404)
    purchase = Purchase(code=numbering.code("ARR"), supplier_id=sid, arrival_date=day, notes=text(d, "notes", "Notes", False, 2000),
                        user_id=g.user.id, total=0)
    db.session.add(purchase)
    db.session.flush()
    total = 0
    for it in sorted(items, key=lambda x: to_int(x.get("product_id"), "Produit", 1)):
        pid, qty, cost = to_int(it.get("product_id"), "Produit", 1), to_int(it.get("qty"), "Quantité", 1), to_int(it.get("unit_cost", 0), "Prix d'achat", 0)
        db.session.add(PurchaseItem(purchase_id=purchase.id, product_id=pid, qty=qty, unit_cost=cost))
        m = stock.apply_movement(pid, "ENTREE", qty, g.user, f"Arrivage {purchase.code}", "purchase", purchase.id)
        if cost and m.product.purchase_price != cost:
            audit.log(g.user, "PRIX_ACHAT_MODIFIE", "product", m.product.code, {"avant": m.product.purchase_price, "apres": cost})
            m.product.purchase_price = cost
        total += qty * cost
    purchase.total = total
    audit.log(g.user, "ARRIVAGE_ENREGISTRE", "purchase", purchase.code, {"lignes": len(items), "total": total})
    db.session.commit()
    return jsonify(purchase_dict(purchase, True)), 201
