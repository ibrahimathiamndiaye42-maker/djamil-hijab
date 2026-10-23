import os, random
import click
from sqlalchemy import select, text
from werkzeug.security import generate_password_hash
from .constants import DEFAULT_CATEGORIES, EMPLOYEE_DEFAULTS, PERMISSIONS, DEFAULT_SETTINGS
from .extensions import db
from .models import Category, Permission, Role, Setting, User, Product, Customer
from .services import audit, numbering, stock

TRIGGERS = os.path.join(os.path.dirname(os.path.dirname(__file__)), "triggers.sql")


def _bootstrap():
    perms = {}
    for code, label in PERMISSIONS.items():
        p = db.session.execute(select(Permission).where(Permission.code == code)).scalar_one_or_none() or Permission(code=code)
        p.label = label
        db.session.add(p)
        perms[code] = p
    for name in ("ADMIN", "EMPLOYE"):
        if not db.session.execute(select(Role).where(Role.name == name)).scalar_one_or_none():
            db.session.add(Role(name=name))
    db.session.flush()
    emp = db.session.execute(select(Role).where(Role.name == "EMPLOYE")).scalar_one()
    emp.permissions = [perms[c] for c in EMPLOYEE_DEFAULTS]
    for k, v in DEFAULT_SETTINGS.items():
        if not db.session.get(Setting, k):
            db.session.add(Setting(key=k, value=v))
    for name in DEFAULT_CATEGORIES:
        if not db.session.execute(select(Category).where(Category.name == name)).scalar_one_or_none():
            db.session.add(Category(name=name))
    db.session.commit()


def register(app):
    @app.cli.command("init-db")
    def init_db():
        """Crée les tables, applique les triggers PostgreSQL et initialise rôles/permissions/paramètres."""
        db.create_all()
        if db.engine.dialect.name == "postgresql":
            with open(TRIGGERS, encoding="utf-8") as f:
                db.session.execute(text(f.read()))
            db.session.commit()
        _bootstrap()
        click.echo("Base initialisée (base propre, sans données de démonstration).")

    @app.cli.command("apply-triggers")
    def apply_triggers():
        """Réapplique triggers.sql (à lancer après `flask db upgrade` si vous utilisez Alembic)."""
        with open(TRIGGERS, encoding="utf-8") as f:
            db.session.execute(text(f.read()))
        db.session.commit()
        click.echo("Triggers et index de recherche appliqués.")

    @app.cli.command("create-admin")
    @click.option("--username", prompt=True)
    @click.option("--full-name", prompt=True)
    @click.password_option()
    def create_admin(username, full_name, password):
        """Crée le premier compte administrateur."""
        _bootstrap()
        if len(password) < 8:
            raise click.ClickException("Mot de passe : 8 caractères minimum")
        role = db.session.execute(select(Role).where(Role.name == "ADMIN")).scalar_one()
        u = User(username=username.lower(), full_name=full_name, role=role, password_hash=generate_password_hash(password))
        db.session.add(u)
        db.session.flush()
        audit.log(u, "ADMIN_CREE", "user", u.username)
        db.session.commit()
        click.echo(f"Administrateur « {username} » créé.")

    @app.cli.command("seed-dev")
    def seed_dev():
        """Données de TEST (refusé si APP_ENV=production)."""
        if app.config["APP_ENV"] == "production":
            raise click.ClickException("seed-dev est interdit en production")
        _bootstrap()
        admin = db.session.execute(select(User).where(User.is_active.is_(True))).scalars().first()
        if not admin:
            raise click.ClickException("Créez d'abord un administrateur (flask create-admin)")
        cats = db.session.execute(select(Category)).scalars().all()
        for i in range(1, 31):
            p = Product(code=numbering.code("PRD"), name=f"Produit test {i}", category_id=random.choice(cats).id,
                        purchase_price=random.randint(2, 8) * 1000, sell_price=random.randint(9, 20) * 1000, alert_threshold=5)
            db.session.add(p)
            db.session.flush()
            stock.apply_movement(p.id, "ENTREE", random.randint(10, 60), admin, "Stock initial (test)", "seed")
        db.session.add(Customer(code=numbering.code("CLI"), name="Cliente test", phone="770000000"))
        db.session.commit()
        click.echo("30 produits de test créés.")
