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
        hide_identity = self.is_anonymous and not self._viewer_can_see_identity(viewer)
        return {
            "id": self.id,
            "campaign_id": self.campaign_id,
            "amount": float(self.amount) if self.amount is not None else None,
            "message": self.message,
            "is_anonymous": self.is_anonymous,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "confirmed_at": self.confirmed_at.isoformat()
            if self.confirmed_at
            else None,
            "contributor": None if hide_identity else self._contributor_summary(),
        }

    def _contributor_summary(self):
        if self.contributor is None:
            return None
        return {
            "id": self.contributor.id,
            "name": getattr(self.contributor, "name", None)
            or getattr(self.contributor, "username", None),
        }

    def _viewer_can_see_identity(self, viewer):
        if viewer is None:
            return False
        if getattr(viewer, "role", None) == "admin":
            return True
        if self.contributor_id is not None and viewer.id == self.contributor_id:
            return True
        campaign = getattr(self, "campaign", None)
        return campaign is not None and campaign.organizer_id == viewer.id

    def __repr__(self):
        return f"<Pledge {self.id} campaign={self.campaign_id} status={self.status}>"