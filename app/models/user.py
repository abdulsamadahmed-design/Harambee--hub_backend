from werkzeug.security import check_password_hash, generate_password_hash

from app.extensions import db


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    name = db.Column(db.String(120), nullable=False)
    role = db.Column(db.String(20), nullable=False, default="contributor")
    password_hash = db.Column(db.String(255), nullable=False, default="")
    is_verified = db.Column(db.Boolean, nullable=False, default=False)

    pledges = db.relationship("Pledge", back_populates="contributor")

    VALID_ROLES = ("organizer", "contributor", "admin")

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f"<User {self.id} {self.email}>"