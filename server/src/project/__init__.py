import os
import xml.etree.ElementTree as ElementTree
from datetime import datetime, timedelta

from flask import Flask, make_response
from werkzeug.middleware.proxy_fix import ProxyFix

from .extensions import csrf, db, login_manager, migrate, oauth
from .routes.auth import auth
from .routes.main import (
    bad_request,
    forbidden,
    internal_server_error,
    main,
    page_not_found,
    service_unavailable,
    unauthorized,
)
from .routes.payment import payment
from .routes.settings import settings


def create_app(database_url="sqlite:///db.sqlite"):
    app = Flask(__name__)
    app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("_DATABASE_URL", database_url)
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["REMEMBER_COOKIE_DURATION"] = timedelta(days=30)
    app.secret_key = os.getenv("SECRET_KEY", "18c2ff95-83a1-4998-8bee-0c6a2170497c")

    @app.route("/sitemap.xml")
    def sitemap():
        pages = []
        ten_days_ago = (datetime.now() - timedelta(days=10)).date().isoformat()

        # Add static pages
        for rule in app.url_map.iter_rules():
            if "GET" in rule.methods and len(rule.arguments) == 0:  # type: ignore
                pages.append([rule.rule, ten_days_ago])

        # Add dynamic pages
        # pages.append(["/dynamic-page", ten_days_ago])

        # Create the XML sitemap
        root = ElementTree.Element("urlset", xmlns="http://www.sitemaps.org/schemas/sitemap/0.9")
        for page in pages:
            url = ElementTree.SubElement(root, "url")
            loc = ElementTree.SubElement(url, "loc")
            loc.text = page[0]
            lastmod = ElementTree.SubElement(url, "lastmod")
            lastmod.text = page[1]
            changefreq = ElementTree.SubElement(url, "changefreq")
            changefreq.text = "weekly"
            priority = ElementTree.SubElement(url, "priority")
            priority.text = "0.5"

        # Return the XML sitemap as a response
        sitemap_xml = ElementTree.tostring(root, encoding="utf-8")
        response = make_response(sitemap_xml)
        response.headers["Content-Type"] = "application/xml"

        return response

    @app.route("/robots.txt")
    def robots():
        robots_txt = "User-agent: *\nDisallow: /admin\nDisallow: /logout\nDisallow: /onboarding\nDisallow: /company-form\nDisallow: /login-linkedin\nDisallow: /login-google\nDisallow: /google-oauth\nDisallow: /linkedin-oauth\n\nSitemap: https://globalify.xyz/sitemap.xml"
        response = make_response(robots_txt)
        response.headers["Content-Type"] = "text/plain"
        return response

    app.register_blueprint(auth)
    app.register_blueprint(main)
    app.register_blueprint(payment, url_prefix="/payment")
    app.register_blueprint(settings, url_prefix="/settings")

    app.register_error_handler(400, bad_request)
    app.register_error_handler(401, unauthorized)
    app.register_error_handler(403, forbidden)
    app.register_error_handler(404, page_not_found)
    app.register_error_handler(500, internal_server_error)
    app.register_error_handler(503, service_unavailable)

    # Reverse proxy support
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    oauth.init_app(app)
    csrf.init_app(app)

    oauth_config_google: dict = {
        "OAUTH2_CLIENT_ID": str(os.getenv("_GOOGLE_OAUTH2_CLIENT_ID")),
        "OAUTH2_CLIENT_SECRET": str(os.getenv("_GOOGLE_OAUTH2_CLIENT_SECRET")),
        "OAUTH2_META_URL": "https://accounts.google.com/.well-known/openid-configuration",
        "FLASK_SECRET": "230a59ee-9caa-43d8-bf33-6c1d57cc4721",
    }

    oauth_config_linkedin: dict = {
        "OAUTH2_CLIENT_ID": str(os.getenv("_LINKEDIN_OAUTH2_CLIENT_ID")),
        "OAUTH2_CLIENT_SECRET": str(os.getenv("_LINKEDIN_OAUTH2_CLIENT_SECRET")),
        "OAUTH2_META_URL": "https://www.linkedin.com/oauth/.well-known/openid-configuration",
        "FLASK_SECRET": "15a104fc-03ed-4c48-9e7e-872fcd6e4c58",
    }

    # oauth_config_apple: dict = {
    #     "OAUTH2_CLIENT_ID": str(os.getenv("_APPLE_OAUTH2_CLIENT_ID")),
    #     "OAUTH2_CLIENT_SECRET": str(os.getenv("_APPLE_OAUTH2_CLIENT_SECRET")),
    #     "OAUTH2_META_URL": "https://appleid.apple.com/.well-known/openid-configuration",
    #     "FLASK_SECRET": "aaea93b4-7a34-46c7-921a-d9642880216c",
    # }

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

    # oauth.register(
    #     "apple",
    #     client_id=oauth_config_apple.get("OAUTH2_CLIENT_ID"),
    #     client_secret=oauth_config_apple.get("OAUTH2_CLIENT_SECRET"),
    #     server_metadata_url=oauth_config_apple.get("OAUTH2_META_URL"),
    #     client_kwargs={"scope": "name email"},
    # )

    return app


application = create_app()
