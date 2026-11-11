from datetime import datetime
from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager, jwt_required, get_jwt_identity

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///harambee.db"  # local database file
app.config["JWT_SECRET_KEY"] = "change-me"                       # signs login tokens

db = SQLAlchemy(app)   # our connection to the database
jwt = JWTManager(app)  # handles login tokens

# TEMPORARY stand-in for Member 1's User model. Delete it once theirs is merged.
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))

# A Campaign = one fundraising notice board
class Campaign(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    title = db.Column(db.String(150), nullable=False)       # e.g. "Help with school fees"
    description = db.Column(db.Text, nullable=False)        # the full story
    category = db.Column(db.String(30), default="other")    # wedding, funeral, school_fees...
    target_amount = db.Column(db.Integer, nullable=False)   # goal in KES
    deadline = db.Column(db.DateTime)                       # optional end date
    status = db.Column(db.String(20), default="active")     # active or closed
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Who created this campaign? (the organizer)
    organizer_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    organizer = db.relationship("User")

    # Turns a Campaign into a dictionary so Flask can send it as JSON
    def to_dict(self):
        # "pledges" will exist once Member 3 adds the Pledge model.
        # getattr gives an empty list until then, so nothing breaks.
        pledges = getattr(self, "pledges", [])
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "category": self.category,
            "target_amount": self.target_amount,
            "raised": sum(p.amount for p in pledges if p.status == "paid"),
            "status": self.status,
            "organizer": self.organizer.name,
        }

# The types of campaign we allow
CATEGORIES = ["wedding", "funeral", "school_fees", "medical", "community", "other"]

# POST /api/campaigns -> a logged-in user creates a campaign
@app.post("/api/campaigns")
@jwt_required()  # the user must be logged in (must show their token)
def create_campaign():
    data = request.get_json() or {}   # the form data sent by the user

    title = (data.get("title") or "").strip()
    description = (data.get("description") or "").strip()
    category = data.get("category", "other")

    # The target must be a whole number bigger than 0
    try:
        target = int(data.get("target_amount"))
    except (TypeError, ValueError):
        target = 0

    # Check the details before saving anything
    if not title or not description:
        return jsonify({"error": "Title and description are required"}), 400
    if target <= 0:
        return jsonify({"error": "Target amount must be more than 0"}), 400
    if category not in CATEGORIES:
        return jsonify({"error": f"Category must be one of {CATEGORIES}"}), 400

    # Build the campaign. The organizer ID comes from the login token.
    campaign = Campaign(
        title=title,
        description=description,
        category=category,
        target_amount=target,
        organizer_id=int(get_jwt_identity()),
    )
    db.session.add(campaign)   # put it in the basket
    db.session.commit()        # save the basket to the database
    return jsonify(campaign.to_dict()), 201   # 201 = "created"cx

with app.app_context():
    db.create_all()   # creates the tables

if __name__ == "__main__":
    app.run(debug=True)