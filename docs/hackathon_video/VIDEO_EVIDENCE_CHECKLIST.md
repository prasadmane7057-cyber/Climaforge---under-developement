# CLIMAFORGE — Video Evidence & Technical Asset Checklist
## Catalog of Empirical Proofs, System Outputs & Demonstration Artifacts (5:45 Run)

This checklist catalogs the concrete, verifiable technical evidence that substantiates every capability demonstrated in the CLIMAFORGE Hackathon Round 2 video.

---

### 1. AUTOMATED TEST SUITE EXECUTION OUTPUTS
These terminal transcripts provide indisputable empirical proof of code correctness, regression safety, and architectural integrity.

#### Evidence 1.1: Backend Pytest Regression Suite
- **Command**: `python -m pytest backend/tests -q`
- **Output Record**: `302 passed, 814 warnings in 32.79s` (100% PASS)
- **Scope Verified**:
  - `test_audit.py` (2 tests): Authentic event logging.
  - `test_auth_api.py`, `test_auth_config.py`, `test_auth_services.py` (73 tests): JWT, cookies, refresh rotation.
  - `test_engine_alg0.py` through `test_engine_alg8.py`, `test_engine_alg10_13.py` (102 tests): Mathematical correctness of Algorithms 0–13.
  - `test_nugen_gateway.py` (15 tests): Nugen advisory gateway, timeouts, live completion, fallback engine.
  - `test_routing_and_alerts.py` (23 tests): Pre-calamity alerts, safe point discovery, Dijkstra flood-pruned routing.
  - `test_database_and_migrations.py` (8 tests): SQLite schema, Alembic migration lifecycle.
  - `test_incidents_and_offline.py` (14 tests): M7 authenticated incident sync, duplicate deduplication, concurrent submission safety, durable persistence, RBAC.
  - `test_rbac.py` (17 tests), `test_chatbot.py` (17 tests), `test_schemas.py` (17 tests), `test_health.py` (3 tests), `test_scenarios.py` (3 tests), `test_engine_pipeline_and_api.py` (8 tests).

#### Evidence 1.2: Frontend Vitest Unit & Integration Suite
- **Command**: `npm --prefix frontend test -- --run`
- **Output Record**: `7 test files passed, 56 tests passed in 5.74s` (100% PASS)
- **Scope Verified**:
  - `rbac_permissions.test.ts` (5 tests): Role permission mapping (`PERM_SCENARIO_READ`, `PERM_CHATBOT_ASK`).
  - `api_interceptor.test.ts` (5 tests): Interceptor header injection.
  - `auth_service.test.ts` (13 tests): In-memory auth and token lifecycle.
  - `cross_tab_auth.test.ts` (14 tests): Web Locks, BroadcastChannel, token handling.
  - `auth_context_and_ui.test.tsx` (7 tests): UI guarding, role badges.
  - `m6_emergency_routing.test.tsx` (4 tests): Alerts display, Dijkstra safe routing, hazard avoidance tags.
  - `m7_offline_sos.test.tsx` (8 tests): IndexedDB initialization, outbox queueing, durable reload persistence, auto-reconnect sync, ACKNOWLEDGMENT state transition, storage failure fallback warning.

#### Evidence 1.3: Real-Browser Playwright Chromium E2E Suite (8 Tests)
- **Command**: `npm --prefix frontend run test:e2e`
- **Output Record**: `8 passed in 20.2s` (100% PASS)
- **Scope Verified**:
  - `cross_tab_auth.spec.ts` (7 tests):
    1. Coordinates simultaneous refresh across two tabs using Web Locks without replay detection.
    2. Verifies REFRESH_COMPLETED never transfers credentials and BroadcastChannel payloads contain zero secrets.
    3. Propagates logout across tabs, purging in-memory access tokens in both pages.
    4. Propagates session expiration and prevents stale tabs from restoring revoked sessions.
    5. Synchronizes login state across tabs without transferring credentials.
    6. Confirms zero access tokens or refresh tokens are persisted in localStorage or sessionStorage.
    7. Fails closed safely when Web Locks API is unavailable without using unsafe localStorage fallback.
  - `m8_end_to_end_demo.spec.ts` (1 test):
    8. Executes complete 6-scene end-to-end operational workflow demonstration in real Chromium.

#### Evidence 1.4: Frontend Production Compilation & Static Analysis
- **Command**: `npm --prefix frontend run build` -> `✓ built in 877ms` (0 TypeScript / Vite errors).
- **Command**: `npm --prefix frontend run lint` -> `0 errors, 7 warnings` (oxlint).

---

### 2. CORE APPLICATION SCREENS & LIVE INTERACTIONS

| Screen / Component | Route / Location | Primary Visual Artifact to Highlight |
| :--- | :--- | :--- |
| **Command Operations Dashboard** | `http://localhost:5173/` | Overview KPIs, tactical river schematic, active scenario selector (`scenario-flash-flood`). |
| **Risk Telemetry Table** | Overview Tab | Riverside District canonical risk score **82.4 (CRITICAL)**, dominant cause: Rainfall ($112.5\text{ mm/hr}$). |
| **Interactive Consequence Graph** | Cascade Tab | Interactive SVG graph with red `FAILING` nodes (`Drainage`, `Road`), dependency edge strengths, cycle-breaking logs. |
| **Logistics & Interventions Matrix** | Interventions Tab | Top-ranked candidate `I1: Deploy High-Capacity Mobile Pumping Units` (-58.7% risk reduction) and Command Decision Card. |
| **Pre-Calamity Citizen Alerts** | Emergency Assistant Tab | Citizen alert cards for Riverside (`CRITICAL`) and Valley Heights (`LOW / WATCH`). |
| **Deterministic Evacuation Routing** | Emergency Assistant Tab | Safe route from `ZONE-001` to `SP-01` showing 11.7 km, ~16 mins, and avoided hazard corridor `Arterial Road Network`. |
| **Offline Survival Mode Banner** | Emergency Assistant Tab | High-visibility amber banner indicating network disconnection and local IndexedDB cache operation. |
| **Emergency SOS Distress Form** | Emergency Assistant Tab | Form fields for Category, Urgency Priority, Location, GPS, and Distress Description. |
| **Client SOS Outbox Queue** | Emergency Assistant Tab | Real-time status badges showing queued distress signals transitioning from `NOT_SENT` (amber) to `ACKNOWLEDGED` (emerald). |

---

### 3. DATABASE & STORAGE LAYER EVIDENCE

#### Evidence 3.1: SQLite Database Durability
- **Database File**: `backend/app.db` (or test SQLite instance).
- **Table Name**: `incidents`.
- **Schema Columns**:
  - `incident_id`: VARCHAR(36) PRIMARY KEY (Client-generated UUID).
  - `scenario_id`: VARCHAR(64) INDEXED.
  - `zone_id`: VARCHAR(32).
  - `reported_at`: DATETIME.
  - `latitude`: FLOAT (Nullable).
  - `longitude`: FLOAT (Nullable).
  - `incident_type`: VARCHAR(32).
  - `urgency`: VARCHAR(16).
  - `status`: VARCHAR(16) DEFAULT 'ACKNOWLEDGED'.
  - `description`: TEXT.
  - `synced_at`: DATETIME.
- **Alembic Migration**: `backend/alembic/versions/0004_incidents_table.py` linked to `0003_rbac_tables`.

#### Evidence 3.2: Client-Side IndexedDB Storage
- **Database Name**: `climaforge_offline_store` (Version 1).
- **Object Stores**:
  - `scenario_cache` (keyPath: `scenario_id`): Caches scenario metadata, alerts, and safe points.
  - `route_cache` (keyPath: `scenario_id`): Caches calculated evacuation routes and waypoints.
  - `sos_outbox` (keyPath: `incident_id`): Durable queue for offline incident distress reports.
- **Browser Verification**: Open DevTools -> Application -> Storage -> IndexedDB -> `climaforge_offline_store` to view live object store records.

---

### 4. NETWORK & API CONTRACT EVIDENCE

#### Evidence 4.1: Authenticated Incident Sync Endpoint
- **HTTP Method & Path**: `POST /api/scenarios/{scenario_id}/incidents/sync`
- **Response Format**:
  ```json
  {
    "scenario_id": "scenario-flash-flood",
    "total_received": 1,
    "total_synced": 1,
    "total_duplicates": 0,
    "status": "ACKNOWLEDGED",
    "synced_incident_ids": ["3fa85f64-5717-4562-b3fc-2c963f66afa6"],
    "duplicate_incident_ids": []
  }
  ```
