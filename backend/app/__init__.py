from flask import Flask, jsonify
from sqlalchemy.exc import IntegrityError
from werkzeug.exceptions import HTTPException
from .config import Config
from .errors import ApiError
from .extensions import cors, db, migrate


def create_app(config=None):
    app = Flask(__name__)
    app.config.from_object(Config)
    if config:
        app.config.update(config)
    db.init_app(app)
    from . import models  # noqa: F401
    migrate.init_app(app, db)
    cors.init_app(app, resources={r"/*": {"origins": app.config["CORS_ORIGINS"]}})

    from .routes import auth_users, catalog, control, sales, stock
    for m in (auth_users, catalog, control, sales, stock):
        app.register_blueprint(m.bp, url_prefix="/api/v1")
    from . import cli
    cli.register(app)

    @app.get("/api/v1/health")
    def health():
        return jsonify(status="ok")

    @app.errorhandler(ApiError)
    def api_error(e):
        db.session.rollback()
        return jsonify(error=e.message, **e.extra), e.status

    @app.errorhandler(IntegrityError)
    def integrity(e):
        db.session.rollback()
        app.logger.warning("IntegrityError: %s", e)
        return jsonify(error="Opération refusée : conflit avec des données existantes"), 409

    @app.errorhandler(HTTPException)
    def http_error(e):
        return jsonify(error=e.description), e.code

    @app.errorhandler(Exception)
    def unexpected(e):
        db.session.rollback()
        app.logger.exception(e)
        return jsonify(error="Erreur interne du serveur"), 500

    return app
