from flask import Blueprint, jsonify, request
from repository.ListingRepository import ListingRepository
from service.ListingService import ListingService

listing_bp = Blueprint("listing_bp", __name__)

repository = ListingRepository("property.db")
service = ListingService(repository)


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