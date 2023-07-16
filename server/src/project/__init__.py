import os
from datetime import timedelta

from flask import Flask
from werkzeug.middleware.proxy_fix import ProxyFix

from .extensions import db, login_manager, oauth
from .routes.main import main, page_not_found, unauthorized


def create_app(DATABASE_URL=os.getenv("_DATABASE_URL", "sqlite:///db.sqlite")):
    app = Flask(__name__)
    app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URL
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["REMEMBER_COOKIE_DURATION"] = timedelta(days=30)
    app.secret_key = os.getenv("SECRET_KEY", os.urandom(32))

    app.register_blueprint(main)

    app.register_error_handler(404, page_not_found)
    app.register_error_handler(401, unauthorized)

    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

    db.init_app(app)
    login_manager.init_app(app)
    oauth.init_app(app)

    oauth_config = {
        "OAUTH2_CLIENT_ID": str(os.getenv("_OAUTH2_CLIENT_ID")),
        "OAUTH2_CLIENT_SECRET": str(os.getenv("_OAUTH2_CLIENT_SECRET")),
        "OAUTH2_META_URL": "https://accounts.google.com/.well-known/openid-configuration",
        "FLASK_SECRET": "230a59ee-9caa-43d8-bf33-6c1d57cc4721",
    }

    oauth.register(
        "globalify",
        client_id=oauth_config.get("OAUTH2_CLIENT_ID"),
        client_secret=oauth_config.get("OAUTH2_CLIENT_SECRET"),
        server_metadata_url=oauth_config.get("OAUTH2_META_URL"),
        client_kwargs={"scope": "openid email profile"},
    )

    return app


application = create_app()
