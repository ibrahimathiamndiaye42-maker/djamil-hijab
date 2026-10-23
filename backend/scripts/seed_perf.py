"""Remplit une base de TEST avec un gros volume pour vérifier les performances.
Usage : python scripts/seed_perf.py --products 5000 --customers 5000 --sales 100000
NE JAMAIS lancer sur la base de production."""
import argparse, os, random, sys, time
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from datetime import timedelta
from sqlalchemy import select, text
from app import create_app
from app.extensions import db
from app.models import Customer, Invoice, Product, Sale, SaleItem, StockMovement, User, now

ap = argparse.ArgumentParser()
ap.add_argument("--products", type=int, default=5000)
ap.add_argument("--customers", type=int, default=5000)
ap.add_argument("--sales", type=int, default=100000)
a = ap.parse_args()
app = create_app()
if app.config["APP_ENV"] == "production":
    sys.exit("Refusé en production")
with app.app_context():
    uid = db.session.execute(select(User.id)).scalars().first()
    if not uid:
        sys.exit("Créez un admin d'abord")
    t0 = time.time()
    db.session.bulk_insert_mappings(Product, [dict(code=f"PRF-{i:07d}", name=f"Voile perf {i}", reference=f"REF{i}", purchase_price=3000,
                                                   sell_price=5000, stock_qty=10**6, alert_threshold=5, is_active=True) for i in range(a.products)])
    db.session.bulk_insert_mappings(Customer, [dict(code=f"CLP-{i:07d}", name=f"Cliente {i}", phone=f"77{random.randint(1000000, 9999999)}", is_active=True) for i in range(a.customers)])
    db.session.commit()
    pids = list(db.session.execute(select(Product.id).where(Product.code.like("PRF-%"))).scalars())
    names = dict(db.session.execute(select(Product.id, Product.name).where(Product.code.like("PRF-%"))).all())
    cids = list(db.session.execute(select(Customer.id).where(Customer.code.like("CLP-%"))).scalars())
    base, B, mv = now(), 5000, 0
    for start in range(0, a.sales, B):
        sales = [dict(code=f"VPF-{start + i:08d}", customer_id=random.choice(cids), user_id=uid, subtotal=5000, discount=0, total=5000, paid=5000,
                      status="VALIDEE", payment_status="PAYEE", created_at=base - timedelta(minutes=random.randint(0, 60 * 24 * 900)))
                 for i in range(min(B, a.sales - start))]
        db.session.bulk_insert_mappings(Sale, sales, return_defaults=True)
        items, movs, invs = [], [], []
        for s in sales:
            pid = random.choice(pids)
            items.append(dict(sale_id=s["id"], product_id=pid, product_name=names[pid], qty=1, unit_price=5000, line_total=5000))
            mv += 1
            movs.append(dict(code=f"MVP-{mv:09d}", product_id=pid, type="VENTE", qty_before=100, qty_delta=-1, qty_after=99, user_id=uid, source_type="sale", source_id=s["id"], created_at=s["created_at"]))
            invs.append(dict(number=f"FPF-{s['id']:09d}", sale_id=s["id"], status="VALIDEE", issued_at=s["created_at"], user_id=uid))
        db.session.bulk_insert_mappings(SaleItem, items); db.session.bulk_insert_mappings(StockMovement, movs); db.session.bulk_insert_mappings(Invoice, invs)
        db.session.commit()
        print(f"{start + len(sales)} ventes...", flush=True)
    print(f"Insertion : {time.time() - t0:.1f}s")
    if db.engine.dialect.name == "postgresql":
        db.session.execute(text("ANALYZE")); db.session.commit()
    c = app.test_client()
    from app.auth import make_token
    with app.test_request_context():
        tok = make_token(db.session.get(User, uid))
    H = {"Authorization": "Bearer " + tok}
    for label, url in (("Factures p.1", "/api/v1/invoices"), ("Recherche facture", "/api/v1/invoices?q=FPF-000000452"),
                       ("Recherche produit", "/api/v1/products?q=Voile%20perf%204"), ("Mouvements", "/api/v1/stock/movements"),
                       ("Dashboard", "/api/v1/dashboard"), ("Clients", "/api/v1/customers?q=Cliente%2012")):
        t = time.time(); r = c.get(url, headers=H); print(f"{label:20s} {r.status_code}  {(time.time() - t) * 1000:7.1f} ms")
    print("Pour nettoyer la base de test : supprimez-la et relancez `flask init-db`.")
