import re
from sqlalchemy import select, func
from app.extensions import db
from app.models import AuditLog, StockMovement


def sell(client, headers, pid, qty, **extra):
    body = {"items": [{"product_id": pid, "qty": qty}], "payments": [{"method": "Espèces", "amount": 5000 * qty}]}
    body.update(extra)
    return client.post("/api/v1/sales", headers=headers, json=body)


def stock_of(client, admin, pid):
    return client.get(f"/api/v1/products/{pid}", headers=admin).get_json()["stock_qty"]


def test_auth_required_and_bad_login(client):
    assert client.get("/api/v1/products").status_code == 401
    assert client.post("/api/v1/auth/login", json={"username": "admin", "password": "faux"}).status_code == 401


def test_employee_forbidden_on_sensitive_routes(client, awa, product):
    assert client.post("/api/v1/products", headers=awa, json={"name": "X"}).status_code == 403
    assert client.get("/api/v1/audit", headers=awa).status_code == 403
    assert client.get("/api/v1/users", headers=awa).status_code == 403
    assert client.post("/api/v1/stock/adjust", headers=awa, json={"type": "CORRECTION", "product_id": product["id"], "qty": -1, "reason": "x"}).status_code == 403
    assert client.get("/api/v1/dashboard", headers=awa).status_code == 403


def test_product_creation_generates_code_and_initial_movement(client, admin, product):
    assert product["code"] == "PRD-000001" and product["stock_qty"] == 10
    mv = client.get("/api/v1/stock/movements", headers=admin).get_json()
    assert mv["total"] == 1 and mv["items"][0]["type"] == "ENTREE" and mv["items"][0]["qty_after"] == 10


def test_stock_cannot_be_edited_directly(client, admin, product):
    r = client.patch(f"/api/v1/products/{product['id']}", headers=admin, json={"stock_qty": 99})
    assert r.status_code == 400


def test_sale_decreases_stock_creates_movement_invoice_and_audit(client, admin, awa, product):
    r = sell(client, awa, product["id"], 3)
    assert r.status_code == 201, r.get_json()
    s = r.get_json()
    assert re.match(r"FAC-\d{4}-000001", s["invoice"]) and s["total"] == 15000 and s["payment_status"] == "PAYEE"
    assert stock_of(client, admin, product["id"]) == 7
    mv = client.get("/api/v1/stock/movements?type=VENTE", headers=admin).get_json()["items"][0]
    assert mv["qty_delta"] == -3 and mv["user"] == "Awa" and mv["qty_before"] == 10
    logs = client.get("/api/v1/audit?q=Awa", headers=admin).get_json()["items"]
    assert any(l["action"] == "VENTE_CREEE" for l in logs)


def test_insufficient_stock_blocks_sale_atomically(client, admin, awa, product):
    r = sell(client, awa, product["id"], 11)
    assert r.status_code == 409 and "Stock insuffisant" in r.get_json()["error"]
    assert stock_of(client, admin, product["id"]) == 10
    assert client.get("/api/v1/sales", headers=admin).get_json()["total"] == 0


def test_partial_payment_requires_customer(client, awa, product):
    r = sell(client, awa, product["id"], 1, payments=[{"method": "Wave", "amount": 1000}])
    assert r.status_code == 400


def test_invoice_pdf_and_cancel_flow(client, admin, awa, product):
    s = sell(client, awa, product["id"], 2).get_json()
    pdf = client.get(f"/api/v1/invoices/{s['invoice_id']}/pdf", headers=awa)
    assert pdf.status_code == 200 and pdf.data.startswith(b"%PDF")
    assert client.post(f"/api/v1/invoices/{s['invoice_id']}/cancel", headers=awa, json={"reason": "erreur"}).status_code == 403
    assert client.post(f"/api/v1/invoices/{s['invoice_id']}/cancel", headers=admin, json={}).status_code == 400
    r = client.post(f"/api/v1/invoices/{s['invoice_id']}/cancel", headers=admin, json={"reason": "erreur de saisie"})
    assert r.status_code == 200 and r.get_json()["status"] == "ANNULEE"
    assert stock_of(client, admin, product["id"]) == 10
    assert client.post(f"/api/v1/invoices/{s['invoice_id']}/cancel", headers=admin, json={"reason": "bis"}).status_code == 409


def test_employee_sees_only_own_invoices(client, admin, awa, fatou, product):
    sell(client, awa, product["id"], 1)
    sell(client, fatou, product["id"], 1)
    assert client.get("/api/v1/invoices", headers=awa).get_json()["total"] == 1
    assert client.get("/api/v1/invoices", headers=admin).get_json()["total"] == 2


def test_correction_requires_reason_and_is_traced(client, admin, product):
    body = {"type": "CORRECTION", "product_id": product["id"], "qty": -2}
    assert client.post("/api/v1/stock/adjust", headers=admin, json=body).status_code == 400
    r = client.post("/api/v1/stock/adjust", headers=admin, json={**body, "reason": "produit manquant"})
    assert r.status_code == 201 and r.get_json()["qty_after"] == 8
    assert stock_of(client, admin, product["id"]) == 8
    assert client.get("/api/v1/audit?q=PRD", headers=admin).get_json()["items"][0]["action"] == "CORRECTION_STOCK"


def test_arrival_increases_stock_and_updates_cost(client, admin, product):
    r = client.post("/api/v1/arrivals", headers=admin, json={"items": [{"product_id": product["id"], "qty": 50, "unit_cost": 3200}]})
    assert r.status_code == 201 and r.get_json()["total"] == 160000 and r.get_json()["code"] == "ARR-000001"
    assert stock_of(client, admin, product["id"]) == 60


def test_inventory_gap_needs_reason_and_shows_in_control(client, admin, awa, product):
    body = {"items": [{"product_id": product["id"], "counted": 8}]}
    assert client.post("/api/v1/inventories", headers=admin, json=body).status_code == 400
    body["items"][0]["reason"] = "casse"
    assert client.post("/api/v1/inventories", headers=admin, json=body).status_code == 201
    assert stock_of(client, admin, product["id"]) == 8
    gap = client.get("/api/v1/control/gaps", headers=admin).get_json()["items"][0]
    assert (gap["theoretical"], gap["counted"], gap["diff"]) == (10, 8, -2)


def test_logs_and_movements_have_no_delete_route(client, admin, product):
    for url in ("/api/v1/audit", "/api/v1/stock/movements", f"/api/v1/audit/1"):
        assert client.delete(url, headers=admin).status_code in (404, 405)


def test_pagination_is_bounded(client, admin, product):
    r = client.get("/api/v1/products?per_page=100000", headers=admin).get_json()
    assert r["per_page"] == 100


def test_deactivated_user_loses_access(client, admin, awa):
    uid = [u for u in client.get("/api/v1/users", headers=admin).get_json() if u["username"] == "awa"][0]["id"]
    assert client.patch(f"/api/v1/users/{uid}", headers=admin, json={"is_active": False}).status_code == 200
    assert client.get("/api/v1/products", headers=awa).status_code == 401
