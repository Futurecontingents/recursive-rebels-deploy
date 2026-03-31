import csv
import sqlite3
from dto.ListingDTO import ListingRequestDTO, ListingResponseDTO


class ListingRepository:
    def __init__(self, db_file: str):
        self.db_file = db_file

    def get_connection(self):
        conn = sqlite3.connect(self.db_file)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        return conn

    def create_tables_from_schema(self, schema_file: str):
        with open(schema_file, "r", encoding="utf-8") as f:
            schema = f.read()

        conn = self.get_connection()
        conn.executescript(schema)
        conn.commit()
        conn.close()

    def clear_transport_points(self):
        conn = self.get_connection()
        conn.execute("DELETE FROM TRANSIT_POINT")
        conn.commit()
        conn.close()

    def insert_transport_point(self, station_name, point_type, latitude, longitude, external_id=None):
        conn = self.get_connection()
        conn.execute(
            """
            INSERT OR IGNORE INTO TRANSIT_POINT (
                StationName, Type, Latitude, Longitude, ExternalID
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (station_name, point_type, latitude, longitude, external_id)
        )
        conn.commit()
        conn.close()

    def count_transport_points(self):
        conn = self.get_connection()
        row = conn.execute(
            "SELECT COUNT(*) AS count FROM TRANSIT_POINT"
        ).fetchone()
        conn.close()
        return row["count"]

    def get_all_transport_points(self):
        conn = self.get_connection()
        rows = conn.execute(
            """
            SELECT TransitPointID, StationName, Type, Latitude, Longitude
            FROM TRANSIT_POINT
            """
        ).fetchall()
        conn.close()
        return rows

    def exists_by_fingerprint(self, fingerprint: str) -> bool:
        conn = self.get_connection()
        row = conn.execute(
            "SELECT COUNT(*) AS count FROM LISTING WHERE Fingerprint = ?",
            (fingerprint,)
        ).fetchone()
        conn.close()
        return row["count"] > 0

    def insert_listing(self, listing: ListingRequestDTO, fingerprint: str) -> int:
        conn = self.get_connection()
        cursor = conn.execute(
            """
            INSERT INTO LISTING (
                Title, Price, Bedrooms, Bathrooms, AreaSqFt,
                Latitude, Longitude, SourceURL, SourceSite,
                RealtorName, RealtorContact, Fingerprint
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                listing.title,
                listing.price,
                listing.bedrooms,
                listing.bathrooms,
                listing.area_sqft,
                listing.latitude,
                listing.longitude,
                listing.source_url,
                listing.source_site,
                listing.realtor_name,
                listing.realtor_contact,
                fingerprint,
            )
        )
        conn.commit()
        listing_id = cursor.lastrowid
        conn.close()
        return listing_id

    def insert_listing_transit_distances(self, listing_id: int, transit_rows: list):
        conn = self.get_connection()

        for row in transit_rows:
            conn.execute(
                """
                INSERT OR REPLACE INTO LISTING_TRANSIT (
                    ListingID, TransitPointID, DistanceMeters
                )
                VALUES (?, ?, ?)
                """,
                (
                    listing_id,
                    row["transit_point_id"],
                    row["distance_meters"]
                )
            )

        conn.commit()
        conn.close()

    def upsert_sustainability_score(
        self,
        listing_id: int,
        transit_score: float,
        distance_to_nearest_transit,
        nearest_transit_type,
        inclusivity_rank: int,
        accessibility_features: int,
        final_score: float,
        score_band: str
    ):
        conn = self.get_connection()
        conn.execute(
            """
            INSERT OR REPLACE INTO SUSTAINABILITY_SCORE (
                ListingID,
                TransitScore,
                DistanceToNearestTransit,
                NearestTransitType,
                InclusivityRank,
                AccessibilityFeatures,
                FinalScore,
                ScoreBand
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                listing_id,
                transit_score,
                distance_to_nearest_transit,
                nearest_transit_type,
                inclusivity_rank,
                accessibility_features,
                final_score,
                score_band
            )
        )
        conn.commit()
        conn.close()

    def get_all_listings(self):
        conn = self.get_connection()
        # also grabbing DistanceToNearestTransit here — was missing before, frontend showed 0
        rows = conn.execute(
            """
            SELECT
                l.ListingID,
                l.Title,
                l.Price,
                l.Bedrooms,
                l.Latitude,
                l.Longitude,
                l.SourceURL,
                s.FinalScore,
                s.ScoreBand,
                s.DistanceToNearestTransit
            FROM LISTING l
            LEFT JOIN SUSTAINABILITY_SCORE s
                ON l.ListingID = s.ListingID
            ORDER BY l.ListingID DESC
            """
        ).fetchall()
        conn.close()

        # print("debug:", rows[0] if rows else "empty")
        return [
            ListingResponseDTO(
                listing_id=row["ListingID"],
                title=row["Title"],
                price=row["Price"],
                bedrooms=row["Bedrooms"],
                latitude=row["Latitude"],
                longitude=row["Longitude"],
                source_url=row["SourceURL"],
                final_score=row["FinalScore"],
                score_band=row["ScoreBand"],
                dist_transit=row["DistanceToNearestTransit"],
            )
            for row in rows
        ]

    def get_listing_by_id(self, listing_id: int):
        conn = self.get_connection()
        row = conn.execute(
            """
            SELECT
                l.ListingID,
                l.Title,
                l.Price,
                l.Bedrooms,
                l.Latitude,
                l.Longitude,
                l.SourceURL,
                s.FinalScore,
                s.ScoreBand,
                s.DistanceToNearestTransit
            FROM LISTING l
            LEFT JOIN SUSTAINABILITY_SCORE s
                ON l.ListingID = s.ListingID
            WHERE l.ListingID = ?
            """,
            (listing_id,)
        ).fetchone()
        conn.close()

        if row is None:
            return None

        return ListingResponseDTO(
            listing_id=row["ListingID"],
            title=row["Title"],
            price=row["Price"],
            latitude=row["Latitude"],
            longitude=row["Longitude"],
            source_url=row["SourceURL"],
            final_score=row["FinalScore"],
            score_band=row["ScoreBand"],
            dist_transit=row["DistanceToNearestTransit"],
        )