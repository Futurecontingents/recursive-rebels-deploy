PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS LISTING (
    ListingID INTEGER PRIMARY KEY AUTOINCREMENT,
    Title TEXT,
    Price REAL NOT NULL,
    Bedrooms INTEGER,
    Bathrooms INTEGER,
    AreaSqFt REAL,
    Latitude REAL NOT NULL,
    Longitude REAL NOT NULL,
    SourceURL TEXT NOT NULL,
    SourceSite TEXT,
    RealtorName TEXT,
    RealtorContact TEXT,
    Fingerprint TEXT UNIQUE NOT NULL,
    CreatedAt DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS TRANSIT_POINT (
    TransitPointID INTEGER PRIMARY KEY AUTOINCREMENT,
    StationName TEXT NOT NULL,
    Type TEXT CHECK(Type IN ('Metro', 'Bus')) NOT NULL,
    Latitude REAL NOT NULL,
    Longitude REAL NOT NULL,
    ExternalID TEXT,
    UNIQUE(StationName, Type, Latitude, Longitude)
);

CREATE TABLE IF NOT EXISTS LISTING_TRANSIT (
    ListingID INTEGER NOT NULL,
    TransitPointID INTEGER NOT NULL,
    DistanceMeters REAL NOT NULL,
    PRIMARY KEY (ListingID, TransitPointID),
    FOREIGN KEY (ListingID) REFERENCES LISTING(ListingID) ON DELETE CASCADE,
    FOREIGN KEY (TransitPointID) REFERENCES TRANSIT_POINT(TransitPointID) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS SUSTAINABILITY_SCORE (
    ListingID INTEGER PRIMARY KEY,
    TransitScore REAL DEFAULT 0,
    DistanceToNearestTransit REAL,
    NearestTransitType TEXT CHECK(NearestTransitType IN ('Metro', 'Bus')),
    InclusivityRank INTEGER DEFAULT 0,
    AccessibilityFeatures INTEGER DEFAULT 0,
    FinalScore REAL DEFAULT 0,
    ScoreBand TEXT CHECK(ScoreBand IN ('Low', 'Medium', 'High')),
    LastCalculatedAt DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (ListingID) REFERENCES LISTING(ListingID) ON DELETE CASCADE
);