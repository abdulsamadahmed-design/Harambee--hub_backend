from datetime import datetime, timezone

from app.extensions import db


class Campaign(db.Model):
    __tablename__ = "campaigns"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False, default="")
    category = db.Column(db.String(80), nullable=False, default="")
    target_amount = db.Column(db.Numeric(12, 2), nullable=False)
    status = db.Column(db.String(20), nullable=False, default="open", index=True)
    organizer_id = db.Column(
        db.Integer, db.ForeignKey("users.id"), nullable=False, index=True
    )
    deadline = db.Column(db.DateTime(timezone=True), nullable=True)
    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    organizer = db.relationship("User")
    pledges = db.relationship("Pledge", back_populates="campaign")

    def __repr__(self):
        return f"<Campaign {self.id} {self.title}>"