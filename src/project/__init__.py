from datetime import timedelta
from uuid import uuid4

import sentry_sdk
from flask import Flask, g, session
from flask_login import current_user
from werkzeug.middleware.proxy_fix import ProxyFix

from .config import get_settings
from .extensions import csrf, db, login_manager, migrate
from .routes.admin import admin
from .routes.auth import auth
from .routes.claim import claim
from .routes.main import (
    bad_request,
    forbidden,
    internal_server_error,
    main,
    page_not_found,
    service_unavailable,
    unauthorized,
)
from .routes.search import search
from .routes.settings import settings


def create_app():
    cfg = get_settings()

    sentry_sdk.init(dsn=cfg.sentry_dsn, traces_sample_rate=0.25, profiles_sample_rate=0.1, attach_stacktrace=True)

    app = Flask(__name__)
    app.config["SQLALCHEMY_DATABASE_URI"] = cfg.database_url
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["SQLALCHEMY_POOL_SIZE"] = cfg.sqlalchemy_pool_size
    app.config["SQLALCHEMY_POOL_RECYCLE"] = cfg.sqlalchemy_pool_recycle
    app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {"pool_pre_ping": True}
    app.config["REMEMBER_COOKIE_DURATION"] = timedelta(days=30)
    app.secret_key = cfg.secret_key

    if cfg.is_testing:
        app.config["TESTING"] = True
        app.config["WTF_CSRF_ENABLED"] = False
        app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///test_db.sqlite"

    if app.config["DEBUG"] and not app.config["TESTING"]:
        app.config["DEBUG_TB_INTERCEPT_REDIRECTS"] = False
        app.config["SQLALCHEMY_RECORD_QUERIES"] = True
        app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = True
        # app.config["SQLALCHEMY_ECHO"] = True
        # app.config["DEBUG_TB_PROFILER_ENABLED"] = True
        # toolbar.init_app(app)

    else:
        # Reverse proxy support
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

    app.register_blueprint(auth)
    app.register_blueprint(main)
    app.register_blueprint(claim)
    app.register_blueprint(search)
    app.register_blueprint(settings, url_prefix="/settings")
    app.register_blueprint(admin, url_prefix="/admin")

    app.register_error_handler(400, bad_request)
    app.register_error_handler(401, unauthorized)
    app.register_error_handler(403, forbidden)
    app.register_error_handler(404, page_not_found)
    app.register_error_handler(500, internal_server_error)
    app.register_error_handler(503, service_unavailable)

    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    csrf.init_app(app)

    @app.before_request
    def assign_anonymous_id():
        if not current_user.is_authenticated:
            if "anonymous_id" not in session:
                session["anonymous_id"] = str(uuid4())
            g.anonymous_id = session["anonymous_id"]

    @app.cli.command("setup")
    def populate():
        from .models import InvestmentFirm, Investor, User, UserInfo, UserPayment, entity_search
        from .models.backfill import backfill_entities

        with app.app_context():
            db.drop_all()
            db.create_all()

            admin_list = [
                {
                    "email": "arstan.usenov@gmail.com",
                    "first_name": "Arstan",
                    "last_name": "Usenov",
                    "username": "barnacle",
                },
                {
                    "email": "arstan@globalify.xyz",
                    "first_name": "Arstanbek",
                    "last_name": "Usenov",
                    "username": "barnacle2",
                },
            ]
            for administrator in admin_list:
                user = User(
                    email=administrator["email"],
                    is_verified=True,
                    is_admin=True,
                )
                user_info = UserInfo(
                    first_name=administrator["first_name"],
                    last_name=administrator["last_name"],
                    username=administrator["username"],
                    user=user,
                )
                user_payment = UserPayment(user=user)

                db.session.add(user)
                db.session.add(user_info)
                db.session.add(user_payment)

            Investor.populate_demo()
            Investor.slugify_existing()

            InvestmentFirm.populate_vcsheet()
            InvestmentFirm.slugify_existing()

            backfill_entities(db.session)

            entity_search.sync_search_index(recreate=True)

    app.cli.add_command(populate)

    @app.cli.command("reindex")
    def reindex():
        """Non-destructive reindex: sync entities collection without dropping the DB."""
        from .models import entity_search

        with app.app_context():
            entity_search.sync_search_index(recreate=False)

    app.cli.add_command(reindex)

    return app


application = create_app()
