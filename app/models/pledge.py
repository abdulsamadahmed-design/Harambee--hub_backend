from datetime import datetime, timezone

from app.extensions import db


class Pledge(db.Model):
    __tablename__ = "pledges"

    id = db.Column(db.Integer, primary_key=True)
    campaign_id = db.Column(
        db.Integer, db.ForeignKey("campaign.id"), nullable=False, index=True
    )
    contributor_id = db.Column(
        db.Integer, db.ForeignKey("user.id"), nullable=True, index=True
    )
    contributor_name = db.Column(db.String(100), nullable=True)
    amount = db.Column(db.Numeric(12, 2), nullable=False)
    message = db.Column(db.String(500), nullable=True)
    is_anonymous = db.Column(db.Boolean, nullable=False, default=False)
    status = db.Column(
        db.String(20), nullable=False, default="pending", index=True
    )
    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    confirmed_at = db.Column(db.DateTime(timezone=True), nullable=True)

    campaign = db.relationship(
        "Campaign", backref=db.backref("pledges", lazy="dynamic")
    )
    contributor = db.relationship("User")

    VALID_STATUSES = ("pending", "confirmed", "cancelled")

    def to_dict(self, viewer=None):
        return {
            "id": self.id,
            "campaign_id": self.campaign_id,
            "amount": float(self.amount) if self.amount is not None else None,
            "message": self.message,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "confirmed_at": self.confirmed_at.isoformat()
            if self.confirmed_at
            else None,
            "contributor": self._contributor_summary(),
        }

    def _contributor_summary(self):
        if self.contributor_name:
            return {"id": self.contributor_id, "name": self.contributor_name}
        if self.contributor is None:
            return None
        return {
            "id": self.contributor.id,
            "name": getattr(self.contributor, "name", None)
            or getattr(self.contributor, "username", None),
        }

    def __repr__(self):
        return f"<Pledge {self.id} campaign={self.campaign_id} status={self.status}>"