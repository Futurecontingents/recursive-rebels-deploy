/*
  UI logic for the prototype.
  Frontend-only backend integration version.
*/

const API_URL = "/api/listings";

let listings = [];

const maxPriceInput = document.getElementById("maxPrice");
const minTransitScoreInput = document.getElementById("minTransitScore");
const maxDistanceInput = document.getElementById("maxDistance");
const propertyTypeCheckboxes = document.querySelectorAll(".propertyTypeCheckbox");
const accessibleOnlyCheckbox = document.getElementById("accessibleOnly");
const highContrastCheckbox = document.getElementById("highContrast");
const textSizeSelect = document.getElementById("textSize");
const applyFiltersBtn = document.getElementById("applyFiltersBtn");
const resetFiltersBtn = document.getElementById("resetFiltersBtn");
const resultsCount = document.getElementById("resultsCount");
const resultsList = document.getElementById("resultsList");
const detailsContainer = document.getElementById("detailsContainer");

function formatAccessibility(value) {
  return value ? "Yes" : "No";
}

function getPropertyTypeFromBedrooms(bedrooms) {
  if (bedrooms === 0 || bedrooms === null || bedrooms === undefined) return "Studio";
  if (bedrooms === 1) return "1BR";
  if (bedrooms === 2) return "2BR";
  return "3BR+";
}

function normalizeListing(rawListing) {
  return {
    ListingID: rawListing.listingId,
    title: rawListing.title || "Untitled listing",
    type: getPropertyTypeFromBedrooms(rawListing.bedrooms),

    Price: extractPrice(rawListing.price),
    TransitScore: Number(rawListing.finalScore ?? 0),

    Latitude: Number(rawListing.latitude),
    Longitude: Number(rawListing.longitude),

    // pulling from api now instead of defaulting to 0 — was hardcoded before
    DistanceToNearestTransit: rawListing.distanceToNearestTransit ?? 0,
    ScoreBand: rawListing.scoreBand || "Low",

    InclusivityRank: 0,
    AccessibilityFeatures: false,
    SourceURL: rawListing.sourceUrl ?? "#"
  };
}

function extractPrice(priceValue) {
  if (typeof priceValue === "number") return priceValue;

  if (typeof priceValue === "string") {
    return Number(priceValue.replace(/[^\d.]/g, ""));
  }

  return 0;
}

async function loadListingsFromBackend() {
  try {
    const response = await fetch(API_URL);

    if (!response.ok) {
      throw new Error(`Failed to fetch listings: ${response.status}`);
    }

    const data = await response.json();
    console.log("RAW API DATA:", data);

    listings = data.map(normalizeListing);
    console.log("NORMALIZED LISTINGS:", listings);
  } catch (error) {
    console.error("Error loading listings from backend:", error);
    listings = [];
  }
}

function renderDetails(listing) {
  detailsContainer.className = "details-box";
  detailsContainer.innerHTML = `
    <div class="details-row"><span class="details-label">Title:</span> ${listing.title}</div>
    <div class="details-row"><span class="details-label">Price:</span> AED ${listing.Price}</div>
    <div class="details-row"><span class="details-label">Transit score:</span> ${listing.TransitScore}</div>
    <div class="details-row"><span class="details-label">Distance to nearest transit:</span> ${listing.DistanceToNearestTransit} m</div>
    <div class="details-row"><span class="details-label">Inclusivity rank:</span> ${listing.InclusivityRank}</div>
    <div class="details-row"><span class="details-label">Coordinates:</span> ${listing.Latitude}, ${listing.Longitude}</div>
    <div class="details-row">
      <span class="details-label">Source:</span>
      <a href="${listing.SourceURL}" target="_blank" rel="noopener noreferrer"class="preview-link">Open listing</a>
    </div>
  `;
}

window.renderDetails = renderDetails;

function renderResultsList(filteredListings) {
  resultsList.innerHTML = "";

  if (filteredListings.length === 0) {
    resultsList.innerHTML = `<div class="details-empty">No listings match the current filters.</div>`;
    return;
  }

  filteredListings.forEach((listing) => {
    const card = document.createElement("div");
    card.className = "listing-card";

    card.innerHTML = `
      <div class="listing-title">${listing.title}</div>
      <div class="listing-meta">
        ${listing.type}<br>
        AED ${listing.Price}<br>
        Transit score: ${listing.TransitScore}<br>
        Transit distance: ${listing.DistanceToNearestTransit} m
      </div>
    `;

    card.addEventListener("click", () => {
      renderDetails(listing);

      if (typeof window.focusListingOnMap === "function") {
        window.focusListingOnMap(listing);
      }

      if (typeof window.openListingPopup === "function") {
        window.openListingPopup(listing.ListingID);
      }
    });

    resultsList.appendChild(card);
  });
}

function getFilteredListings() {
  const maxPrice = Number(maxPriceInput.value);
  const minTransit = Number(minTransitScoreInput.value);
  const maxDist = Number(maxDistanceInput.value);
  const selectedTypes = Array.from(propertyTypeCheckboxes)
    .filter((checkbox) => checkbox.checked)
    .map((checkbox) => checkbox.value);
  const accessibleOnly = accessibleOnlyCheckbox.checked;

  return listings.filter((listing) => {
    const price = Number(listing.Price ?? 0);
    const score = listing.TransitScore;
    const distance = listing.DistanceToNearestTransit;
    const type = listing.type ?? "N/A";
    const accessible = Boolean(listing.AccessibilityFeatures);

    console.log("FILTER CHECK:", {
      title: listing.title,
      price: price,
      maxPrice: maxPrice,
      score: score,
      minTransit: minTransit,
      distance: distance,
      maxDist: maxDist,
      type: type,
      selectedTypes: selectedTypes,
      accessible: accessible,
      accessibleOnly: accessibleOnly
    });

    if (price > maxPrice) {
      return false;
    }

    if (score !== null && score !== undefined && !Number.isNaN(Number(score))) {
      if (Number(score) < minTransit) {
        return false;
      }
    }

    if (distance !== null && distance !== undefined && !Number.isNaN(Number(distance))) {
      if (Number(distance) > maxDist) {
        return false;
      }
    }

    if (selectedTypes.length > 0) {
      if (type !== "N/A" && !selectedTypes.includes(type)) {
        return false;
      }
    }

    if (accessibleOnly && !accessible) {
      return false;
    }

    return true;
  });
}

function applyFilters() {
  const filteredListings = getFilteredListings();

  console.log("Filtered listings:", filteredListings);

  resultsCount.textContent = `Results: ${filteredListings.length}`;
  renderResultsList(filteredListings);
  renderMarkers(filteredListings);

  if (filteredListings.length > 0) {
    fitMapToListings(filteredListings);
  }
}

function resetFilters() {
  maxPriceInput.value = 10000000;
  minTransitScoreInput.value = 0;
  maxDistanceInput.value = 2000;
  propertyTypeCheckboxes.forEach((checkbox) => {
    checkbox.checked = true;
  });
  accessibleOnlyCheckbox.checked = false;

  detailsContainer.className = "details-empty";
  detailsContainer.textContent = "Select a property from the map or from the results list.";

  applyFilters();
}

function setupAccessibilityControls() {
  highContrastCheckbox.addEventListener("change", () => {
    document.body.classList.toggle("high-contrast", highContrastCheckbox.checked);
  });

  textSizeSelect.addEventListener("change", () => {
    document.body.style.setProperty("--font-scale", textSizeSelect.value);
  });
}

function setupFilterControls() {
  applyFiltersBtn.addEventListener("click", applyFilters);
  resetFiltersBtn.addEventListener("click", resetFilters);
}

async function initializeApp() {
  setupAccessibilityControls();
  setupFilterControls();
  document.body.style.setProperty("--font-scale", textSizeSelect.value);

  await loadListingsFromBackend();
  applyFilters();
}

initializeApp();