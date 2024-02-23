from authlib.integrations.flask_client import OAuth
from flask_debugtoolbar import DebugToolbarExtension
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import CSRFProtect
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


db = SQLAlchemy(model_class=Base)
login_manager = LoginManager()
oauth = OAuth()
migrate = Migrate()
csrf = CSRFProtect()
toolbar = DebugToolbarExtension()
