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
