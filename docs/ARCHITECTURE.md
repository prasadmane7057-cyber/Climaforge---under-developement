# CLIMAFORGE — System Architecture & Foundation Document (Milestone 0)

## 1. System Overview

**CLIMAFORGE** is a climate-flood decision-support prototype engineered to deliver deterministic, explainable calculations for flood risk, cascade failures, intervention optimization, and emergency response.

The system architecture cleanly decouples:
1. **Authoritative Calculation Core**: Deterministic backend Python algorithms (Algorithms 0–13).
2. **Advisory Layer (Nugen)**: Strictly an advisory AI layer. It cannot calculate or override authoritative risk, resource feasibility, ranking, simulation, or validation decisions.
3. **Operations Dashboard & Emergency Chatbot**: Responsive React + TypeScript frontend for emergency operators and citizen assistance.

---

## 2. Milestone 0 Scope & Architecture Boundary

```
+-----------------------------------------------------------------------+
|                           FRONTEND                                    |
|      React 19 + TypeScript + Vite (Port 5173)                         |
|  - Dark-mode responsive starter screen branded CLIMAFORGE             |
|  - Real-time connection status check to Backend GET /health           |
|  - Explicit loading, success, and structured error states             |
|  - Configurable API target via VITE_API_URL                           |
+-----------------------------------------------------------------------+
                                   |
                             HTTP / REST
                           (CORS Enabled)
                                   v
+-----------------------------------------------------------------------+
|                           BACKEND                                     |
|             Python 3.14 + FastAPI + Pydantic (Port 8000)             |
|  - Config management via app.config (pydantic-settings / env vars)   |
|  - Strict CORS policy supporting local dev frontend                   |
|  - GET /health structured status & diagnostics endpoint               |
|  - Domain Schemas: ZoneInput, GraphNode, Intervention, DecisionCard,  |
|    IncidentRecord, ZoneRisk, ExposureResult, CascadeResult, etc.      |
|  - Synthetic illustrative datasets (3-5 zones, nodes, interventions)  |
+-----------------------------------------------------------------------+
```

---

## 3. Directory Layout

```
climaforge/
├── .env.example              # Canonical reference of environment variables
├── .gitignore                # Source control ignore rules
├── README.md                 # Setup, verification, and run guide
├── docs/
│   ├── ARCHITECTURE.md       # Architectural specification and contracts
│   └── IMPLEMENTATION_STATUS.md # Milestone tracker and requirement status
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py           # FastAPI entrypoint and CORS middleware
│   │   ├── config.py         # Application settings
│   │   ├── routers/
│   │   │   ├── __init__.py
│   │   │   └── health.py     # GET /health endpoint
│   │   └── schemas/
│   │       ├── __init__.py
│   │       ├── contracts.py  # Domain Pydantic models with validation
│   │       └── synthetic_data.py # Illustrative sample data
│   ├── tests/
│   │   ├── __init__.py
│   │   ├── test_health.py    # Health endpoint verification
│   │   └── test_schemas.py   # Schema validation tests
│   ├── requirements.txt      # Backend Python dependencies
│   └── pytest.ini           # Pytest runner configuration
└── frontend/
    ├── src/
    │   ├── App.tsx           # Dark starter screen with connection status
    │   ├── App.css           # Styling for status indicators and cards
    │   ├── main.tsx          # React application root
    │   ├── types/
    │   │   └── api.ts        # Typed API contracts for frontend
    │   └── services/
    │       └── api.ts        # Fetch client with health check
    ├── index.html
    ├── package.json
    ├── tsconfig.json
    ├── tsconfig.node.json
    └── vite.config.ts
```

---

## 4. Provisional Domain Contracts & Source Clarifications

The following core Pydantic contracts are established in Milestone 0. Each schema specifies the fields requiring final confirmation against the reference documentation (`CLIMAFORGE_PRD_System_Architecture.docx` and `CLIMAFORGE_Algorithm_Report_v2.pdf`):

### 4.1 ZoneInput
- **Purpose**: Input telemetry and baseline metadata for a designated geographic zone.
- **Fields**:
  - `zone_id` (str): Unique zone identifier (e.g., `ZONE-001`).
  - `name` (str): Human-readable zone designation.
  - `area_sq_km` (float): Zone geographic surface area in square kilometers.
  - `population` (int): Baseline resident population count.
  - `elevation_m` (float): Mean elevation above sea level.
  - `rainfall_mm` (float): Current or projected cumulative precipitation (mm).
  - `drainage_capacity_cms` (float): Drainage throughput capacity in cubic meters/sec.
  - `soil_saturation_index` (float): Soil moisture saturation ratio [0.0 - 1.0].
  - `critical_infrastructure_count` (int): Count of hospitals, substations, water plants.
- **Confirmation Notes**: Confirm whether real-time water level sensor feeds (river gauge heights in meters) should be integrated into `ZoneInput` or maintained as a separate `GaugeReading` stream in Algorithm 0.

### 4.2 GraphNode
- **Purpose**: Nodes representing critical infrastructure elements in the cascade consequence graph.
- **Fields**:
  - `node_id` (str): Unique node identifier (e.g., `NODE_HOSPITAL_A`).
  - `zone_id` (str): Geographic zone containing the node.
  - `name` (str): Facility or asset name.
  - `node_type` (str): Enum-like category (`hospital`, `substation`, `water_treatment`, `bridge`, `shelter`).
  - `baseline_capacity` (float): Normal operating capacity (e.g., megawatts, beds, liters/day).
  - `current_operational_ratio` (float): Operating ratio [0.0 - 1.0].
  - `flood_threshold_m` (float): Water inundation depth at which failure initiates.
  - `criticality_weight` (float): Priority weighting factor [0.0 - 1.0].
- **Confirmation Notes**: Verify edge dependency types (e.g., power feed vs physical access) and whether recovery latency (hours to restore) is required on the node or the edge.

### 4.3 Intervention
- **Purpose**: Operational actions evaluated to prevent or break failure cascades.
- **Fields**:
  - `intervention_id` (str): Unique intervention identifier (e.g., `INTV-SANDBAG-01`).
  - `name` (str): Descriptive label.
  - `target_node_id` (Optional[str]): Targeted infrastructure node.
  - `target_zone_id` (str): Geographic target zone.
  - `intervention_type` (str): Category (`deploy_barriers`, `mobile_pumps`, `traffic_diversion`, `generator_dispatch`).
  - `required_resources` (Dict[str, int]): Map of resource identifier to quantity required.
  - `cost_estimate_usd` (float): Estimated operational cost.
  - `lead_time_minutes` (int): Time required to deploy on site.
  - `risk_reduction_factor` (float): Expected attenuation factor on failure probability [0.0 - 1.0].
- **Confirmation Notes**: Clarify whether Algorithm 10 uses fixed resource catalog units or dynamic logistics constraints (e.g., road transit accessibility).

### 4.4 DecisionCard
- **Purpose**: Structured final operational summary output from Algorithms 12–13.
- **Fields**:
  - `card_id` (str): Unique decision card reference.
  - `scenario_id` (str): Scenario identifier.
  - `generated_at` (datetime): Timestamp of card synthesis.
  - `headline` (str): Summary recommendation heading.
  - `primary_action_ids` (List[str]): Prioritized list of approved interventions.
  - `total_estimated_cost_usd` (float): Cumulative budget requirement.
  - `projected_impact` (str): Summary of risk mitigation and cascade arrest.
  - `nugen_advisory_status` (str): `ADVISORY_ACCEPTED`, `FALLBACK`, or `DISABLED`.
  - `nugen_rationale` (Optional[str]): Advisory commentary from Nugen (if active).
  - `sign_off_status` (str): `PENDING_REVIEW`, `COMMAND_APPROVED`, `REJECTED`.
- **Confirmation Notes**: Confirm required sign-off authorization fields (e.g., operator badge ID, electronic signature hash) for multi-tier audit trails.

### 4.5 IncidentRecord
- **Purpose**: Telemetry and dispatch logs for emergency SOS and field incident reports.
- **Fields**:
  - `incident_id` (str): Unique record ID.
  - `reported_at` (datetime): Time recorded.
  - `zone_id` (str): Zone identifier.
  - `latitude` (Optional[float]): GPS coordinates.
  - `longitude` (Optional[float]): GPS coordinates.
  - `incident_type` (str): `RISING_WATER`, `MEDICAL_EMERGENCY`, `STRANDED_PERSONS`, `ROAD_BLOCKED`.
  - `urgency` (str): `LOW`, `MEDIUM`, `HIGH`, `CRITICAL`.
  - `status` (str): `NOT_SENT` (offline cache), `QUEUED`, `ACKNOWLEDGED`, `RESOLVED`.
  - `description` (str): Operator or citizen report text.
- **Confirmation Notes**: Confirm offline payload synchronization format when bridging client IndexedDB to server SQLite.

---

## 5. Technology Stack & Decision Rationale

- **Backend Framework**: `FastAPI` (>= 0.115.0) on Python 3.14. High performance, native OpenAPI generation, first-class asynchronous handling, robust type validation via Pydantic v2.
- **Data Validation**: `Pydantic` (>= 2.9.0) with strict field constraints, custom validators, and comprehensive test suites.
- **Frontend Framework**: `React 19` with `TypeScript` (>= 5.0) and `Vite` (>= 6.0). Provides fast Hot Module Replacement (HMR), rigorous type safety, and minimal bundle sizes.
- **Styling**: Tailored high-contrast dark theme engineered for emergency command operations, meeting WCAG AA accessibility standards.
- **Testing**: `pytest` and `httpx` for backend unit and API testing; `tsc --noEmit` and `vite build` for frontend static typing and production asset bundling.

---

## 6. Milestone 5: Nugen Advisory AI Gateway Architecture

```
+-------------------------------------------------------------------------------+
|                       CLIMAFORGE ADVISORY AI GATEWAY (NUGEN)                  |
+-------------------------------------------------------------------------------+
|                                                                               |
|   +-----------------------------------------------------------------------+   |
|   |                 AUTHORITATIVE ENGINE (ALGORITHMS 0–13)                |   |
|   |  - Pure deterministic calculation core                                |   |
|   |  - FloodRisk scores, Hotspots, Cascades, Critical Nodes               |   |
|   |  - Resource allocation, Feasibility verification, Multi-criteria rank |   |
|   |  - ALWAYS authoritative; CANNOT be altered or overridden by AI        |   |
|   +-----------------------------------------------------------------------+   |
|                                       |                                       |
|                         Verified Grounded Context JSON                        |
|                                       v                                       |
|   +-----------------------------------------------------------------------+   |
|   |                        NUGEN GATEWAY COORDINATOR                      |   |
|   |  - Resolves active provider based on server-side config               |   |
|   |  - Enforces non-authoritative tagging and human-review disclaimers    |   |
|   |  - Automatic fail-safe fallback routing on any error or timeout       |   |
|   +-----------------------------------------------------------------------+   |
|           |                               |                       |           |
|           v                               v                       v           |
|   +---------------+              +-----------------+     +----------------+   |
|   | MOCK PROVIDER |              | LIVE COMPLETIONS|     | DETERMINISTIC  |   |
|   | - Grounded    |              | - OpenAI-comp.  |     |   FALLBACK     |   |
|   |   advisory    |              | - Timeout guard |     | - Zero         |   |
|   | - Offline     |              | - HTTP 5xx catch|     |   hallucination|   |
|   |   reproducible|              | - JSON validate |     | - Alg 0-13 data|   |
|   +---------------+              +-----------------+     +----------------+   |
+-------------------------------------------------------------------------------+
```

### 6.1 Architectural Rules & Boundaries
1. **Unidirectional Context Flow**: Nugen ingests read-only scenario and algorithm context; it never writes to simulation graphs, scenario registries, or risk scoring pipelines.
2. **Fail-Closed / Fail-Safe Degradation**: If the live LLM provider experiences timeouts, network interruptions, HTTP 5xx errors, or unparseable payloads, the gateway instantly degrades to the deterministic fallback provider. The core pipeline and decision card generation never fail.
3. **Explicit Advisory Tagging**: All API responses and UI cards returned from the advisory gateway are tagged with `NON-AUTHORITATIVE ADVISORY` and mandatory operator sign-off warnings.
4. **Zero Frontend Secret Exposure**: Provider credentials (`NUGEN_API_KEY`, `CHATBOT_API_KEY`) reside exclusively in backend environment configuration and are never transmitted to client devices.

## 7. Milestone 6: Emergency Alerts, Shelter Discovery & Safe Evacuation Routing

```
+-------------------------------------------------------------------------------+
|             CLIMAFORGE CITIZEN ALERTS & SAFE EVACUATION ROUTING (M6)           |
+-------------------------------------------------------------------------------+
|                                                                               |
|   +------------------------------------+   +------------------------------+   |
|   |   ALGORITHM 1 & 2 RISK PIPELINE    |   |  ALGORITHM 5 CASCADE STATES  |   |
|   |  - Zone 0–100 Risk Scores          |   |  - Node states (FAILING,     |   |
|   |  - Hotspots & Dominant Causes      |   |    WATCH, SAFE) via tau=0.30 |   |
|   +------------------------------------+   +------------------------------+   |
|                     |                                     |                   |
|                     v                                     v                   |
|   +------------------------------------+   +------------------------------+   |
|   |      PRE-CALAMITY ALERT SYSTEM     |   |  SAFE EVACUATION ROUTE ENGINE|   |
|   |  - CRITICAL (>= 75): Evacuation    |   |  - NetworkX transit topology |   |
|   |  - HIGH (50–74.9): Flood Advisory  |   |  - Hard-prunes FAILING nodes |   |
|   |  - MEDIUM / LOW: Watch/Monitoring  |   |  - Penalizes WATCH corridors |   |
|   |  - Grounded dominant cause factor  |   |  - Diverts to elevated ridge |   |
|   |  - Citizen action recommendations  |   |    bypass corridors          |   |
|   +------------------------------------+   |  - Dijkstra shortest path    |   |
|                     |                      +------------------------------+   |
|                     |                                     |                   |
|                     +------------------+------------------+                   |
|                                        v                                      |
|   +-----------------------------------------------------------------------+   |
|   |                     AUTHENTICATED SCENARIO-SCOPED API                 |   |
|   |  - GET  /api/scenarios/{id}/alerts        (PERM_SCENARIO_READ)        |   |
|   |  - GET  /api/scenarios/{id}/safe-points   (PERM_SCENARIO_READ)        |   |
|   |  - POST /api/scenarios/{id}/evacuation-route (PERM_CHATBOT_ASK)       |   |
|   |  - GET  /api/scenarios/{id}/evacuation-route/{route_id}               |   |
|   |  - Strict Contract: is_live_confirmed=False, is_simulated=True        |   |
|   |  - Explicit BLOCKED status & shelter-in-place instructions on cutoff  |   |
|   +-----------------------------------------------------------------------+   |
|                                        |                                      |
|                                        v                                      |
|   +-----------------------------------------------------------------------+   |
|   |                  HIGH-CONTRAST EMERGENCY FRONTEND UI                  |   |
|   |  - EmergencyChatbotTab: Warnings banner, shelter selector, directions |   |
|   |  - RiskMapTab: Interactive safe refuges, dynamic evacuation corridor  |   |
|   |  - Human verification & simulated disclaimers on all views            |   |
|   +-----------------------------------------------------------------------+   |
+-------------------------------------------------------------------------------+
```

### 7.1 Pre-Calamity Citizen Alert Guarantees
1. **Authoritative Severity Mapping**: Risk scores are categorized into citizen-facing tiers:
   - `CRITICAL`: Risk score $\ge 75.0$ (immediate evacuation notice).
   - `HIGH`: Risk score $\ge 50.0$ and $< 75.0$ (flood advisory and preparation warning).
   - `MEDIUM`: Risk score $\ge 25.0$ and $< 50.0$ (flood watch and situational vigilance).
   - `LOW`: Risk score $< 25.0$ (baseline monitoring).
   - `DATA_INSUFFICIENT`: Missing telemetry prevents false classifications.
2. **Dominant Cause Traceability**: Every alert cites the primary physical driver directly extracted from Algorithm 1 factor weighting (`dominant_cause`), eliminating hallucinated causes.
3. **Non-Alarmist Citizen Guidance**: Clear action recommendations matched to severity, advising citizens on orderly movement, go-kit preparation, or baseline vigilance.

### 7.2 Evacuation Routing Safety Guarantees
1. **Dynamic Hazard Pruning**: Intermediate transportation nodes experiencing failure ($p \ge \tau = 0.30$) in Algorithm 5 cascade analysis are excised from the traversable graph. Vehicles and citizens are never routed through flooded road segments.
2. **Deterministic Corridor Diversion**: When primary arterial road networks are flooded, Dijkstra pathfinding automatically identifies and routes through safe, elevated perimeter bypass corridors (e.g. `ROAD-PERIM-01`).
3. **Fail-Closed on Complete Isolation**: If all exit corridors from an origin catchment are severed by flood waters, the engine returns status `BLOCKED` with an explicit list of blocking hazard nodes and actionable shelter-in-place guidance. It strictly refuses to invent or fabricate passable paths.
4. **Mandatory Synthetic Labeling**: Every route plan asserts `is_live_confirmed: false` and `is_simulated: true`, with prominent disclaimers requiring official civil defense verification.

### 7.3 Security & Role-Based Access Control
- All alerts and safe points endpoints require valid JWT authentication and scenario-scoped access grants (`PERM_SCENARIO_READ`).
- Evacuation route planning requires `PERM_CHATBOT_ASK`.
- Users with `AUDITOR` role are strictly restricted from route planning and hazard alerts, returning HTTP 403 Forbidden.
- Unauthenticated requests are rejected with HTTP 401 Unauthorized.



---

## 8. Milestone 7: Offline Panic Storage, Client SOS Outbox & Idempotent Synchronization

```
+-------------------------------------------------------------------------------+
|             CLIMAFORGE OFFLINE PANIC & SOS SYNCHRONIZATION (M7)               |
+-------------------------------------------------------------------------------+
|                                                                               |
|   +------------------------------------+   +------------------------------+   |
|   |         ONLINE CACHE SEED          |   |      OFFLINE SOS OUTBOX      |   |
|   |  - Proactive scenario snapshot     |   |  - Client UUID generation    |   |
|   |  - Pre-calamity alerts & refuges   |   |  - Timestamp, Zone, Urgency  |   |
|   |  - Turn-by-turn route directions   |   |  - Description & GPS coords  |   |
|   +------------------------------------+   +------------------------------+   |
|                     |                                     |                   |
|                     v                                     v                   |
|   +-----------------------------------------------------------------------+   |
|   |             INDEXEDDB LOCAL STORAGE: climaforge_offline_db            |   |
|   |  - Store: offline_scenarios (Full scenario models & calculations)     |   |
|   |  - Store: offline_alerts (Pre-calamity emergency warnings)            |   |
|   |  - Store: offline_safe_points (Designated shelter facilities)         |   |
|   |  - Store: offline_routes (Pre-calculated hazard-avoidance corridors)  |   |
|   |  - Store: offline_sos_outbox (Queued distress calls; NOT_SENT state)  |   |
|   +-----------------------------------------------------------------------+   |
|                     |                                     |                   |
|          Connection Restored                   navigator.onLine === true      |
|                     |                                     |                   |
|                     +------------------+------------------+                   |
|                                        v                                      |
|   +-----------------------------------------------------------------------+   |
|   |                IDEMPOTENT BATCH SYNC API & DEDUPLICATION              |   |
|   |  - POST /api/incidents/batch-sync                                     |   |
|   |  - Atomic database transaction processing                             |   |
|   |  - Unique constraint rollback on duplicate UUID collision             |   |
|   |  - Response: status: "ACKNOWLEDGED", duplicate_incident_ids list      |   |
|   |  - Client outbox transitions records to green ACKNOWLEDGED pill       |   |
|   +-----------------------------------------------------------------------+   |
+-------------------------------------------------------------------------------+
```

### 8.1 Client-Side Offline Storage Guarantees
1. **IndexedDB Architecture**: Implemented via `frontend/src/services/offlineStorage.ts`. Provides structured key-value persistence independent of browser tab crashes or network drops.
2. **Panic Fallback Activation**: When connectivity is severed (`navigator.onLine === false` or API connection timeout), the UI switches seamlessly to cached scenario alerts and route guidance, accompanied by an amber offline notice.
3. **Guaranteed Local SOS Persistence**: Distress signals created during network blackouts are written to IndexedDB with status `NOT_SENT` before UI confirmation is displayed, guaranteeing zero in-memory data loss.
4. **Graceful Storage Degradation**: In environments where IndexedDB is blocked or restricted, the system falls back to in-memory buffering without crashing the application.

### 8.2 Backend Batch Synchronization & Deduplication Guarantees
1. **Transactional Ingestion**: The `/api/incidents/batch-sync` endpoint processes batches inside an isolated SQLAlchemy transaction.
2. **Idempotent Retry Safety**: Network retries sending identical incident UUIDs encounter database unique constraints, trigger immediate transaction rollback, query existing records, and return HTTP 200 with `duplicate_incident_ids`.
3. **Audit Trail Accountability**: Synced incidents are stamped with creation timestamps, reporting zone identifiers, and synchronization event logs for first-responder triage.

---

## 9. Milestone 8: Full End-to-End System Integration, Demo Pipeline & Submission Readiness

```
+-------------------------------------------------------------------------------+
|               CLIMAFORGE M8 FULL PLATFORM INTEGRATION ARCHITECTURE            |
+-------------------------------------------------------------------------------+
|                                                                               |
|   +-------------------+    +--------------------+    +--------------------+   |
|   |  SCENE 1: BASELINE|    |  SCENE 2: ESCALATE |    |  SCENE 3: CASCADE  |   |
|   |  Catchment Normal |    |  Score 82.4 Alert  |    |  Noisy-OR Propag.  |   |
|   |  Zero Hotspots    |    |  Active Inundation |    |  DFS Cycle Safe    |   |
|   +-------------------+    +--------------------+    +--------------------+   |
|             |                        |                         |              |
|             v                        v                         v              |
|   +-------------------+    +--------------------+    +--------------------+   |
|   |  SCENE 4: INTERV. |    |  SCENE 5: CITIZEN  |    |  SCENE 6: RESILIENCE|  |
|   |  Knapsack Optimal |    |  Hazard-Pruned Evac|    |  IndexedDB Panic   |   |
|   |  Decision Card    |    |  Avoidance Alerts  |    |  SOS Queue & Sync  |   |
|   +-------------------+    +--------------------+    +--------------------+   |
|                                                                               |
|   +-----------------------------------------------------------------------+   |
|   |             AUTOMATED REAL-BROWSER VERIFICATION PIPELINE              |   |
|   |  - Playwright Chromium Multi-Tab Suite: frontend/e2e/                 |   |
|   |  - cross_tab_auth.spec.ts: 7 tests verifying Web Locks API mutex,     |   |
|   |    session sync, refresh rotation, and fail-closed security           |   |
|   |  - m8_end_to_end_demo.spec.ts: Automated 6-scene end-to-end run       |   |
|   |  - 100% Deterministic execution across all browser workflows          |   |
|   +-----------------------------------------------------------------------+   |
+-------------------------------------------------------------------------------+
```

### 9.1 Multi-Tab Web Locks Coordination (M16A.7 Integration)
* **Single Refresh Mutex**: `navigator.locks.request('climaforge_auth_refresh_lock')` ensures only one browser tab executes the network refresh call.
* **Secret-Free BroadcastChannel**: Peer tabs are notified via `climaforge_auth_channel` with empty payloads, prompting silent timestamp updates without sharing tokens.
* **Fail-Closed Guarantee**: In browsers lacking Web Locks API support, the platform intentionally refuses to use vulnerable `localStorage` timestamp locks, failing closed safely to prevent race conditions.

### 9.2 Complete Operational Demonstration Pipeline
* Fully documented in `docs/demo/DEMO_RUNBOOK.md`, `SCENARIO_MATRIX.md`, and `REHEARSAL_CHECKLIST.md`.
* Reproducible via automated script `frontend/e2e/m8_end_to_end_demo.spec.ts`.
* Video production scripts, storyboards, and evidence checklists archived in `docs/hackathon_video/`.
* Hackathon submission package consolidated in `docs/hackathon_submission/`.

---

## 10. REAL-TIME ENVIRONMENTAL INTELLIGENCE & INDRAYANI RIVER SURVEILLANCE

```
+-------------------------------------------------------------------------------+
|             REAL-TIME ENVIRONMENTAL INTELLIGENCE ARCHITECTURE                 |
|                                                                               |
|   +-----------------------+     +--------------------+     +--------------+   |
|   |   BROWSER GEOLOCATION |     |  OPEN-METEO CLIENT |     |  IMD CLIENT  |   |
|   |   GPS & Accuracy (m)  |     |  10m Cache / TTL   |     |  Pune Alerts |   |
|   |   6 Corridor Presets  |     |  WMO Weather / 48h |     |  RBAC Guard  |   |
|   +-----------------------+     +--------------------+     +--------------+   |
|               |                            |                       |          |
|               v                            v                       v          |
|   +-----------------------------------------------------------------------+   |
|   |               ENVIRONMENTAL DATA SERVICE COORDINATOR                  |   |
|   |   - Moshi Primary Reference: MPCB Stn 11 (Lat 18.68365, Lon 73.87855) |   |
|   |   - Scientific Disclaimer: "Flood telemetry not verified"             |   |
|   |   - Indrayani Corridor Stations (Dehu, Moshi, Alandi, Tulapur)        |   |
|   |   - Authoritative Algorithms 0-13 Isolation & Null Preservation       |   |
|   +-----------------------------------------------------------------------+   |
|                                    |                                          |
|                                    v                                          |
|   +-----------------------------------------------------------------------+   |
|   |                      FRONTEND ENVIRONMENTAL TAB                       |   |
|   |   - Interactive High-Performance SVG Corridor Map                     |   |
|   |   - 24-48h Hourly Precipitation & Rain Probability Visualizer         |   |
|   |   - Color-Coded IMD District Weather Advisory Matrix                  |   |
|   |   - Historical MPCB Surface-Water Quality Laboratory Archive          |   |
|   +-----------------------------------------------------------------------+   |
+-------------------------------------------------------------------------------+
```

### 10.1 Corridor Geographic Bounding
* Strictly bounded to the Indrayani River Basin, Pune District, Maharashtra, India.
* Official Primary Reference Station: Indrayani River downstream of Moshi village, Taluka Haveli, District Pune (MPCB Station 11, GEMS/MINARS 80).
* Corridor Reference Points: Dehu Ghat, Moshi Reference, Alandi Ghat, and Tulapur Confluence (Bhima-Indrayani Triveni Sangam).

### 10.2 Scientific Honesty Guarantees
* Surface-water quality monitoring reference only; live flood telemetry is unmonitored at this site.
* Mandatory user-facing disclaimers: *"Verified geographical environmental monitoring reference — flood telemetry not verified"* and *"Indrayani River telemetry currently unavailable"*.
* Zero fabricated gauge levels or synthetic stage heights.

### 10.3 Engine Isolation
* Deterministic Algorithms 0–13 remain completely isolated and authoritative.
* Weather readings and unverified river telemetry are never ingested into calculation engines without explicit human-in-the-loop validation.
