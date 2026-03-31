import csv
from repository.ListingRepository import ListingRepository

DB_FILE = "property.db"
SCHEMA_FILE = "database.sql"
METRO_CSV = "Dubai_Metro_Stations_2026-03-29.csv"
BUS_CSV = "Bus_Stop_Details_2026-03-29.csv"


def import_metro_data(repository: ListingRepository):
    with open(METRO_CSV, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)

        for row in reader:
            name = row["location_name_english"].strip()
            latitude = row["station_location_latitude"]
            longitude = row["station_location_longitude"]
            external_id = row.get("location_id")

            if not name or not latitude or not longitude:
                continue

            repository.insert_transport_point(
                station_name=name,
                point_type="Metro",
                latitude=float(latitude),
                longitude=float(longitude),
                external_id=external_id
            )


def import_bus_data(repository: ListingRepository):
    with open(BUS_CSV, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)

        seen = set()

        for row in reader:
            name = row["stop_name"].strip()
            latitude = row["stop_location_latitude"]
            longitude = row["stop_location_longitude"]
            external_id = row.get("stop_id")

            if not name or not latitude or not longitude:
                continue

            # stop rows may repeat across routes, so deduplicate manually
            key = (name, latitude, longitude)
            if key in seen:
                continue
            seen.add(key)

            repository.insert_transport_point(
                station_name=name,
                point_type="Bus",
                latitude=float(latitude),
                longitude=float(longitude),
                external_id=external_id
            )


def main():
    repository = ListingRepository(DB_FILE)
    repository.create_tables_from_schema(SCHEMA_FILE)

    repository.clear_transport_points()

    import_metro_data(repository)
    import_bus_data(repository)

    print(f"Imported transport points successfully.")
    print(f"Total transport points: {repository.count_transport_points()}")


if __name__ == "__main__":
    main()