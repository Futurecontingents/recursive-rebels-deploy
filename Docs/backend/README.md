
# **Test Plan**


**Folders created:**
- Docs/backend/logic_test
- Docs/backend/api_test
- Docs/backend/evidence

What the backend logic tests cover:
- listing validation
- fingerprint generation
- haversine distance calculation
- linear score threshold logic
- nearest transport selection
- transport SDG score calculation
- duplicate listing detection
- repository transport point insert/count
- repository listing insert/fetch

What the backend API tests cover:

- `GET /api/health`
- `POST /api/listings` with valid data
- `GET /api/listings` after insert
- `GET /api/listings`
- invalid request handling
- duplicate listing submission


**Expected results:**
- Logic tests: 18 passed
- API tests: 5 passed

- Combined total: 23 passed

**Command to rerun logic and api tests individually from project root in the terminal:**

pytest -q Docs/backend/logic_test

pytest -q Docs/backend/api_test

**Command to run both tests together in the terminal:**

pytest -q Docs/backend

