
from datetime import datetime, timezone

from app.extensions import db


class EmailDeliveryEvent(db.Model):
    __tablename__ = "email_delivery_events"

    id = db.Column(db.Integer, primary_key=True)

    # SendGrid's unique event identifier prevents duplicate records.
    event_id = db.Column(
        db.String(255),
        unique=True,
        nullable=False
    )

    recipient_email = db.Column(
        db.String(120),
        nullable=False,
        index=True
    )

    event_type = db.Column(
        db.String(40),
        nullable=False,
        index=True
    )

    message_id = db.Column(db.String(512))

    occurred_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        index=True
    )

    reason = db.Column(db.Text)
    response = db.Column(db.Text)

    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc)
    )
