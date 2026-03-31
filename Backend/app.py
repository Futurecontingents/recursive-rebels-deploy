from flask import Flask, jsonify, render_template
from pathlib import Path
from repository.ListingRepository import ListingRepository
from routes.ListingRoutes import listing_bp

BASE_DIR = Path(__file__).resolve().parent.parent
BACKEND_DIR = Path(__file__).resolve().parent
DB_PATH = BACKEND_DIR / "property.db"
SCHEMA_PATH = BACKEND_DIR / "database.sql"

app = Flask(
    __name__,
    template_folder=str(BASE_DIR),
    static_folder=str(BASE_DIR),
    static_url_path=""
)

repository = ListingRepository(str(DB_PATH))
repository.create_tables_from_schema(str(SCHEMA_PATH))

app.register_blueprint(listing_bp)


@app.route("/", methods=["GET"])
def home():
    return render_template("map.html")


@app.route("/info", methods=["GET"])
def info():
    return jsonify({
        "message": "Recursive Rebels backend is running",
        "availableEndpoints": [
            "GET /api/health",
            "POST /api/listings",
            "GET /api/listings",
            "GET /api/listings/<id>"
        ]
    })


if __name__ == "__main__":
    app.run(debug=True)
