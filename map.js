let map;
let markersLayer;
let markerMap = {};
let activeMarker = null;

const greenIcon = new L.Icon({
  iconUrl: "https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-green.png",
  shadowUrl: "https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-shadow.png",
  iconSize: [25, 41],
  iconAnchor: [12, 41],
  popupAnchor: [1, -34],
  shadowSize: [41, 41]
});

const orangeIcon = new L.Icon({
  iconUrl: "https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-orange.png",
  shadowUrl: "https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-shadow.png",
  iconSize: [25, 41],
  iconAnchor: [12, 41],
  popupAnchor: [1, -34],
  shadowSize: [41, 41]
});

const redIcon = new L.Icon({
  iconUrl: "https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-red.png",
  shadowUrl: "https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-shadow.png",
  iconSize: [25, 41],
  iconAnchor: [12, 41],
  popupAnchor: [1, -34],
  shadowSize: [41, 41]
});

// dropping score thresholds — backend sends scoreBand directly now so no point guessing
function getIconForBand(bandVal) {
  if (bandVal === "High") return greenIcon;
  if (bandVal === "Medium") return orangeIcon;
  return redIcon;
}

function getBandColor(bandVal) {
  if (bandVal === "High") return "#2e7d32";
  if (bandVal === "Medium") return "#ef6c00";
  return "#c62828";
}

function initMap() {
  map = L.map("map").setView([25.2048, 55.2708], 11);

  L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
    maxZoom: 19,
    attribution: "&copy; OpenStreetMap contributors"
  }).addTo(map);

  markersLayer = L.layerGroup().addTo(map);
}

function renderMarkers(filteredListings) {
  if (!markersLayer) return;

  markersLayer.clearLayers();
  markerMap = {};
  activeMarker = null;

  filteredListings.forEach((listing) => {
    const lat = Number(listing.Latitude ?? listing.latitude);
    const lng = Number(listing.Longitude ?? listing.longitude);
    const score = Number(listing.TransitScore ?? listing.finalScore ?? 0);
    const price = Number(listing.Price ?? listing.price ?? 0);
    const title = listing.title ?? "Untitled listing";
    const type = listing.type ?? "N/A";
    const listingId = listing.ListingID ?? listing.listingId;
    // scoreBand from backend - fallback to Low just in case site returns weird data
    const sband = listing.ScoreBand || "Low";

    if (Number.isNaN(lat) || Number.isNaN(lng)) {
      return;
    }

    const titleColor = getBandColor(sband);

    const marker = L.marker([lat, lng], {
      icon: getIconForBand(sband)
    });

    const popupHtml = `
      <div class="popup-card">
        <div class="popup-title" style="color: ${titleColor};">
          ${title}
        </div>
        <div>Price: AED ${price}</div>
        <div>Score: ${score}</div>
        <div>Type: ${type}</div>
      </div>
    `;

    const popupClass =
      sband === "High" ? "popup-green" :
      sband === "Medium" ? "popup-orange" :
      "popup-red";

    marker.bindPopup(popupHtml, {
      className: popupClass,
      closeButton: false,
      offset: [0, -10]
    });

    marker.on("mouseover", () => {
      if (marker._icon) {
        marker._icon.style.filter = "brightness(1.15)";
      }
      marker.openPopup();
    });

    marker.on("mouseout", () => {
      if (marker._icon) {
        marker._icon.style.filter = "brightness(1)";
      }

      if (activeMarker !== marker) {
        marker.closePopup();
      }
    });

    marker.on("click", () => {
      activeMarker = marker;

      map.flyTo([lat, lng], 13, { duration: 1 });

      if (typeof window.renderDetails === "function") {
        window.renderDetails(listing);
      }

      marker.openPopup();
    });

    marker.addTo(markersLayer);

    if (listingId !== undefined) {
      markerMap[listingId] = marker;
    }
  });
}

function fitMapToListings(filteredListings) {
  if (!map || filteredListings.length === 0) return;

  const coords = filteredListings
    .map((listing) => [
      Number(listing.Latitude ?? listing.latitude),
      Number(listing.Longitude ?? listing.longitude)
    ])
    .filter(([lat, lng]) => !Number.isNaN(lat) && !Number.isNaN(lng));

  if (coords.length === 0) return;

  const bounds = L.latLngBounds(coords);
  map.fitBounds(bounds, { padding: [30, 30] });
}

function openListingPopup(listingId) {
  const marker = markerMap[listingId];
  if (marker) {
    activeMarker = marker;
    marker.openPopup();
  }
}

function focusListingOnMap(listing) {
  if (!map) return;

  const lat = Number(listing.Latitude ?? listing.latitude);
  const lng = Number(listing.Longitude ?? listing.longitude);

  if (!Number.isNaN(lat) && !Number.isNaN(lng)) {
    map.flyTo([lat, lng], 13, { duration: 1 });
  }
}

window.openListingPopup = openListingPopup;
window.focusListingOnMap = focusListingOnMap;

initMap();