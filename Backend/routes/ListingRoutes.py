from flask import Blueprint, jsonify, request
from pathlib import Path
from repository.ListingRepository import ListingRepository
from service.ListingService import ListingService
from import_transport_data import import_metro_data, import_bus_data

listing_bp = Blueprint("listing_bp", __name__)

repository = ListingRepository("property.db")
service = ListingService(repository)


BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "property.db"
SCHEMA_PATH = BASE_DIR / "database.sql"


@listing_bp.route("/api/admin/import-transport", methods=["POST"])
def import_transport():
    try:
        repo = ListingRepository(str(DB_PATH))
        repo.create_tables_from_schema(str(SCHEMA_PATH))
        repo.clear_transport_points()
        import_metro_data(repo)
        import_bus_data(repo)

        return jsonify({
            "message": "Transport data imported successfully",
            "transportPoints": repo.count_transport_points()
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500



@listing_bp.route("/api/health", methods=["GET"])
def health_check():
    return jsonify({
        "status": "ok",
        "message": "Backend API is running"
    }), 200


@listing_bp.route("/api/listings", methods=["POST"])
def create_listing():
    try:
        data = request.get_json()

        if data is None:
            return jsonify({"error": "Request body must be JSON"}), 400

        listing_id = service.create_listing(data)

        return jsonify({
            "message": "Listing created successfully",
            "listingId": listing_id
        }), 201

    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@listing_bp.route("/api/listings", methods=["GET"])
def get_all_listings():
    try:
        listings = service.fetch_all_listings()
        return jsonify([listing.to_dict() for listing in listings]), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@listing_bp.route("/api/listings/<int:listing_id>", methods=["GET"])
def get_listing_by_id(listing_id: int):
    try:
        listing = service.fetch_listing_by_id(listing_id)

        if listing is None:
            return jsonify({"error": "Listing not found"}), 404

        return jsonify(listing.to_dict()), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500