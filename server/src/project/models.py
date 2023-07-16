from flask_login import UserMixin
from sqlalchemy.orm import relationship

from werkzeug.security import check_password_hash, generate_password_hash

from .extensions import db


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(50), nullable=False, unique=True)
    password_hash = db.Column(db.String(128), nullable=True)
    first_name = db.Column(db.String(30), nullable=True)
    last_name = db.Column(db.String(30), nullable=True)
    picture = db.Column(db.String, nullable=True)
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

    @staticmethod
    def signed_with_oauth(email: str) -> bool:
        """
        Returns False if the user signed up with email and password or doesn't exist.
        """
        try:
            user = User.query.filter(User.email == email).first()
            return True if user.password_hash is None else False
        except:
            return False
        finally:
            db.session.close()


class EmailForNewsletter(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(50), nullable=False, unique=True)
    added_at = db.Column(db.DateTime, nullable=False, default=db.func.now())

    def __repr__(self):
        return f"<EmailForNewsletter {self.email}>"

    @staticmethod
    def get_by_email(email: str):
        try:
            email = EmailForNewsletter.query.filter(
                EmailForNewsletter.email == email
            ).first()
            return email
        except:
            return None
        finally:
            db.session.close()
