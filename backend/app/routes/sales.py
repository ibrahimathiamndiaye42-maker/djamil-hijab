from flask import Blueprint, g, jsonify, request, send_file
from io import BytesIO
from sqlalchemy import select, or_
from ..auth import has_perm, require_permission
from ..errors import ApiError
from ..extensions import db
from ..models import Customer, CreditNote, Invoice, Payment, Sale, SaleItem
from ..services import audit, numbering, stock
from ..services.pdf import build_invoice_pdf
from ..services.settings import get_settings
from ..utils import body, like, paginate, parse_day, text, to_int, iso

bp = Blueprint("sales", __name__)


def sale_dict(s, full=False):
    out = {"id": s.id, "code": s.code, "invoice_id": s.invoice.id if s.invoice else None,
           "invoice": s.invoice.number if s.invoice else None, "invoice_status": s.invoice.status if s.invoice else None,
           "customer": s.customer.name if s.customer else None, "customer_id": s.customer_id,
           "user": s.user.full_name, "user_id": s.user_id, "subtotal": s.subtotal, "discount": s.discount,
           "total": s.total, "paid": s.paid, "rest": s.total - s.paid, "status": s.status,
           "payment_status": s.payment_status, "created_at": iso(s.created_at)}
    if full:
        out["items"] = [{"product_id": i.product_id, "name": i.product_name, "qty": i.qty, "unit_price": i.unit_price,
                         "line_total": i.line_total} for i in s.items]
        out["payments"] = [{"method": p.method, "amount": p.amount, "date": iso(p.created_at)} for p in s.payments]
    return out


def _pay_status(total, paid):
    return "PAYEE" if paid >= total else ("PARTIELLE" if paid > 0 else "IMPAYEE")


def _parse_payments(raw):
    methods = get_settings()["payment_methods"]
    out = []
    for p in raw or []:
        amount = to_int(p.get("amount"), "Montant payé", 0)
        if p.get("method") not in methods:
            raise ApiError(f"Mode de paiement invalide : {p.get('method')}")
        if amount:
            out.append((p["method"], amount))
    return out


@bp.post("/sales")
@require_permission("sales.create")
def create_sale():
    d = body()
    items = d.get("items") or []
    if not items:
        raise ApiError("Le panier est vide")
    lines = {}
    for it in items:
        pid, qty = to_int(it.get("product_id"), "Produit", 1), to_int(it.get("qty"), "Quantité", 1)
        lines[pid] = {"qty": lines.get(pid, {}).get("qty", 0) + qty, "price": it.get("unit_price")}
    # verrouillage dans un ordre fixe (évite les blocages croisés)
    products = {pid: stock.lock_product(pid) for pid in sorted(lines)}
    subtotal, shortages = 0, []
    for pid, l in lines.items():
        p = products[pid]
        if not p.is_active:
            raise ApiError(f"Produit désactivé : {p.name}")
        if l["price"] is not None and to_int(l["price"], "Prix", 0) != p.sell_price:
            if not has_perm("products.write"):
                raise ApiError("Vous n'êtes pas autorisé à modifier le prix de vente", 403)
            l["price"] = to_int(l["price"], "Prix", 0)
        else:
            l["price"] = p.sell_price
        if p.stock_qty < l["qty"]:
            shortages.append(f"« {p.name} » : disponible {p.stock_qty}, demandé {l['qty']}")
        subtotal += l["price"] * l["qty"]
    if shortages:
        raise ApiError("Stock insuffisant. " + " ; ".join(shortages), 409)
    discount = to_int(d.get("discount", 0), "Remise", 0)
    if discount > subtotal:
        raise ApiError("La remise dépasse le sous-total")
    total = subtotal - discount
    payments = _parse_payments(d.get("payments"))
    paid = sum(a for _, a in payments)
    if paid > total:
        raise ApiError("Le montant payé dépasse le total")
    cid = to_int(d["customer_id"], "Client", 1) if d.get("customer_id") else None
    if cid and not db.session.get(Customer, cid):
        raise ApiError("Client introuvable", 404)
    if paid < total and not cid:
        raise ApiError("Un client est requis pour une vente avec un reste à payer")
    sale = Sale(code=numbering.code("VTE", yearly=True), customer_id=cid, user_id=g.user.id, subtotal=subtotal,
                discount=discount, total=total, paid=paid, payment_status=_pay_status(total, paid))
    db.session.add(sale)
    db.session.flush()
    for pid, l in lines.items():
        p = products[pid]
        db.session.add(SaleItem(sale_id=sale.id, product_id=pid, product_name=p.name, qty=l["qty"],
                                unit_price=l["price"], line_total=l["price"] * l["qty"]))
        stock.apply_movement(pid, "VENTE", -l["qty"], g.user, None, "sale", sale.id)
    for method, amount in payments:
        db.session.add(Payment(sale_id=sale.id, method=method, amount=amount, user_id=g.user.id))
    inv = Invoice(number=numbering.code("FAC", yearly=True), sale_id=sale.id, user_id=g.user.id)
    db.session.add(inv)
    audit.log(g.user, "VENTE_CREEE", "invoice", inv.number, {"vente": sale.code, "total": total, "lignes": len(lines)})
    db.session.commit()
    db.session.refresh(sale)
    return jsonify(sale_dict(sale, True)), 201


def _visible(stmt):
    return stmt if has_perm("sales.read_all") else stmt.where(Sale.user_id == g.user.id)


@bp.get("/sales")
@require_permission("sales.read", "sales.read_all")
def list_sales():
    a = request.args
    stmt = _visible(select(Sale))
    if a.get("date_from"):
        stmt = stmt.where(Sale.created_at >= parse_day(a["date_from"]))
    if a.get("date_to"):
        stmt = stmt.where(Sale.created_at < parse_day(a["date_to"], end=True))
    return jsonify(paginate(stmt.order_by(Sale.created_at.desc(), Sale.id.desc()), sale_dict))


@bp.get("/invoices")
@require_permission("sales.read", "sales.read_all")
def list_invoices():
    a = request.args
    stmt = _visible(select(Invoice).join(Sale, Sale.id == Invoice.sale_id).outerjoin(Customer, Customer.id == Sale.customer_id))
    if a.get("q"):
        q = like(a["q"])
        stmt = stmt.where(or_(Invoice.number.ilike(q), Customer.name.ilike(q), Customer.phone.ilike(q)))
    if a.get("date_from"):
        stmt = stmt.where(Invoice.issued_at >= parse_day(a["date_from"]))
    if a.get("date_to"):
        stmt = stmt.where(Invoice.issued_at < parse_day(a["date_to"], end=True))
    if a.get("customer_id"):
        stmt = stmt.where(Sale.customer_id == to_int(a["customer_id"], "Client"))
    if a.get("user_id"):
        stmt = stmt.where(Sale.user_id == to_int(a["user_id"], "Employé"))
    if a.get("min_amount"):
        stmt = stmt.where(Sale.total >= to_int(a["min_amount"], "Montant min"))
    if a.get("max_amount"):
        stmt = stmt.where(Sale.total <= to_int(a["max_amount"], "Montant max"))
    return jsonify(paginate(stmt.order_by(Invoice.issued_at.desc(), Invoice.id.desc()), lambda i: sale_dict(i.sale)))


def _get_invoice(iid):
    inv = db.session.get(Invoice, iid)
    if not inv or (not has_perm("sales.read_all") and inv.sale.user_id != g.user.id):
        raise ApiError("Facture introuvable", 404)
    return inv


@bp.get("/invoices/<int:iid>")
@require_permission("sales.read", "sales.read_all")
def get_invoice(iid):
    return jsonify(sale_dict(_get_invoice(iid).sale, True))


@bp.get("/invoices/<int:iid>/pdf")
@require_permission("sales.read", "sales.read_all")
def invoice_pdf(iid):
    inv = _get_invoice(iid)
    data = build_invoice_pdf(inv, get_settings())
    return send_file(BytesIO(data), mimetype="application/pdf", download_name=f"{inv.number}.pdf")


@bp.post("/sales/<int:sid>/payments")
@require_permission("sales.create")
def add_payment(sid):
    sale = db.session.get(Sale, sid)
    if not sale or (not has_perm("sales.read_all") and sale.user_id != g.user.id):
        raise ApiError("Vente introuvable", 404)
    if sale.status != "VALIDEE":
        raise ApiError("Vente annulée")
    pays = _parse_payments([body()])
    if not pays:
        raise ApiError("Montant obligatoire")
    method, amount = pays[0]
    if sale.paid + amount > sale.total:
        raise ApiError("Le paiement dépasse le reste à payer")
    db.session.add(Payment(sale_id=sale.id, method=method, amount=amount, user_id=g.user.id))
    sale.paid += amount
    sale.payment_status = _pay_status(sale.total, sale.paid)
    audit.log(g.user, "PAIEMENT_AJOUTE", "invoice", sale.invoice.number, {"montant": amount, "mode": method})
    db.session.commit()
    return jsonify(sale_dict(sale, True))


@bp.post("/invoices/<int:iid>/cancel")
@require_permission("sales.cancel")
def cancel_invoice(iid):
    reason = text(body(), "reason", "Motif d'annulation", True, 500)
    inv = db.session.get(Invoice, iid)
    if not inv:
        raise ApiError("Facture introuvable", 404)
    if inv.status == "ANNULEE":
        raise ApiError("Facture déjà annulée", 409)
    sale = inv.sale
    for it in sorted(sale.items, key=lambda x: x.product_id):
        stock.apply_movement(it.product_id, "RETOUR_CLIENT", it.qty, g.user, f"Annulation {inv.number} : {reason}", "invoice", inv.id)
    inv.status, sale.status = "ANNULEE", "ANNULEE"
    db.session.add(CreditNote(number=numbering.code("AVR", yearly=True), invoice_id=inv.id, reason=reason, user_id=g.user.id))
    audit.log(g.user, "FACTURE_ANNULEE", "invoice", inv.number, {"motif": reason, "total": sale.total})
    db.session.commit()
    return jsonify(sale_dict(sale, True))
