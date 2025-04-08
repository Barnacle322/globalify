import os
import time
from datetime import timedelta
from uuid import uuid4

import jwt
import sentry_sdk
from flask import Flask, g, session
from flask_login import current_user
from itsdangerous import base64_decode
from jwt.exceptions import InvalidKeyError
from werkzeug.middleware.proxy_fix import ProxyFix

from .extensions import csrf, db, login_manager, migrate, oauth, toolbar
from .routes.admin import admin
from .routes.auth import auth
from .routes.claim import claim
from .routes.investment import investment
from .routes.main import (
    bad_request,
    forbidden,
    internal_server_error,
    main,
    page_not_found,
    service_unavailable,
    unauthorized,
)
from .routes.message import message
from .routes.onboarding import onboarding
from .routes.payment import payment
from .routes.profile import profile
from .routes.search import search
from .routes.settings import settings


def get_apple_client_secret():
    try:
        private_key = os.getenv("_APPLE_OAUTH2_PRIVATE_KEY", "")
        if not private_key:
            raise ValueError("Private key not found in environment variables")
        private_key = base64_decode(private_key).decode("utf-8")

        token = jwt.encode(
            headers={"kid": "T86FS463PW"},
            payload={
                "iss": "4F97NW68H8",
                "iat": int(time.time()),
                "exp": int(time.time()) + 86400 * 180,
                "aud": "https://appleid.apple.com",
                "sub": os.getenv("_APPLE_OAUTH2_CLIENT_ID"),
            },
            key=private_key,
            algorithm="ES256",
        )
    except InvalidKeyError as e:
        print(f"Invalid key error: {e}")
        return
    except Exception as e:
        print(f"An error occurred while generating the token: {e}")
        return

    return token


def create_app(database_url="sqlite:///db.sqlite"):
    sentry_sdk.init(
        dsn=os.getenv("_SENTRY_DSN"), traces_sample_rate=0.25, profiles_sample_rate=0.1, attach_stacktrace=True
    )

    app = Flask(__name__)
    app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("_DATABASE_URL", database_url)
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["SQLALCHEMY_POOL_SIZE"] = int(os.getenv("SQLALCHEMY_POOL_SIZE", 5))
    app.config["SQLALCHEMY_POOL_RECYCLE"] = int(os.getenv("SQLALCHEMY_POOL_RECYCLE", 1800))
    app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {"pool_pre_ping": True}
    app.config["REMEMBER_COOKIE_DURATION"] = timedelta(days=30)
    app.secret_key = os.getenv("SECRET_KEY", "18c2ff95-83a1-4998-8bee-0c6a2170497c")

    if os.getenv("FLASK_ENV") == "testing":
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
    app.register_blueprint(payment, url_prefix="/payment")
    app.register_blueprint(settings, url_prefix="/settings")
    app.register_blueprint(profile, url_prefix="/profile")
    app.register_blueprint(admin, url_prefix="/admin")
    app.register_blueprint(onboarding, url_prefix="/onboarding")
    app.register_blueprint(investment, url_prefix="/investment")
    app.register_blueprint(message, url_prefix="/message")

    app.register_error_handler(400, bad_request)
    app.register_error_handler(401, unauthorized)
    app.register_error_handler(403, forbidden)
    app.register_error_handler(404, page_not_found)
    app.register_error_handler(500, internal_server_error)
    app.register_error_handler(503, service_unavailable)

    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    oauth.init_app(app)
    csrf.init_app(app)

    oauth.register(
        "google",
        client_id=str(os.getenv("_GOOGLE_OAUTH2_CLIENT_ID")),
        client_secret=str(os.getenv("_GOOGLE_OAUTH2_CLIENT_SECRET")),
        server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
        client_kwargs={"scope": "openid email profile"},
    )

    oauth.register(
        "linkedin",
        client_id=str(os.getenv("_LINKEDIN_OAUTH2_CLIENT_ID")),
        client_secret=str(os.getenv("_LINKEDIN_OAUTH2_CLIENT_SECRET")),
        server_metadata_url="https://www.linkedin.com/oauth/.well-known/openid-configuration",
        client_kwargs={"scope": "r_liteprofile r_emailaddress"},
    )

    oauth.register(
        "apple",
        client_id=str(os.getenv("_APPLE_OAUTH2_CLIENT_ID")),
        client_secret=get_apple_client_secret(),
        server_metadata_url="https://appleid.apple.com/.well-known/openid-configuration",
        client_kwargs={
            "scope": "name email",
            "response_mode": "form_post",
            "token_endpoint_auth_method": "client_secret_post",
        },
    )

    @app.before_request
    def assign_anonymous_id():
        if not current_user.is_authenticated:
            if "anonymous_id" not in session:
                session["anonymous_id"] = str(uuid4())
            g.anonymous_id = session["anonymous_id"]

    @app.cli.command("setup")
    def populate():
        from .models import InvestmentFirm, Investor, User, UserInfo, UserPayment
        from .utils.enums import OauthProvider

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
                    oauth_provider=OauthProvider.GOOGLE,
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
            Investor.sync_search_index(recreate=True)

            InvestmentFirm.populate_vcsheet()
            InvestmentFirm.slugify_existing()
            InvestmentFirm.sync_search_index(recreate=True)

    app.cli.add_command(populate)

    return app


application = create_app()
