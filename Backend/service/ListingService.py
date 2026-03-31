import hashlib
import math
from dto.ListingDTO import ListingRequestDTO
from repository.ListingRepository import ListingRepository


class ListingService:
    def __init__(self, repository: ListingRepository):
        self.repository = repository

    def generate_fingerprint(self, listing: ListingRequestDTO) -> str:
        raw = f"{listing.price}|{listing.latitude}|{listing.longitude}|{listing.source_url}"
        return hashlib.md5(raw.encode("utf-8")).hexdigest()

    def validate_listing_data(self, data: dict):
        required_fields = ["price", "latitude", "longitude", "source_url"]

        for field in required_fields:
            if field not in data or data[field] in [None, ""]:
                raise ValueError(f"{field} is required")

        if float(data["price"]) <= 0:
            raise ValueError("price must be greater than 0")

    def haversine_distance(self, lat1, lon1, lat2, lon2):
        r = 6371000

        phi1 = math.radians(lat1)
        phi2 = math.radians(lat2)
        delta_phi = math.radians(lat2 - lat1)
        delta_lambda = math.radians(lon2 - lon1)

        a = (
            math.sin(delta_phi / 2) ** 2
            + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2
        )
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

        return r * c

    def linear_score(self, distance, excellent, good, acceptable):
        if distance is None:
            return 0.0

        if distance <= excellent:
            return 10.0
        elif distance <= good:
            return 10 - ((distance - excellent) / (good - excellent)) * 3
        elif distance <= acceptable:
            return 7 - ((distance - good) / (acceptable - good)) * 4
        else:
            return 0.0

    def calculate_transport_sdg_score(self, nearest_metro_m, nearest_bus_m):
        metro_score = self.linear_score(nearest_metro_m, 400, 800, 1500)
        bus_score = self.linear_score(nearest_bus_m, 250, 500, 1000)

        final_score = round((0.6 * metro_score) + (0.4 * bus_score), 2)

        if final_score >= 8:
            score_band = "High"
        elif final_score >= 5:
            score_band = "Medium"
        else:
            score_band = "Low"

        nearest_distance = min(
            [d for d in [nearest_metro_m, nearest_bus_m] if d is not None],
            default=None
        )

        if nearest_distance is None:
            nearest_type = None
        else:
            candidates = {
                "Metro": nearest_metro_m,
                "Bus": nearest_bus_m,
            }
            candidates = {k: v for k, v in candidates.items() if v is not None}
            nearest_type = min(candidates, key=candidates.get)

        return {
            "transit_score": final_score,
            "distance_to_nearest_transit": round(nearest_distance, 2) if nearest_distance is not None else None,
            "nearest_transit_type": nearest_type,
            "inclusivity_rank": 0,
            "accessibility_features": 0,
            "final_score": final_score,
            "score_band": score_band
        }

    def find_nearest_transport_distances(self, listing_lat, listing_lon):
        transport_points = self.repository.get_all_transport_points()

        nearest_metro = None
        nearest_bus = None
        listing_transit_rows = []

        for point in transport_points:
            if point["Type"] not in ("Metro", "Bus"):
                continue

            distance = self.haversine_distance(
                listing_lat,
                listing_lon,
                point["Latitude"],
                point["Longitude"]
            )

            listing_transit_rows.append({
                "transit_point_id": point["TransitPointID"],
                "distance_meters": round(distance, 2)
            })

            if point["Type"] == "Metro":
                if nearest_metro is None or distance < nearest_metro:
                    nearest_metro = distance
            elif point["Type"] == "Bus":
                if nearest_bus is None or distance < nearest_bus:
                    nearest_bus = distance

        return {
            "nearest_metro": nearest_metro,
            "nearest_bus": nearest_bus,
            "listing_transit_rows": listing_transit_rows
        }

    def create_listing(self, data: dict) -> int:
        self.validate_listing_data(data)

        listing = ListingRequestDTO(
            title=data.get("title"),
            price=float(data["price"]),
            latitude=float(data["latitude"]),
            longitude=float(data["longitude"]),
            source_url=data["source_url"],
            bedrooms=data.get("bedrooms"),
            bathrooms=data.get("bathrooms"),
            area_sqft=data.get("area_sqft"),
            source_site=data.get("source_site"),
            realtor_name=data.get("realtor_name"),
            realtor_contact=data.get("realtor_contact"),
        )

        fingerprint = self.generate_fingerprint(listing)

        if self.repository.exists_by_fingerprint(fingerprint):
            raise ValueError("Duplicate listing detected")

        listing_id = self.repository.insert_listing(listing, fingerprint)

        nearest = self.find_nearest_transport_distances(
            listing.latitude,
            listing.longitude
        )

        score_data = self.calculate_transport_sdg_score(
            nearest_metro_m=nearest["nearest_metro"],
            nearest_bus_m=nearest["nearest_bus"],
        )

        self.repository.insert_listing_transit_distances(
            listing_id,
            nearest["listing_transit_rows"]
        )

        self.repository.upsert_sustainability_score(
            listing_id=listing_id,
            transit_score=score_data["transit_score"],
            distance_to_nearest_transit=score_data["distance_to_nearest_transit"],
            nearest_transit_type=score_data["nearest_transit_type"],
            inclusivity_rank=score_data["inclusivity_rank"],
            accessibility_features=score_data["accessibility_features"],
            final_score=score_data["final_score"],
            score_band=score_data["score_band"]
        )

        return listing_id

    def fetch_all_listings(self):
        return self.repository.get_all_listings()

    def fetch_listing_by_id(self, listing_id: int):
        return self.repository.get_listing_by_id(listing_id)