
import os
from datetime import datetime, timezone

from flask import Blueprint, current_app, jsonify, request
from sendgrid.helpers.eventwebhook import EventWebhook

from app.extensions import db
from app.models.email_delivery_event import EmailDeliveryEvent


sendgrid_webhook_bp = Blueprint(
    "sendgrid_webhook",
    __name__,
    url_prefix="/api/webhooks/sendgrid"
)


@sendgrid_webhook_bp.post("/events")
def receive_events():
    # Keep the original request body intact for signature verification.
    raw_body = request.get_data(cache=True)

    signature = request.headers.get(
        "X-Twilio-Email-Event-Webhook-Signature"
    )
    timestamp_header = request.headers.get(
        "X-Twilio-Email-Event-Webhook-Timestamp"
    )

    public_key = os.getenv("SENDGRID_EVENT_WEBHOOK_PUBLIC_KEY")

    # Do not accept unsigned webhook requests.
    if not public_key:
        current_app.logger.error(
            "SendGrid webhook public key is not configured."
        )
        return jsonify({"error": "Webhook security is not configured"}), 503


    if not signature or not timestamp_header:
        return jsonify({"error": "Missing signature headers"}), 401

    try:
        verifier = EventWebhook()

        ec_public_key = verifier.convert_public_key_to_ecdsa(
            public_key
        )

        valid_signature = verifier.verify_signature(
            raw_body.decode("utf-8"),
            signature,
            timestamp_header,
            ec_public_key
        )

    except Exception:
        current_app.logger.exception(
            "SendGrid signature verification failed."
        )
        return jsonify({"error": "Invalid webhook signature"}), 401

        return jsonify({"error": "Invalid webhook signature"}), 401

    if not valid_signature:
        return jsonify({"error": "Invalid webhook signature"}), 401

    # SendGrid sends events as a JSON array.
    events = request.get_json(silent=True)

    if not isinstance(events, list):
        return jsonify({"error": "Expected a JSON event array"}), 400

    event_ids = [
        event.get("sg_event_id")
        for event in events
        if isinstance(event, dict) and event.get("sg_event_id")
    ]

    existing_ids = set()

    if event_ids:
        existing_ids = {
            row[0]
            for row in db.session.query(
                EmailDeliveryEvent.event_id
            ).filter(
                EmailDeliveryEvent.event_id.in_(event_ids)
            ).all()
        }

    new_events = []

    for event in events:
        if not isinstance(event, dict):
            continue

        event_id = event.get("sg_event_id")
        email = event.get("email")
        event_type = event.get("event")
        event_timestamp = event.get("timestamp")

        if not event_id or not email or not event_type:
            continue

        if event_id in existing_ids:
            continue

        try:
            occurred_at = datetime.fromtimestamp(
                float(event_timestamp),
                tz=timezone.utc
            )
        except (TypeError, ValueError, OverflowError, OSError):
            continue

        new_events.append(
            EmailDeliveryEvent(
                event_id=event_id,
                recipient_email=email.strip().lower(),
                event_type=event_type,
                message_id=event.get("sg_message_id"),
                occurred_at=occurred_at,
                reason=event.get("reason"),
                response=event.get("response")
            )
        )

        existing_ids.add(event_id)

    try:
        db.session.add_all(new_events)
        db.session.commit()
    except Exception:
        db.session.rollback()
        current_app.logger.exception(
            "Could not save SendGrid delivery events."
        )
        return jsonify({"error": "Could not save events"}), 500

    return jsonify({
        "message": "SendGrid events received successfully",
        "received": len(events),
        "stored": len(new_events)
    }), 200
