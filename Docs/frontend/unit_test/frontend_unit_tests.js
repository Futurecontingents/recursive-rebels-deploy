function extractPrice(priceValue) {
  if (typeof priceValue === "number") return priceValue;

  if (typeof priceValue === "string") {
    return Number(priceValue.replace(/[^\d.]/g, ""));
  }

  return 0;
}

function getPropertyTypeFromBedrooms(bedrooms) {
  if (bedrooms === 0 || bedrooms === null || bedrooms === undefined) return "Studio";
  if (bedrooms === 1) return "1BR";
  if (bedrooms === 2) return "2BR";
  return "3BR";
}

function normalizeListing(rawListing) {
  return {
    ListingID: rawListing.listingId,
    title: rawListing.title || "Untitled listing",
    type: rawListing.type || "N/A",
    Price: extractPrice(rawListing.price),
    TransitScore: Number(rawListing.finalScore ?? 0),
    Latitude: Number(rawListing.latitude),
    Longitude: Number(rawListing.longitude),
    DistanceToNearestTransit: rawListing.distanceToNearestTransit ?? 0,
    ScoreBand: rawListing.scoreBand || "Low",
    InclusivityRank: 0,
    AccessibilityFeatures: false,
    SourceURL: rawListing.sourceUrl ?? "#"
  };
}

function getFilteredListings(listings, filters) {
  const maxPrice = Number(filters.maxPrice);
  const minTransit = Number(filters.minTransitScore);
  const maxDist = Number(filters.maxDistance);
  const selectedType = filters.propertyType;
  const accessibleOnly = filters.accessibleOnly;

  return listings.filter((listing) => {
    const price = Number(listing.Price ?? 0);
    const score = listing.TransitScore;
    const distance = listing.DistanceToNearestTransit;
    const type = listing.type ?? "N/A";
    const accessible = Boolean(listing.AccessibilityFeatures);

    if (price > maxPrice) return false;

    if (score !== null && score !== undefined && !Number.isNaN(Number(score))) {
      if (Number(score) < minTransit) return false;
    }

    if (distance !== null && distance !== undefined && !Number.isNaN(Number(distance))) {
      if (Number(distance) > maxDist) return false;
    }

    if (selectedType !== "all") {
      if (type !== "N/A" && type !== selectedType) return false;
    }

    if (accessibleOnly && !accessible) return false;

    return true;
  });
}

function toggleHighContrast(currentState) {
  return !currentState;
}

function applyTextScale(selectedValue) {
  return String(selectedValue);
}

function assert(condition, message) {
  if (!condition) {
    throw new Error(message);
  }
}

function runTests() {
  const rawListing = {
    listingId: 12,
    title: "Test Listing",
    price: "AED 4,500",
    latitude: "25.2",
    longitude: "55.3",
    distanceToNearestTransit: 420,
    finalScore: 7.8,
    scoreBand: "Medium",
    sourceUrl: "https://example.com"
  };

  const normalized = normalizeListing(rawListing);

  assert(extractPrice(3500) === 3500, "extractPrice should keep numeric price");
  assert(extractPrice("AED 4,500") === 4500, "extractPrice should parse formatted price");
  assert(extractPrice("4500 AED") === 4500, "extractPrice should parse trailing currency");
  assert(extractPrice(null) === 0, "extractPrice should return 0 for null");
  assert(extractPrice(undefined) === 0, "extractPrice should return 0 for undefined");

  assert(getPropertyTypeFromBedrooms(0) === "Studio", "0 bedrooms should map to Studio");
  assert(getPropertyTypeFromBedrooms(1) === "1BR", "1 bedroom should map to 1BR");
  assert(getPropertyTypeFromBedrooms(2) === "2BR", "2 bedrooms should map to 2BR");
  assert(getPropertyTypeFromBedrooms(4) === "3BR", "3+ bedrooms should map to 3BR");
  assert(getPropertyTypeFromBedrooms(undefined) === "Studio", "undefined bedrooms should map to Studio");

  assert(normalized.ListingID === 12, "normalizeListing should map listingId");
  assert(normalized.title === "Test Listing", "normalizeListing should map title");
  assert(normalized.Price === 4500, "normalizeListing should normalize price");
  assert(normalized.TransitScore === 7.8, "normalizeListing should map finalScore");
  assert(normalized.Latitude === 25.2, "normalizeListing should map latitude");
  assert(normalized.Longitude === 55.3, "normalizeListing should map longitude");
  assert(normalized.DistanceToNearestTransit === 420, "normalizeListing should map transit distance");
  assert(normalized.ScoreBand === "Medium", "normalizeListing should map scoreBand");
  assert(normalized.SourceURL === "https://example.com", "normalizeListing should map sourceUrl");

  const normalizedMissing = normalizeListing({
    listingId: 99,
    price: null,
    latitude: "25.1",
    longitude: "55.1"
  });

  assert(normalizedMissing.title === "Untitled listing", "normalizeListing should set default title");
  assert(normalizedMissing.type === "N/A", "normalizeListing should set default type");
  assert(normalizedMissing.Price === 0, "normalizeListing should default price to 0");
  assert(normalizedMissing.DistanceToNearestTransit === 0, "normalizeListing should default transit distance to 0");
  assert(normalizedMissing.ScoreBand === "Low", "normalizeListing should default score band to Low");
  assert(normalizedMissing.SourceURL === "#", "normalizeListing should default source URL");

  const listings = [
    {
      ListingID: 1,
      title: "Business Bay Studio",
      type: "Studio",
      Price: 3200,
      TransitScore: 8.8,
      DistanceToNearestTransit: 420,
      AccessibilityFeatures: true
    },
    {
      ListingID: 2,
      title: "Deira 1BR",
      type: "1BR",
      Price: 4500,
      TransitScore: 9.3,
      DistanceToNearestTransit: 210,
      AccessibilityFeatures: true
    },
    {
      ListingID: 3,
      title: "JLT 2BR",
      type: "2BR",
      Price: 7600,
      TransitScore: 7.2,
      DistanceToNearestTransit: 640,
      AccessibilityFeatures: false
    },
    {
      ListingID: 4,
      title: "Mirdif 3BR",
      type: "3BR",
      Price: 9800,
      TransitScore: 4.2,
      DistanceToNearestTransit: 1600,
      AccessibilityFeatures: false
    }
  ];

  let result;

  result = getFilteredListings(listings, {
    maxPrice: 5000,
    minTransitScore: 0,
    maxDistance: 5000,
    propertyType: "all",
    accessibleOnly: false
  });
  assert(result.length === 2, "max price filter failed");

  result = getFilteredListings(listings, {
    maxPrice: 10000000,
    minTransitScore: 8,
    maxDistance: 5000,
    propertyType: "all",
    accessibleOnly: false
  });
  assert(result.length === 2, "min transit score filter failed");

  result = getFilteredListings(listings, {
    maxPrice: 10000000,
    minTransitScore: 0,
    maxDistance: 500,
    propertyType: "all",
    accessibleOnly: false
  });
  assert(result.length === 2, "max distance filter failed");

  result = getFilteredListings(listings, {
    maxPrice: 10000000,
    minTransitScore: 0,
    maxDistance: 5000,
    propertyType: "2BR",
    accessibleOnly: false
  });
  assert(result.length === 1 && result[0].type === "2BR", "property type filter failed");

  result = getFilteredListings(listings, {
    maxPrice: 10000000,
    minTransitScore: 0,
    maxDistance: 5000,
    propertyType: "all",
    accessibleOnly: true
  });
  assert(result.length === 2, "accessibility filter failed");

  result = getFilteredListings(listings, {
    maxPrice: 10000000,
    minTransitScore: 0,
    maxDistance: 5000,
    propertyType: "all",
    accessibleOnly: false
  });
  assert(result.length === 4, "propertyType = all should not exclude valid listings");

  assert(toggleHighContrast(false) === true, "high contrast toggle enable failed");
  assert(toggleHighContrast(true) === false, "high contrast toggle disable failed");

  assert(applyTextScale("1") === "1", "text scale default failed");
  assert(applyTextScale("1.25") === "1.25", "text scale large failed");

  console.log("All frontend unit tests passed.");
}
runTests();
