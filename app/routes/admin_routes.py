from flask import Blueprint, jsonify

from app.models.user import User
from app.utils.decorators import roles_required
from app.utils.errors import error_response
from app.utils.pagination import paginate_query


admin_bp = Blueprint(
    "admin",
    __name__,
    url_prefix="/api/admin"
)


@admin_bp.get("/users")
@roles_required("admin")
def list_users():
    """
    Return a paginated list of users.

    Only authenticated administrators can access this endpoint.
    """
    try:
        result = paginate_query(
            User.query.order_by(User.id.asc()),
            serializer=lambda user: user.to_dict()
        )

        return jsonify(result), 200

    except ValueError as error:
        return error_response(str(error), 400)
