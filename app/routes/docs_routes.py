from pathlib import Path

from flask import Blueprint, send_file
from flask_swagger_ui import get_swaggerui_blueprint


docs_bp = Blueprint("docs", __name__)

# Locate the OpenAPI YAML file from the project root
BASE_DIR = Path(__file__).resolve().parents[2]
OPENAPI_FILE = BASE_DIR / "docs" / "openapi.yaml"


@docs_bp.get("/api/openapi.yaml")
def openapi_spec():
    return send_file(
        OPENAPI_FILE,
        mimetype="application/yaml"
    )


swaggerui_blueprint = get_swaggerui_blueprint(
    "/api/docs",
    "/api/openapi.yaml",
    config={"app_name": "Harambee Hub API"}
)
