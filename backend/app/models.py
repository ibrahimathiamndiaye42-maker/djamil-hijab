from datetime import datetime, timezone
from .extensions import db
from .constants import PERMISSIONS


def now():
    return datetime.now(timezone.utc)


BigPK = db.BigInteger().with_variant(db.Integer, "sqlite")
DT = db.DateTime(timezone=True)

role_permissions = db.Table(
    "role_permissions",
    db.Column("role_id", db.Integer, db.ForeignKey("roles.id"), primary_key=True),
    db.Column("permission_id", db.Integer, db.ForeignKey("permissions.id"), primary_key=True))
user_permissions = db.Table(
    "user_permissions",
    db.Column("user_id", db.BigInteger, db.ForeignKey("users.id"), primary_key=True),
    db.Column("permission_id", db.Integer, db.ForeignKey("permissions.id"), primary_key=True))


class Role(db.Model):
    __tablename__ = "roles"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(30), unique=True, nullable=False)
    permissions = db.relationship("Permission", secondary=role_permissions, lazy="selectin")


class Permission(db.Model):
    __tablename__ = "permissions"
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(60), unique=True, nullable=False)
    label = db.Column(db.String(200))


class User(db.Model):
    __tablename__ = "users"
    id = db.Column(BigPK, primary_key=True)
    username = db.Column(db.String(60), unique=True, nullable=False)
    full_name = db.Column(db.String(120), nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role_id = db.Column(db.Integer, db.ForeignKey("roles.id"), nullable=False)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(DT, default=now)
    last_login = db.Column(DT)
    role = db.relationship("Role", lazy="joined")
    extra_permissions = db.relationship("Permission", secondary=user_permissions, lazy="selectin")

    @property
    def is_admin(self):
        return self.role.name == "ADMIN"

    def permission_codes(self):
        if self.is_admin:
            return sorted(PERMISSIONS)
        return sorted({p.code for p in self.role.permissions} | {p.code for p in self.extra_permissions})


class Category(db.Model):
    __tablename__ = "categories"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True, nullable=False)
    is_active = db.Column(db.Boolean, nullable=False, default=True)


class Supplier(db.Model):
    __tablename__ = "suppliers"
    id = db.Column(BigPK, primary_key=True)
    code = db.Column(db.String(20), unique=True, nullable=False)
    name = db.Column(db.String(150), nullable=False, index=True)
    phone = db.Column(db.String(40), index=True)
    address = db.Column(db.String(255))
    notes = db.Column(db.Text)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(DT, default=now)


class Customer(db.Model):
    __tablename__ = "customers"
    id = db.Column(BigPK, primary_key=True)
    code = db.Column(db.String(20), unique=True, nullable=False)
    name = db.Column(db.String(150), nullable=False, index=True)
    phone = db.Column(db.String(40), index=True)
    address = db.Column(db.String(255))
    notes = db.Column(db.Text)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(DT, default=now, index=True)


class Product(db.Model):
    __tablename__ = "products"
    id = db.Column(BigPK, primary_key=True)
    code = db.Column(db.String(20), unique=True, nullable=False)
    name = db.Column(db.String(200), nullable=False, index=True)
    reference = db.Column(db.String(80), index=True)
    category_id = db.Column(db.Integer, db.ForeignKey("categories.id"), index=True)
    subcategory = db.Column(db.String(80))
    description = db.Column(db.Text)
    color = db.Column(db.String(60))
    size = db.Column(db.String(40))
    attributes = db.Column(db.JSON)  # champs libres (matière, modèle, etc.)
    purchase_price = db.Column(db.BigInteger, nullable=False, default=0)
    sell_price = db.Column(db.BigInteger, nullable=False, default=0)
    stock_qty = db.Column(db.Integer, nullable=False, default=0)  # dérivé : modifié UNIQUEMENT via services.stock
    alert_threshold = db.Column(db.Integer, nullable=False, default=5)
    photo_url = db.Column(db.String(500))
    supplier_id = db.Column(db.BigInteger, db.ForeignKey("suppliers.id"))
    is_active = db.Column(db.Boolean, nullable=False, default=True, index=True)
    created_at = db.Column(DT, default=now)
    updated_at = db.Column(DT, default=now, onupdate=now)
    category = db.relationship("Category", lazy="joined")
    supplier = db.relationship("Supplier", lazy="joined")
    __table_args__ = (db.CheckConstraint("stock_qty >= 0", name="ck_products_stock_nonneg"),
                      db.CheckConstraint("sell_price >= 0 AND purchase_price >= 0", name="ck_products_prices"))


class Purchase(db.Model):
    __tablename__ = "purchases"
    id = db.Column(BigPK, primary_key=True)
    code = db.Column(db.String(20), unique=True, nullable=False)
    supplier_id = db.Column(db.BigInteger, db.ForeignKey("suppliers.id"), index=True)
    arrival_date = db.Column(db.Date, nullable=False, index=True)
    notes = db.Column(db.Text)
    total = db.Column(db.BigInteger, nullable=False, default=0)
    user_id = db.Column(db.BigInteger, db.ForeignKey("users.id"), nullable=False)
    created_at = db.Column(DT, default=now)
    supplier = db.relationship("Supplier", lazy="joined")
    user = db.relationship("User", lazy="joined")
    items = db.relationship("PurchaseItem", lazy="selectin", cascade="all")


class PurchaseItem(db.Model):
    __tablename__ = "purchase_items"
    id = db.Column(BigPK, primary_key=True)
    purchase_id = db.Column(db.BigInteger, db.ForeignKey("purchases.id"), nullable=False, index=True)
    product_id = db.Column(db.BigInteger, db.ForeignKey("products.id"), nullable=False, index=True)
    qty = db.Column(db.Integer, nullable=False)
    unit_cost = db.Column(db.BigInteger, nullable=False)
    product = db.relationship("Product", lazy="joined")
    __table_args__ = (db.CheckConstraint("qty > 0", name="ck_purchase_items_qty"),)


class Sale(db.Model):
    __tablename__ = "sales"
    id = db.Column(BigPK, primary_key=True)
    code = db.Column(db.String(24), unique=True, nullable=False)
    customer_id = db.Column(db.BigInteger, db.ForeignKey("customers.id"), index=True)
    user_id = db.Column(db.BigInteger, db.ForeignKey("users.id"), nullable=False, index=True)
    subtotal = db.Column(db.BigInteger, nullable=False)
    discount = db.Column(db.BigInteger, nullable=False, default=0)
    total = db.Column(db.BigInteger, nullable=False, index=True)
    paid = db.Column(db.BigInteger, nullable=False, default=0)
    status = db.Column(db.String(12), nullable=False, default="VALIDEE")
    payment_status = db.Column(db.String(12), nullable=False, default="PAYEE")
    created_at = db.Column(DT, default=now, index=True)
    customer = db.relationship("Customer", lazy="joined")
    user = db.relationship("User", lazy="joined")
    items = db.relationship("SaleItem", lazy="selectin")
    payments = db.relationship("Payment", lazy="selectin")
    invoice = db.relationship("Invoice", uselist=False, lazy="joined", back_populates="sale")


class SaleItem(db.Model):
    __tablename__ = "sale_items"
    id = db.Column(BigPK, primary_key=True)
    sale_id = db.Column(db.BigInteger, db.ForeignKey("sales.id"), nullable=False, index=True)
    product_id = db.Column(db.BigInteger, db.ForeignKey("products.id"), nullable=False, index=True)
    product_name = db.Column(db.String(200), nullable=False)  # copie figée pour la facture
    qty = db.Column(db.Integer, nullable=False)
    unit_price = db.Column(db.BigInteger, nullable=False)
    line_total = db.Column(db.BigInteger, nullable=False)
    __table_args__ = (db.CheckConstraint("qty > 0", name="ck_sale_items_qty"),)


class Payment(db.Model):
    __tablename__ = "payments"
    id = db.Column(BigPK, primary_key=True)
    sale_id = db.Column(db.BigInteger, db.ForeignKey("sales.id"), nullable=False, index=True)
    method = db.Column(db.String(40), nullable=False)
    amount = db.Column(db.BigInteger, nullable=False)
    user_id = db.Column(db.BigInteger, db.ForeignKey("users.id"))
    created_at = db.Column(DT, default=now)


class Invoice(db.Model):
    __tablename__ = "invoices"
    id = db.Column(BigPK, primary_key=True)
    number = db.Column(db.String(24), unique=True, nullable=False)
    sale_id = db.Column(db.BigInteger, db.ForeignKey("sales.id"), unique=True, nullable=False)
    status = db.Column(db.String(12), nullable=False, default="VALIDEE", index=True)
    issued_at = db.Column(DT, default=now, index=True)
    user_id = db.Column(db.BigInteger, db.ForeignKey("users.id"), nullable=False)
    sale = db.relationship("Sale", back_populates="invoice", lazy="joined")


class CreditNote(db.Model):
    __tablename__ = "credit_notes"
    id = db.Column(BigPK, primary_key=True)
    number = db.Column(db.String(24), unique=True, nullable=False)
    invoice_id = db.Column(db.BigInteger, db.ForeignKey("invoices.id"), unique=True, nullable=False)
    reason = db.Column(db.Text, nullable=False)
    user_id = db.Column(db.BigInteger, db.ForeignKey("users.id"), nullable=False)
    created_at = db.Column(DT, default=now)


class StockMovement(db.Model):
    __tablename__ = "stock_movements"
    id = db.Column(BigPK, primary_key=True)
    code = db.Column(db.String(20), unique=True, nullable=False)
    product_id = db.Column(db.BigInteger, db.ForeignKey("products.id"), nullable=False)
    type = db.Column(db.String(24), nullable=False)
    qty_before = db.Column(db.Integer, nullable=False)
    qty_delta = db.Column(db.Integer, nullable=False)
    qty_after = db.Column(db.Integer, nullable=False)
    reason = db.Column(db.Text)
    source_type = db.Column(db.String(24))
    source_id = db.Column(db.BigInteger)
    user_id = db.Column(db.BigInteger, db.ForeignKey("users.id"), nullable=False)
    created_at = db.Column(DT, default=now)
    product = db.relationship("Product", lazy="joined")
    user = db.relationship("User", lazy="joined")
    __table_args__ = (db.Index("ix_mvt_product_date", "product_id", "created_at"),
                      db.Index("ix_mvt_user_date", "user_id", "created_at"),
                      db.Index("ix_mvt_type_date", "type", "created_at"),
                      db.Index("ix_mvt_date", "created_at"),
                      db.CheckConstraint("qty_delta <> 0", name="ck_mvt_delta"),
                      db.CheckConstraint("qty_after >= 0", name="ck_mvt_after"))


class Inventory(db.Model):
    __tablename__ = "inventories"
    id = db.Column(BigPK, primary_key=True)
    code = db.Column(db.String(20), unique=True, nullable=False)
    user_id = db.Column(db.BigInteger, db.ForeignKey("users.id"), nullable=False)
    notes = db.Column(db.Text)
    created_at = db.Column(DT, default=now, index=True)
    user = db.relationship("User", lazy="joined")
    items = db.relationship("InventoryItem", lazy="selectin", back_populates="inventory")


class InventoryItem(db.Model):
    __tablename__ = "inventory_items"
    id = db.Column(BigPK, primary_key=True)
    inventory_id = db.Column(db.BigInteger, db.ForeignKey("inventories.id"), nullable=False, index=True)
    product_id = db.Column(db.BigInteger, db.ForeignKey("products.id"), nullable=False, index=True)
    theoretical = db.Column(db.Integer, nullable=False)
    counted = db.Column(db.Integer, nullable=False)
    diff = db.Column(db.Integer, nullable=False, index=True)
    reason = db.Column(db.Text)
    product = db.relationship("Product", lazy="joined")
    inventory = db.relationship("Inventory", lazy="joined", back_populates="items")


class AuditLog(db.Model):
    __tablename__ = "audit_logs"
    id = db.Column(BigPK, primary_key=True)
    user_id = db.Column(db.BigInteger, db.ForeignKey("users.id"), index=True)
    user_name = db.Column(db.String(120))
    action = db.Column(db.String(40), nullable=False, index=True)
    entity_type = db.Column(db.String(30))
    entity_ref = db.Column(db.String(40), index=True)
    details = db.Column(db.JSON)
    created_at = db.Column(DT, default=now, index=True)


class Setting(db.Model):
    __tablename__ = "settings"
    key = db.Column(db.String(60), primary_key=True)
    value = db.Column(db.JSON)


class NumberSequence(db.Model):
    __tablename__ = "number_sequences"
    key = db.Column(db.String(40), primary_key=True)
    value = db.Column(db.BigInteger, nullable=False, default=0)
