from flask_login import UserMixin
from sqlalchemy.orm import relationship

from werkzeug.security import check_password_hash, generate_password_hash

from .extensions import db


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(50), nullable=False, unique=True)
    password_hash = db.Column(db.String(128), nullable=False)
    first_name = db.Column(db.String(30), nullable=True)
    last_name = db.Column(db.String(30), nullable=True)
    is_admin = db.Column(db.Boolean, nullable=False, default=False)

    def __repr__(self):
        return f"<User {self.email}>"

    @property
    def password(self):
        raise AttributeError("Password is not a readable attribute.")

    @password.setter
    def password(self, password):
        self.password_hash = generate_password_hash(password)

    def verify_password(self, password):
        return check_password_hash(self.password_hash, password)

    @staticmethod
    def get_by_id(id: int):
        try:
            user = User.query.filter(User.id == id).first()
            return user
        except:
            return None
        finally:
            db.session.close()

    @staticmethod
    def get_by_email(email: str):
        try:
            user = User.query.filter(User.email == email).first()
            return user
        except:
            return None
        finally:
            db.session.close()
