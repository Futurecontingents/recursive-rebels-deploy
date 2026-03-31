# Integration Test Plan
**Pipeline under test:**

Mock HTML → Scraper Parser → ETL Transform → POST /api/listings → DB

## Scope

- Bayut scraper parser (JSON-LD extraction) 
- PropertyFinder scraper parser (`__NEXT_DATA__`)
- ETL `transform()` normalization + dedup
- ETL `to_api_payload()` field mapping
- `POST /api/listings` acceptance
- Haversine distance calculation
- Transit scoring (metro + bus weights)
- `GET /api/listings/<id>` response shape
- Duplicate listing rejection
- Data integrity across all returned listings

---

## Mock Inputs

### Listing Data (from HTML files)
Extracted from mock HTML files before running any code:

Bayut Latitude = 24.862833525277
Bayut Longitude = 55.141468873901
got it from the Json-LD block in the mainentity.geo block

PropertyFinder Latitude = 25.20560073852539
PropertyFinder Longitude = 55.35015106201172
got it from the value stored in __NEXT_DATA__ specifically property.location.coordinates

### Mock Transit Stations (injected directly into test DB, no real CSV data)
- Mock metro A Longitude = 55.141468873901
- Mock metro A Latitude = 24.865528

- Mock metro B Longitude = 55.35015106201172
- Mock metro B Latitude = 25.208295

-Mock bus A Latitude = 24.857443
-Mock bus A Longitude = 55.141468873901


## Pre-Calculated Expected Values

### Haversine Distance Calculation

The backend uses this formula:
R = 6,371,000 m

φ1 = radians(lat1),  φ2 = radians(lat2)
Δφ = radians(lat2 − lat1)
Δλ = radians(lon2 − lon1)

a = sin²(Δφ/2) + cos(φ1)·cos(φ2)·sin²(Δλ/2)
c = 2·atan2(√a, √(1−a))
distance = R·c

### Bayut → Metro A

Δlat = 300 / 111320 = 0.002694933525...°
a = sin²(Δφ/2) + cos(φ1)·cos(φ2)·0     (Δλ = 0)
  = sin²(Δφ/2)
c = 2·atan2(sin(Δφ/2), cos(Δφ/2))
  = Δφ (for small angles)

distance ≈ 299.66 m


### Bayut → Bus A

Δlat = 600 / 111320  →  distance ≈ 599.33 m

### PF → Metro B

Δlat = 300 / 111320  →  distance ≈ 299.66 m
(same offset, same formula, slightly different cosine factor but negligible)

---

### Linear Scoring

From `ListingService.linear_score(distance, excellent, good, acceptable)`:

Metro thresholds:  excellent=400m, good=800m, acceptable=1500m
Bus thresholds:    excellent=250m, good=500m, acceptable=1000m

if distance ≤ excellent  →  score = 10.0
if distance ≤ good       →  score = 10 − ((distance − excellent) / (good − excellent)) × 3
if distance ≤ acceptable →  score = 7  − ((distance − good) / (acceptable − good)) × 4
else                     →  score = 0.0

### Bayut scores

| Station | Distance | Threshold check | Score |
|---|---|---|---|
| Metro A | 299.66 m | 299.66 ≤ 400 → excellent | **10.0** |
| Bus A | 599.33 m | 500 < 599.33 ≤ 1000 | 7 − ((599.33-500)/(1000-500))×4 = **6.205** |

Final = (0.6 × 10.0) + (0.4 × 6.205)
      = 6.0 + 2.482
      = 8.48   → band = "High"

### PropertyFinder scores

| Station | Distance | Threshold check | Score |
|---|---|---|---|
| Metro B | 299.66 m | ≤ 400 → excellent | **10.0** |
| Bus A | ~44,000 m | > 1000 → unacceptable | **0.0** |

Final = (0.6 × 10.0) + (0.4 × 0.0)
      = 6.0 + 0.0
      = 6.0   → band = "Medium"

> This edge case validates that a listing with no nearby bus does not get a false score
> and correctly shows a degraded but non-zero final score.

---

### Distance to Nearest Transit

`calculate_transport_sdg_score` picks `min(nearest_metro, nearest_bus)`:

| Listing | nearest_metro | nearest_bus | distance_to_nearest_transit |
|---|---|---|---|
| Bayut | 299.66 | 599.33 | **299.66 m** |
| PF | 299.66 | ~44,054 | **299.66 m** |

---

### Summary Table

| Assertion | Bayut expected | PF expected |
|---|---|---|
| `distanceToNearestTransit` | 299.66 m (±2) | 299.66 m (±2) |
| `finalScore` | 8.48 (±0.05) | 6.0 (±0.05) |
| `scoreBand` | High | Medium |


## How to Run

1. Activate the virtual environment from the project root:
   .venv\Scripts\activate

2. Navigate to the integration test directory:
   cd Docs\integration-tests

3. Run the test:
   python test_integration.py

Evidence of a passing run is stored in: `Docs/integration-tests/Evidance/test_results.log`
