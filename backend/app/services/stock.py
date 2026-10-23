from sqlalchemy import select
from ..constants import MOVEMENT_SIGN, REASON_REQUIRED
from ..errors import ApiError
from ..extensions import db
from ..models import Product, StockMovement
from . import numbering


def lock_product(pid):
    """Verrouille la ligne produit (SELECT ... FOR UPDATE) pour éviter les ventes simultanées."""
    stmt = (select(Product).where(Product.id == pid).with_for_update(of=Product)
            .execution_options(populate_existing=True))
    p = db.session.execute(stmt).unique().scalar_one_or_none()
    if p is None:
        raise ApiError("Produit introuvable", 404)
    return p


def apply_movement(product_id, mtype, delta, user, reason=None, source_type=None, source_id=None):
    """SEUL point d'entrée pour modifier le stock. Écrit un mouvement immuable dans la même transaction."""
    if mtype not in MOVEMENT_SIGN:
        raise ApiError("Type de mouvement invalide")
    if delta == 0:
        raise ApiError("La quantité ne peut pas être nulle")
    sign = MOVEMENT_SIGN[mtype]
    if sign and (delta > 0) != (sign > 0):
        raise ApiError(f"Quantité de signe incorrect pour « {mtype} »")
    reason = (reason or "").strip() or None
    if mtype in REASON_REQUIRED and not reason:
        raise ApiError("Un motif est obligatoire pour ce type de mouvement")
    p = lock_product(product_id)
    before, after = p.stock_qty, p.stock_qty + delta
    if after < 0:
        raise ApiError(f"Stock insuffisant pour « {p.name} ». Disponible : {before} — Demandé : {-delta}", 409,
                       product_id=p.id, available=before, requested=-delta)
    p.stock_qty = after
    m = StockMovement(code=numbering.code("MVT"), product_id=p.id, type=mtype, qty_before=before,
                      qty_delta=delta, qty_after=after, reason=reason, source_type=source_type,
                      source_id=source_id, user_id=user.id)
    db.session.add(m)
    db.session.flush()
    return m
