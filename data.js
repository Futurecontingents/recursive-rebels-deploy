/*
  Demo data for frontend testing.

  Important note:
  This data is only for the prototype.
  It is loosely shaped around the current backend/database schema:
  - ListingID
  - Price
  - Latitude
  - Longitude
  - SourceURL
  - TransitScore
  - DistanceToNearestTransit
  - InclusivityRank
  - AccessibilityFeatures

  Some UI-friendly fields such as title and type are still demo-only fields
  and may need to be synchronised later with the real backend/API.
*/

const listings = [
  {
    ListingID: 1,
    title: "Business Bay Studio",
    type: "Studio",
    Price: 3200,
    Latitude: 25.1866,
    Longitude: 55.2744,
    SourceURL: "https://example.com/listing/1",
    TransitScore: 88,
    DistanceToNearestTransit: 420,
    InclusivityRank: 76,
    AccessibilityFeatures: true
  },
  {
    ListingID: 2,
    title: "Deira 1BR",
    type: "1BR",
    Price: 4500,
    Latitude: 25.2711,
    Longitude: 55.3075,
    SourceURL: "https://example.com/listing/2",
    TransitScore: 93,
    DistanceToNearestTransit: 210,
    InclusivityRank: 81,
    AccessibilityFeatures: true
  },
  {
    ListingID: 3,
    title: "JLT 2BR",
    type: "2BR",
    Price: 7600,
    Latitude: 25.0765,
    Longitude: 55.1458,
    SourceURL: "https://example.com/listing/3",
    TransitScore: 72,
    DistanceToNearestTransit: 640,
    InclusivityRank: 68,
    AccessibilityFeatures: false
  },
  {
    ListingID: 4,
    title: "Al Barsha Studio",
    type: "Studio",
    Price: 2800,
    Latitude: 25.1072,
    Longitude: 55.2006,
    SourceURL: "https://example.com/listing/4",
    TransitScore: 61,
    DistanceToNearestTransit: 890,
    InclusivityRank: 59,
    AccessibilityFeatures: false
  },
  {
    ListingID: 5,
    title: "Bur Dubai 1BR",
    type: "1BR",
    Price: 5200,
    Latitude: 25.2548,
    Longitude: 55.2972,
    SourceURL: "https://example.com/listing/5",
    TransitScore: 95,
    DistanceToNearestTransit: 180,
    InclusivityRank: 84,
    AccessibilityFeatures: true
  },
  {
    ListingID: 6,
    title: "Dubai Marina 2BR",
    type: "2BR",
    Price: 9200,
    Latitude: 25.0800,
    Longitude: 55.1403,
    SourceURL: "https://example.com/listing/6",
    TransitScore: 86,
    DistanceToNearestTransit: 300,
    InclusivityRank: 73,
    AccessibilityFeatures: true
  },
  {
    ListingID: 7,
    title: "Mirdif 3BR",
    type: "3BR",
    Price: 9800,
    Latitude: 25.2234,
    Longitude: 55.4211,
    SourceURL: "https://example.com/listing/7",
    TransitScore: 42,
    DistanceToNearestTransit: 1600,
    InclusivityRank: 51,
    AccessibilityFeatures: false
  },
  {
    ListingID: 8,
    title: "JVC Studio",
    type: "Studio",
    Price: 2500,
    Latitude: 25.0560,
    Longitude: 55.2114,
    SourceURL: "https://example.com/listing/8",
    TransitScore: 67,
    DistanceToNearestTransit: 720,
    InclusivityRank: 62,
    AccessibilityFeatures: true
  }
];