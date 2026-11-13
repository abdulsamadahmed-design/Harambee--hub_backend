
from datetime import datetime
from app.extensions import db

class Campaign(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    title = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text, nullable=False)

    goal_amount = db.Column(db.Numeric(12, 2), nullable=False)

    image_url = db.Column(db.String(255), nullable=True)

    status = db.Column(db.String(20), nullable=False, default="active")

    end_date = db.Column(db.DateTime, nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    organizer_id = db.Column(
        db.Integer,
        db.ForeignKey("user.id"),
        nullable=False
    )

    organizer = db.relationship(
        "User",
        backref=db.backref("campaigns", lazy=True)
    )

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "goal_amount": float(self.goal_amount),
            "image_url": self.image_url,
            "status": self.status,
            "end_date": self.end_date.isoformat() if self.end_date else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "organizer_id": self.organizer_id
        }