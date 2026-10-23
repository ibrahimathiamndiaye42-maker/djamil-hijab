from flask import Blueprint, g, jsonify, request, current_app, send_from_directory
from sqlalchemy import select, func, or_
from ..auth import login_required, require_permission, has_perm
from ..errors import ApiError
from ..extensions import db
from ..models import Category, Customer, Product, Purchase, Sale, Supplier
from ..services import audit, numbering, stock, storage
from ..utils import body, like, paginate, text, to_int, iso

bp = Blueprint("catalog", __name__)


def product_status(p):
    if p.stock_qty <= 0:
        return "RUPTURE"
    return "FAIBLE" if p.stock_qty <= p.alert_threshold else "NORMAL"


def product_dict(p):
    return {"id": p.id, "code": p.code, "name": p.name, "reference": p.reference, "category_id": p.category_id,
            "category": p.category.name if p.category else None, "subcategory": p.subcategory,
            "description": p.description, "color": p.color, "size": p.size, "attributes": p.attributes or {},
            "purchase_price": p.purchase_price, "sell_price": p.sell_price, "stock_qty": p.stock_qty,
            "alert_threshold": p.alert_threshold, "photo_url": p.photo_url, "supplier_id": p.supplier_id,
            "supplier": p.supplier.name if p.supplier else None, "is_active": p.is_active,
            "stock_value": p.stock_qty * p.purchase_price, "status": product_status(p)}


# ---------- catégories ----------
@bp.get("/categories")
@login_required
def categories():
    rows = db.session.execute(select(Category).order_by(Category.name)).scalars().all()
    return jsonify([{"id": c.id, "name": c.name, "is_active": c.is_active} for c in rows])


@bp.post("/categories")
@require_permission("categories.write")
def create_category():
    name = text(body(), "name", "Nom", True, 80)
    if db.session.execute(select(Category.id).where(func.lower(Category.name) == name.lower())).first():
        raise ApiError("Cette catégorie existe déjà", 409)
    c = Category(name=name)
    db.session.add(c)
    audit.log(g.user, "CATEGORIE_CREEE", "category", name)
    db.session.commit()
    return jsonify(id=c.id, name=c.name, is_active=True), 201


@bp.patch("/categories/<int:cid>")
@require_permission("categories.write")
def update_category(cid):
    d, c = body(), db.session.get(Category, cid)
    if not c:
        raise ApiError("Catégorie introuvable", 404)
    old = {"name": c.name, "is_active": c.is_active}
    if "name" in d:
        c.name = text(d, "name", "Nom", True, 80)
    if "is_active" in d:
        c.is_active = bool(d["is_active"])
    audit.log(g.user, "CATEGORIE_MODIFIEE", "category", c.name, {"avant": old, "apres": {"name": c.name, "is_active": c.is_active}})
    db.session.commit()
    return jsonify(id=c.id, name=c.name, is_active=c.is_active)


# ---------- produits ----------
@bp.get("/products")
@require_permission("products.read", "sales.create", "stock.read")
def list_products():
    a = request.args
    stmt = select(Product)
    if a.get("q"):
        q = like(a["q"])
        stmt = stmt.where(or_(Product.name.ilike(q), Product.code.ilike(q), Product.reference.ilike(q)))
    if a.get("category_id"):
        stmt = stmt.where(Product.category_id == to_int(a["category_id"], "Catégorie"))
    if a.get("active", "1") == "1":
        stmt = stmt.where(Product.is_active.is_(True))
    st = a.get("status")
    if st == "RUPTURE":
        stmt = stmt.where(Product.stock_qty <= 0)
    elif st == "FAIBLE":
        stmt = stmt.where(Product.stock_qty > 0, Product.stock_qty <= Product.alert_threshold)
    elif st == "NORMAL":
        stmt = stmt.where(Product.stock_qty > Product.alert_threshold)
    return jsonify(paginate(stmt.order_by(Product.name, Product.id), product_dict))


def _product_fields(d, p, creating=False):
    if creating or "name" in d:
        p.name = text(d, "name", "Nom du produit", True, 200)
    for key, label, ln in (("reference", "Référence", 80), ("subcategory", "Sous-catégorie", 80),
                           ("description", "Description", 2000), ("color", "Couleur", 60), ("size", "Taille", 40),
                           ("photo_url", "Photo", 500)):
        if key in d:
            setattr(p, key, text(d, key, label, False, ln))
    if "attributes" in d:
        if d["attributes"] is not None and not isinstance(d["attributes"], dict):
            raise ApiError("Attributs invalides")
        p.attributes = d["attributes"]
    for key, label in (("purchase_price", "Prix d'achat"), ("sell_price", "Prix de vente")):
        if key in d:
            setattr(p, key, to_int(d[key], label, 0))
    if "alert_threshold" in d:
        p.alert_threshold = to_int(d["alert_threshold"], "Seuil d'alerte", 0)
    if "category_id" in d:
        p.category_id = to_int(d["category_id"], "Catégorie", 1) if d["category_id"] else None
    if "supplier_id" in d:
        p.supplier_id = to_int(d["supplier_id"], "Fournisseur", 1) if d["supplier_id"] else None
    if "is_active" in d:
        p.is_active = bool(d["is_active"])


@bp.post("/products")
@require_permission("products.write")
def create_product():
    d = body()
    p = Product(code=numbering.code("PRD"), stock_qty=0)
    _product_fields(d, p, creating=True)
    db.session.add(p)
    db.session.flush()
    qty = to_int(d.get("initial_qty", 0), "Quantité initiale", 0)
    if qty:
        stock.apply_movement(p.id, "ENTREE", qty, g.user, "Stock initial", "product", p.id)
    audit.log(g.user, "PRODUIT_CREE", "product", p.code, {"nom": p.name, "stock_initial": qty})
    db.session.commit()
    return jsonify(product_dict(p)), 201


@bp.get("/products/<int:pid>")
@require_permission("products.read", "stock.read")
def get_product(pid):
    p = db.session.get(Product, pid)
    if not p:
        raise ApiError("Produit introuvable", 404)
    return jsonify(product_dict(p))


@bp.patch("/products/<int:pid>")
@require_permission("products.write")
def update_product(pid):
    d, p = body(), db.session.get(Product, pid)
    if not p:
        raise ApiError("Produit introuvable", 404)
    if "stock_qty" in d:
        raise ApiError("Le stock ne se modifie que par mouvement (arrivage, correction, inventaire)")
    before = product_dict(p)
    _product_fields(d, p)
    db.session.flush()
    after = product_dict(p)
    diff = {k: {"avant": before[k], "apres": after[k]} for k in after if before[k] != after[k]}
    if diff:
        audit.log(g.user, "PRODUIT_MODIFIE", "product", p.code, diff)
    db.session.commit()
    return jsonify(after)


@bp.delete("/products/<int:pid>")
@require_permission("products.write")
def deactivate_product(pid):
    p = db.session.get(Product, pid)
    if not p:
        raise ApiError("Produit introuvable", 404)
    p.is_active = False  # désactivation logique : l'historique reste intact
    audit.log(g.user, "PRODUIT_DESACTIVE", "product", p.code)
    db.session.commit()
    return jsonify(product_dict(p))


@bp.post("/uploads/image")
@require_permission("products.write", "settings.write")
def upload_image():
    f = request.files.get("file")
    if not f:
        raise ApiError("Fichier manquant")
    return jsonify(url=storage.save_image(f, request.args.get("folder", "products")))


@bp.get("/files/<path:key>")
def local_file(key):
    if current_app.config["STORAGE_BACKEND"] != "local":
        raise ApiError("Introuvable", 404)
    return send_from_directory(current_app.config["UPLOAD_DIR"], key)


# ---------- clients & fournisseurs ----------
def party_dict(x):
    return {"id": x.id, "code": x.code, "name": x.name, "phone": x.phone, "address": x.address,
            "notes": x.notes, "is_active": x.is_active, "created_at": iso(x.created_at)}


def register_party(path, model, prefix, perm_r, perm_w, audit_name):
    def listing():
        stmt = select(model)
        q = request.args.get("q")
        if q:
            stmt = stmt.where(or_(model.name.ilike(like(q)), model.phone.ilike(like(q)), model.code.ilike(like(q))))
        if request.args.get("active", "1") == "1":
            stmt = stmt.where(model.is_active.is_(True))
        return jsonify(paginate(stmt.order_by(model.name, model.id), party_dict))

    def create():
        d = body()
        x = model(code=numbering.code(prefix), name=text(d, "name", "Nom", True, 150), phone=text(d, "phone", "Téléphone", False, 40),
                  address=text(d, "address", "Adresse", False, 255), notes=text(d, "notes", "Notes", False, 2000))
        db.session.add(x)
        audit.log(g.user, f"{audit_name}_CREE", path, x.code, {"nom": x.name})
        db.session.commit()
        return jsonify(party_dict(x)), 201

    def update(xid):
        d, x = body(), db.session.get(model, xid)
        if not x:
            raise ApiError("Introuvable", 404)
        before = party_dict(x)
        for key, label, ln in (("name", "Nom", 150), ("phone", "Téléphone", 40), ("address", "Adresse", 255), ("notes", "Notes", 2000)):
            if key in d:
                setattr(x, key, text(d, key, label, key == "name", ln))
        if "is_active" in d:
            x.is_active = bool(d["is_active"])
        db.session.flush()
        after = party_dict(x)
        diff = {k: {"avant": before[k], "apres": after[k]} for k in after if before[k] != after[k]}
        if diff:
            audit.log(g.user, f"{audit_name}_MODIFIE", path, x.code, diff)
        db.session.commit()
        return jsonify(after)

    def detail(xid):
        x = db.session.get(model, xid)
        if not x:
            raise ApiError("Introuvable", 404)
        out = party_dict(x)
        if model is Customer:
            cnt, total = db.session.execute(select(func.count(), func.coalesce(func.sum(Sale.total), 0))
                                            .where(Sale.customer_id == x.id, Sale.status == "VALIDEE")).one()
            recent = db.session.execute(select(Sale).where(Sale.customer_id == x.id).order_by(Sale.created_at.desc()).limit(10)).scalars().all()
            out.update(purchases_count=cnt, total_spent=int(total),
                       recent_sales=[{"code": s.code, "total": s.total, "status": s.status, "date": iso(s.created_at),
                                      "invoice": s.invoice.number if s.invoice else None} for s in recent])
        else:
            arr = db.session.execute(select(Purchase).where(Purchase.supplier_id == x.id).order_by(Purchase.arrival_date.desc()).limit(20)).scalars().all()
            out["arrivals"] = [{"id": a.id, "code": a.code, "date": a.arrival_date.isoformat(), "total": a.total} for a in arr]
        return jsonify(out)

    bp.add_url_rule(f"/{path}", f"{path}_list", require_permission(perm_r)(listing), methods=["GET"])
    bp.add_url_rule(f"/{path}", f"{path}_create", require_permission(perm_w)(create), methods=["POST"])
    bp.add_url_rule(f"/{path}/<int:xid>", f"{path}_get", require_permission(perm_r)(detail), methods=["GET"])
    bp.add_url_rule(f"/{path}/<int:xid>", f"{path}_patch", require_permission(perm_w)(update), methods=["PATCH"])


register_party("customers", Customer, "CLI", "customers.read", "customers.write", "CLIENT")
register_party("suppliers", Supplier, "FRN", "suppliers.read", "suppliers.write", "FOURNISSEUR")
