import os
from datetime import timedelta

from flask import Flask
from werkzeug.middleware.proxy_fix import ProxyFix

from .extensions import db, login_manager, oauth, migrate
from .routes.main import main, page_not_found, unauthorized, bad_request


def create_app(DATABASE_URL=os.getenv("_DATABASE_URL", "sqlite:///db.sqlite")):
    app = Flask(__name__)
    app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URL
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["REMEMBER_COOKIE_DURATION"] = timedelta(days=30)
    app.secret_key = os.getenv("SECRET_KEY", os.urandom(32))

    app.register_blueprint(main)

    app.register_error_handler(400, bad_request)
    app.register_error_handler(401, unauthorized)
    app.register_error_handler(403, unauthorized)
    app.register_error_handler(404, page_not_found)

    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    oauth.init_app(app)

    oauth_config_google = {
        "OAUTH2_CLIENT_ID": str(os.getenv("_GOOGLE_OAUTH2_CLIENT_ID")),
        "OAUTH2_CLIENT_SECRET": str(os.getenv("_GOOGLE_OAUTH2_CLIENT_SECRET")),
        "OAUTH2_META_URL": "https://accounts.google.com/.well-known/openid-configuration",
        "FLASK_SECRET": "230a59ee-9caa-43d8-bf33-6c1d57cc4721",
    }

    oauth_config_linkedin = {
        "OAUTH2_CLIENT_ID": str(os.getenv("_LINKEDIN_OAUTH2_CLIENT_ID")),
        "OAUTH2_CLIENT_SECRET": str(os.getenv("_LINKEDIN_OAUTH2_CLIENT_SECRET")),
        "OAUTH2_META_URL": "https://www.linkedin.com/oauth/.well-known/openid-configuration",
        "FLASK_SECRET": "15a104fc-03ed-4c48-9e7e-872fcd6e4c58",
    }

    oauth.register(
        "google",
        client_id=oauth_config_google.get("OAUTH2_CLIENT_ID"),
        client_secret=oauth_config_google.get("OAUTH2_CLIENT_SECRET"),
        server_metadata_url=oauth_config_google.get("OAUTH2_META_URL"),
        client_kwargs={"scope": "openid email profile"},
    )

    oauth.register(
        "linkedin",
        client_id=oauth_config_linkedin.get("OAUTH2_CLIENT_ID"),
        client_secret=oauth_config_linkedin.get("OAUTH2_CLIENT_SECRET"),
        server_metadata_url=oauth_config_linkedin.get("OAUTH2_META_URL"),
        client_kwargs={"scope": "r_liteprofile r_emailaddress"},
    )

    return app


application = create_app()
