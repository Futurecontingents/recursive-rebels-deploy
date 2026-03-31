from dataclasses import dataclass
from typing import Optional


@dataclass
class ListingRequestDTO:
    title: Optional[str]
    price: float
    latitude: float
    longitude: float
    source_url: str
    bedrooms: Optional[int] = None
    bathrooms: Optional[int] = None
    area_sqft: Optional[float] = None
    source_site: Optional[str] = None
    realtor_name: Optional[str] = None
    realtor_contact: Optional[str] = None


@dataclass
class ListingResponseDTO:
    listing_id: int
    title: Optional[str]
    price: float
    latitude: float
    longitude: float
    source_url: str
    bedrooms: Optional[int] = None
    final_score: Optional[float] = None
    score_band: Optional[str] = None
    # added this because frontend was showing 0 for transit distance — it was never included
    dist_transit: Optional[float] = None

    def to_dict(self) -> dict:
        return {
            "listingId": self.listing_id,
            "title": self.title,
            "price": self.price,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "sourceUrl": self.source_url,
            "bedrooms": self.bedrooms,
            "finalScore": self.final_score,
            "scoreBand": self.score_band,
            "distanceToNearestTransit": self.dist_transit,
        }