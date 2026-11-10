# CLIMAFORGE — Climate-Flood Decision-Support Prototype

CLIMAFORGE is an emergency operations and decision-support prototype engineered to deliver deterministic, explainable calculations for flood risk, critical infrastructure cascades, intervention feasibility, and citizen emergency guidance.

> **IMPORTANT DISCLAIMER**  
> All demo data, threshold parameters, and risk values in Milestone 0 are **SYNTHETIC / ILLUSTRATIVE ONLY**.  
> The system does not claim real-world prediction accuracy, guaranteed evacuation times, or real-world emergency dispatch.

---

## Real ML Flood-Rainfall Prediction

The separate ML layer uses the NOAA GHCN-Daily Central Park station (`USW00094728`) historical weather observations:
https://www.ncei.noaa.gov/data/global-historical-climatology-network-daily/access/USW00094728.csv

Features are current/lagged precipitation, maximum/minimum temperature, snow depth, and 3/7/14-day precipitation means. The target is the following calendar day's precipitation class: LOW `<25 mm`, MEDIUM `25-49.999 mm`, HIGH `50-99.999 mm`, or CRITICAL `>=100 mm`.

```powershell
# From the workspace root
.\backend\.venv\Scripts\python.exe backend\ml\train_flood_model.py --download

# Run API
.\backend\.venv\Scripts\python.exe -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000
```

POST `/api/ml/flood/predict` with the fields documented in Swagger. Evaluation data and the model artifact are written to `backend/models/flood_rf_metrics.json` and `backend/models/flood_rf.joblib`.
The ML prediction is advisory and does not modify or replace deterministic Algorithms 0-13.

### M10 validation methodology and actual results

The training script preserves chronological order and creates a 60% train, 20% validation, and 20% untouched test partition (34,573 / 11,525 / 11,525 observations). It does not shuffle observations. The target remains the next-day precipitation class:
LOW `<25 mm`, MEDIUM `25-49.999 mm`, HIGH `50-99.999 mm`, or CRITICAL `>=100 mm`. Rolling features are constructed from precipitation shifted by one row, so the 3/7/14-day windows contain historical observations and do not include the prediction target or future rows.

Compared models:

- Random Forest, no class weights
- Random Forest, `balanced`
- Random Forest, `balanced_subsample`
- Extra Trees, `balanced`

Validation-only threshold search was also tested for class probability thresholds. Thresholds are never selected from the chronological test partition. Precision-recall curves are saved in the detailed metrics file. No resampling was applied.

The baseline retained for production had test accuracy **96.19%**, macro precision **0.2405**, macro recall **0.2500**, macro F1 **0.2451**, and weighted F1 **0.9432**. HIGH recall was **0.0000** and CRITICAL recall was **0.0000**. MEDIUM recall was also **0.0000**.

The balanced Extra Trees/Random Forest threshold experiments improved some priority recall in validation or test partitions, but none demonstrated reliable HIGH and CRITICAL detection and one reduced LOW recall and overall weighted F1 severely while producing almost entirely MEDIUM/HIGH predictions. Under the milestone acceptance rule, no candidate qualified for replacement because it did not achieve meaningful validation recall for both HIGH and CRITICAL. Therefore `backend/models/flood_rf.joblib` and `backend/models/flood_rf_baseline.joblib` contain the retained baseline configuration.

Baseline test confusion matrix, ordered LOW/MEDIUM/HIGH/CRITICAL:

```text
11086     0     0    0
  346     0     0    0
   81     0     0    0
   12     0     0    0
```

### M11 rare rainfall detection investigation

`backend/ml/research_rare_rainfall.py` preserves the four-class target and adds a separate binary experiment:
NORMAL is next-day rainfall below 50 mm, while HEAVY_RAIN is next-day rainfall at or above 50 mm.
The same chronological 60/20/20 partition is used: 34,573 train, 11,524 validation, and 11,525 test rows.

Heavy-rain test prevalence is 93 of 11,525 observations (0.807%). In chronological order:

| Partition | LOW | MEDIUM | HIGH | CRITICAL |
|---|---:|---:|---:|---:|
| Train | 33,537 | 846 | 173 | 17 |
| Validation | 11,107 | 314 | 95 | 8 |
| Test | 11,086 | 346 | 81 | 12 |

The production four-class baseline predicts only LOW: accuracy alone remains 96.19%, but every MEDIUM, HIGH, and CRITICAL observation is missed. This occurs because the four-class Random Forest is strongly dominated by the 96% LOW majority and receives no class-weight or threshold-adjusted heavy-event optimization in the retained artifact.

Experimental binary models produced a meaningful recall tradeoff instead of all-Low predictions. The selected Extra Trees model achieved validation PR-AUC 0.0112 and test PR-AUC 0.0124. Its test heavy-rain recall was 48.39% with 45 true positives, 48 false negatives, and a 51.61% false-negative rate. It produced 4,254 false positives and precision was 0.01047. Logistic regression and the two class-weighted Random Forest variants were weaker overall on validation recall/PR-AUC.

The dataset is not sufficient for confidently claimed heavy-rainfall prediction. Only 190 of 34,573 training observations reach at least 50 mm, and the test period has only 93 heavy events. The binary result is therefore a research signal only; the experimental model is not deployed automatically.

Experimental artifacts are kept separately:

- `backend/models/binary_heavy_rain_experiment.json`
- `backend/models/binary_heavy_rain_experimental.joblib`

The production model and API are unchanged.

Results, comparison metrics, baseline artifact, and precision-recall analysis are stored in:

- `backend/models/flood_rf_metrics.json`
- `backend/models/flood_rf_comparison.json`
- `backend/models/flood_rf.joblib`
- `backend/models/flood_rf_baseline.joblib`

### M12 historical NOAA dataset expansion

The M12 expansion script downloads and normalizes NOAA GHCN-Daily station CSV files while preserving the original Central Park dataset and existing model artifacts.

```powershell
.\backend\.venv\Scripts\python.exe backend\ml\expand_historical_weather.py
```

The normalized research dataset is `backend/data/noaa_expanded_rainfall.csv`. Missing `PRCP` observations remain `NaN`, are identified by `prcp_missing=true`, and are never converted to zero. NOAA PRCP tenths of a millimetre are divided by 10 to produce `prcp_mm`.

The audit covered six stations and 195,682 station-day observations. Five stations passed the predefined quality gates of at least 50 record years, 95% precipitation completeness, and 18,250 observations: Central Park, Miami, Seattle, Los Angeles, and Houston. Chicago failed the completeness gate at 84.9398%. The Chicago, Los Angeles, and Seattle station data also contain station-level missing values documented in the audit report.

Across the expanded dataset, `PRCP` is missing in 4,625 observations (2.3635%). The dataset contains 1,269 observations at or above 50 mm and 168 observations at or above 100 mm. The chronological audit used 117,409 train rows, 39,136 validation rows, and 39,137 test rows. Station-held-out audits are included for every station, and no date/station observation is reused across those station splits.

This data is suitable only for controlled rainfall research and validation experiments. It is not evidence of a confirmed flood prediction capability and was not used to retrain, replace, or deploy the production model.

Audit and download metadata are stored in:

- `backend/models/noaa_expansion_report.json`
- `backend/data/noaa_expanded/` (cached source CSV files)

### M13 multi-station heavy rainfall experiment

`backend/ml/experiment_multi_station_rainfall.py` creates a separate binary rainfall experiment without changing the production model or API.

The target remains:

- `NORMAL`: next observation has precipitation below 50 mm
- `HEAVY_RAIN`: next observation has precipitation at or above 50 mm

Features are engineered independently for each station. Lag and 3/7/14-day rolling precipitation features shift rainfall by one observation and use only historical values. Station boundaries prevent rolling data from crossing locations. Missing target observations and non-consecutive dates are excluded; missing feature values are median-imputed and are never converted to zero. Geographic station information is included as station ID, latitude, longitude, and elevation.

The chronological experiment used a unique-date 60%/20%/20% split. It retained 166,220 valid station-observation rows and 1,179 heavy-rain targets. HistGradientBoosting was validation-selected. On the untouched chronological test period, it achieved 0.0439 precision, 0.2275 recall, 0.0736 F1, and 0.0327 PR-AUC. It detected 111 of 488 heavy-rain events, missed 377, and produced 2,418 false positives.

Per-station chronological recall varied from 0.0500 for Seattle to 0.3610 for Miami. Central Park recall was 0.0538, below the 48.39% M11 Central Park-only experimental recall. This result is not evidence that geographic expansion improved Central Park generalization.

Leave-one-station-out results remained weak:

| Held-out station | Selected model | Precision | Recall | F1 | PR-AUC | False negatives |
|---|---|---:|---:|---:|---:|---:|
| Central Park | Logistic | 0.0144 | 0.1606 | 0.0265 | 0.0131 | 839/993 |
| Miami | HistGradient | 0.0338 | 0.4318 | 0.0627 | 0.0341 | 254/447 |
| Seattle | HistGradient | 0.0000 | 0.0000 | 0.0000 | 0.0040 | 38/38 |
| Los Angeles | Logistic | 0.0380 | 0.1667 | 0.0619 | 0.0149 | 35/42 |
| Houston | Logistic | 0.0518 | 0.1128 | 0.0710 | 0.0400 | 236/266 |

Artifacts are kept separate from production:

- `backend/models/multi_station_heavy_rain_experiment.json`
- `backend/models/multi_station_heavy_rain_experimental.joblib`
- `backend/models/multi_station_heavy_rain_threshold.json`
- `backend/models/multi_station_heldout_*.joblib`

Production integration is not justified by this experiment. Heavy-rain detection remains rare-event sensitive, precision is low, and station-held-out performance is inconsistent.

### M14 predictive feature enhancement experiment

`backend/ml/experiment_predictive_features.py` merges NOAA GHCN-Daily temperature and available atmospheric observations into a separate M14 dataset without modifying the expanded rainfall CSV or production artifacts.

```powershell
.\backend\.venv\Scripts\python.exe backend\ml\experiment_predictive_features.py
```

Available and missing coverage in the 166,220 valid model rows:

- Precipitation: 100% coverage
- Maximum temperature: 99.9777% coverage
- Minimum temperature: 99.9917% coverage
- Average wind speed: 44.3939% coverage
- Humidity fields: approximately 20.64% coverage
- Sea-level pressure and station pressure: approximately 20.56% coverage
- Calendar features: 100% coverage

Temperature, wind, humidity, and pressure observations are used only as same-date historical observations for predicting next-day rainfall. They are never derived from the target day, and precipitation rolling features remain shifted and station-local. Missing values are median-imputed by pipelines; they are not converted to zero.

Chronological experiment comparison:

| Feature group | Selected model | Precision | Recall | F1 | PR-AUC | False negatives |
|---|---|---:|---:|---:|---:|---:|
| Precipitation only | HistGradient | 0.0363 | 30.12% | 0.0648 | 0.0345 | 341/488 |
| Precipitation + temperature | HistGradient | 0.0479 | 20.49% | 0.0777 | 0.0334 | 388/488 |
| Precipitation + atmospheric | HistGradient | 0.0363 | 30.12% | 0.0648 | 0.0345 | 341/488 |
| Precipitation + seasonal | Logistic | 0.0411 | 24.59% | 0.0705 | 0.0430 | 368/488 |

Temperature improved chronological F1 and precision but reduced recall. Seasonal features improved PR-AUC but did not improve F1 or recall enough to establish an operationally useful result. Atmospheric variables did not improve over precipitation only in the chronological comparison.

M14 station-held-out performance remained inconsistent. Miami recall improved with temperature to 69.57%, but Central Park recall fell to 2.33%, Los Angeles to 4.76%, and Seattle remained at zero recall for the temperature and precipitation-only variants. Results were not consistent across locations and should not be interpreted as proven generalization.

Experimental files are kept separately:

- `backend/data/m14_predictive_features.csv`
- `backend/models/m14_predictive_feature_experiment.json`
- `backend/models/m14_*.joblib`

No M14 model is connected to the production API or deterministic engine. Additional variables do not justify production integration based on these controlled experiments.

---

## M15 grounded chatbot

The emergency assistant is a read-only backend integration. It rebuilds context from the selected scenario's synthetic/illustrative inputs and a fresh deterministic Algorithms 0–13 run. It also permits audit context where relevant and explicitly marks experimental rainfall models as non-authoritative. It does not use the production rainfall classifier as a flood forecast or expose any provider credentials to the browser.

Endpoint:

```text
POST /api/chatbot/message
{
  "scenario_id": "scenario-monsoon-alert",
  "question": "Which locations are most affected?",
  "history": []
}
```

The response identifies whether it came from the provider or deterministic fallback:

```json
{
  "answer": "... grounded actual values or an explicit unavailable-data statement ...",
  "source": "DETERMINISTIC_FALLBACK",
  "mode": "deterministic_fallback",
  "scenario_id": "scenario-monsoon-alert",
  "context_available": true
}
```

No provider is enabled by default. Configure an OpenAI-compatible chat completions endpoint in `backend/.env` only when credentials are available:

```text
NUGEN_ENABLED=True
NUGEN_MOCK_MODE=False
CHATBOT_PROVIDER=openai-compatible
CHATBOT_API_KEY=your-secret
CHATBOT_ENDPOINT=https://provider.example/v1/chat/completions
CHATBOT_MODEL=provider-model-name
CHATBOT_TIMEOUT_SECONDS=20
```

Keep secrets in backend environment files and never use `VITE_*` variables for chatbot credentials. Provider timeout or failure returns the deterministic fallback. The fallback summarizes actual deterministic risk, consequence, resource, intervention, what-if, and missing-data fields; it does not invent deployments, live measurements, emergency services, or flood forecasts. Chat requests only read and explain existing outputs and cannot modify engine state.

Test the backend chatbot:

```powershell
.\backend\.venv\Scripts\python.exe -m pytest backend\tests\test_chatbot.py -q
```

---

## Architecture Boundary

1. **Authoritative Calculation Core (Algorithms 0–13)**: Strictly deterministic Python modules.
2. **Advisory AI Layer (Nugen)**: Strictly advisory and non-authoritative. It cannot calculate or override risk scores, resource constraints, intervention rankings, or validation criteria.
3. **Emergency Chatbot**: Multi-phase guidance (Pre-Calamity Alert, Live Navigation, Panic Phase / Offline Outbox).
4. **Data Integrity**: Missing required telemetry yields `DATA_INSUFFICIENT`; scores and safe routes are never fabricated. Offline SOS reports remain `NOT_SENT` until confirmed by a backend receipt.

---

## Repository Structure

```
Climaforge Workspace/
├── .env.example              # Unified root environment template
├── .gitignore                # Git exclusions (node_modules, venvs, caches, secrets)
├── README.md                 # Setup and run guide
├── docs/
│   ├── ARCHITECTURE.md       # Full-stack architectural specification & contracts
│   └── IMPLEMENTATION_STATUS.md # Milestone tracker & feature status
├── backend/
│   ├── app/
│   │   ├── __init__.py       # Package metadata
│   │   ├── main.py           # FastAPI entrypoint, CORS configuration & routes
│   │   ├── config.py         # Application settings via pydantic-settings
│   │   ├── routers/
│   │   │   ├── __init__.py
│   │   │   └── health.py     # GET /health diagnostic endpoint
│   │   └── schemas/
│   │       ├── __init__.py   # Domain contracts export
│   │       ├── contracts.py  # Pydantic models (ZoneInput, GraphNode, etc.)
│   │       └── synthetic_data.py # Baseline illustrative demo datasets
│   ├── tests/
│   │   ├── __init__.py
│   │   ├── test_health.py    # Health endpoint verification
│   │   └── test_schemas.py   # Pydantic contract validation tests
│   ├── pytest.ini            # Pytest test runner configuration
│   ├── requirements.txt      # Python dependencies
│   └── .env.example          # Backend environment template
└── frontend/
    ├── src/
    │   ├── App.tsx           # Dark starter screen with connection status
    │   ├── App.css           # Styling for status indicators and cards
    │   ├── index.css         # Baseline style reset
    │   ├── main.tsx          # React application root
    │   ├── types/
    │   │   └── api.ts        # Typed API models & contracts
    │   └── services/
    │       └── api.ts        # Backend health check fetch client
    ├── index.html            # HTML page shell
    ├── package.json          # Node dependencies & scripts
    ├── tsconfig.json         # TypeScript compiler configuration
    ├── vite.config.ts        # Vite build tool configuration
    └── .env.example          # Frontend environment template
```

---

## System Prerequisites

- **OS**: Windows 10/11 with PowerShell
- **Node.js**: v20+ (tested with Node v24.17.0 and npm 12.0.0)
- **Python**: 3.11+ (tested with Python 3.14.3)

---

## Quick Setup Guide (Windows PowerShell)

Open PowerShell in the workspace root:

```powershell
cd "C:\Users\Aditya\Desktop\Climaforge Workspace"
```

### 1. Environment Configuration

Copy the example environment configurations:

```powershell
# Root template
Copy-Item .env.example .env

# Backend configuration
Copy-Item backend\.env.example backend\.env

# Frontend configuration
Copy-Item frontend\.env.example frontend\.env
```

Strict authentication requires a JWT signing key and a separate refresh-token
pepper. Generate two independent values, then replace the corresponding
placeholders in both `.env` and `backend\.env`:

```powershell
python -c "import secrets; print(secrets.token_hex(32))"
python -c "import secrets; print(secrets.token_hex(32))"
```

Keep these values private. The examples use a local SQLite database URL; the
backend also accepts PostgreSQL URLs using the `postgresql+psycopg` driver.
The backend exits at startup if strict authentication configuration is missing
or invalid.

### 2. Backend Setup

Create the Python virtual environment and install dependencies:

```powershell
# Create virtual environment
python -m venv backend\.venv

# Activate virtual environment (PowerShell)
.\backend\.venv\Scripts\Activate.ps1

# Upgrade pip and install required dependencies
pip install -r backend\requirements.txt
```

### 3. Frontend Setup

Install the frontend Node dependencies:

```powershell
cd frontend
npm install
cd ..
```

---

## Running the Verification Suite

### 1. Execute Backend Tests

Run `pytest` to verify the `/health` endpoint, Pydantic domain contracts, and all Milestone 2, 3 & 4 calculation and decision modules (Algorithms 0–13):

```powershell
.\backend\.venv\Scripts\pytest backend\tests
```

Expected output: `135 passed in ~1s`.

### 2. Verify Frontend Production Build

Run the TypeScript typechecker and Vite production bundler:

```powershell
cd frontend
npm run build
cd ..
```

Expected output: `✓ built in ~1s` with 0 TypeScript diagnostics.

---

## Starting the Development Services

Run the backend and frontend services in separate Windows PowerShell terminals:

### Terminal 1: Backend Service (Port 8000)

```powershell
cd "C:\Users\Aditya\Desktop\Climaforge Workspace"
.\backend\.venv\Scripts\python -m uvicorn app.main:app --app-dir backend --host 0.0.0.0 --port 8000 --reload
```

- **Health Diagnostics**: [http://localhost:8000/health](http://localhost:8000/health)
- **Interactive OpenAPI Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **Scenarios Endpoint**: [http://localhost:8000/api/scenarios](http://localhost:8000/api/scenarios)
- **Scenario Analysis Endpoint**: `POST http://localhost:8000/api/scenarios/{scenario_id}/analyze`

### Terminal 2: Frontend Service (Port 5173)

```powershell
cd "C:\Users\Aditya\Desktop\Climaforge Workspace\frontend"
npm run dev
```

- **Operations Dashboard**: [http://localhost:5173](http://localhost:5173)

---

## Demonstrating Milestone 2 in the Operations Dashboard

1. Launch both backend (port 8000) and frontend (port 5173).
2. Open [http://localhost:5173](http://localhost:5173). The top bar indicates `BACKEND CORE ONLINE (HTTP 200)`.
3. In the scenario dropdown on the **Overview** tab, select **"Severe Flash Flood Surge (Zone Inundation)"** or **"Moderate Monsoon Inflow (48h Warning)"**.
4. Click the blue **"Run Flood Analysis"** button in the control bar.
5. Observe the live deterministic results:
   - **KPI Cards** update with calculated Peak Risk Index (0–100 scale), evaluated zones count, and qualified priority hotspots.
   - **Catchment Zone Table** updates with authoritative 0–100 risk scores, normalized `[0.0-1.0]` indices, canonical severity bands (`CRITICAL`, `HIGH`, `MEDIUM`, `LOW`), hotspot tags (score &ge; 50.0), and the dominant critical cause (e.g. Rainfall Inundation, Drainage Constriction).
   - **Algorithm 3 Exposure Panel** renders multi-factor vulnerability assessment (`ImpactScore` [0.0–1.0], Population, Infrastructure, Arterial Roads, and Emergency Corridors) for all qualified hotspots.
6. Select **"Dry Season Baseline (Nominal Flow)"** and click **"Run Flood Analysis"**:
   - Notice the status updates to `MONITORING_ONLY` (0 hotspots qualified).
   - A verified notification explains that downstream exposure and cascade analysis is safely suspended per Algorithm 2 specification.
7. Open the **Audit Log** tab from the sidebar to inspect the authentic `ANALYSIS_RUN` event recorded on the backend.

---

## Milestone 2 Implementation Overview

CLIMAFORGE Milestone 2 implements the pure deterministic risk engine covering Algorithms 0–3:
- **Algorithm 0 (`alg0_data_prep.py`)**: Type/bounds validation, fixed reference range normalization, missing required feature handling (`DATA_INSUFFICIENT`), and missing optional feature tracking.
- **Algorithm 1 (`alg1_flood_risk.py`)**: Deterministic 0–100 FloodRisk score calculation, dynamic weight rescaling when optional inputs are omitted, canonical severity bands (`CRITICAL` &ge;75, `HIGH` &ge;50, `MEDIUM` &ge;25, `LOW` <25), and explainable factor breakdown.
- **Algorithm 2 (`alg2_hotspots.py`)**: Priority hotspot ranking at threshold 50.0; zero qualified zones triggers `MONITORING_ONLY` state and halts downstream analysis.
- **Algorithm 3 (`alg3_exposure.py`)**: Multi-factor impact and exposure calculation for hotspots only (weights: Population 0.35, Infrastructure 0.25, Road Network 0.20, Emergency Corridors 0.20), clearly separating normalized indices from raw physical counts.
- **API & UI Integration**: `POST /api/scenarios/{id}/analyze` and `POST /api/scenarios/run/adhoc` endpoints fully wired to the interactive operational dashboard.


---

## Milestone 16A: Authentication, Role-Based Access Control (RBAC), and Frontend Integration

CLIMAFORGE Milestone 16A delivers production-grade authentication, session management, and granular authorization spanning backend services and the React operations center:

- **M16A.1 (Configuration)**: Centralized security settings via Pydantic (`JWT_SECRET_KEY`, `JWT_ALGORITHM`, Argon2id memory/time parameters, token lifetimes).
- **M16A.2 (Database & Migrations)**: SQLAlchemy models (`users`, `refresh_tokens`) and Alembic migration infrastructure with UUID primary keys and indices.
- **M16A.3 (Core Security Services)**: Argon2id password hashing with timing attack mitigation, short-lived JWT access tokens, opaque refresh-token rotation with family replay protection and revocation.
- **M16A.4 (Authentication API & Secure Sessions)**:
  - `POST /api/auth/login`: Rate-limited endpoint issuing short-lived JWT in JSON and opaque refresh token in HttpOnly cookie; double-submit CSRF cookie.
  - `POST /api/auth/refresh`: Atomic refresh token rotation with replay detection and CSRF enforcement.
  - `POST /api/auth/logout`: Idempotent session family revocation and cookie clearance.
  - `GET /api/auth/me`: Profile retrieval with live database verification.
- **M16A.5 (Role-Based Access Control & Scenario Authorization)**:
  - Five canonical roles: `ADMIN`, `OPERATOR`, `ANALYST`, `AUDITOR`, `VIEWER`.
  - 15 granular permissions (`scenario.*`, `chatbot.*`, `ml.*`, `audit.*`, `intervention.*`, `admin.*`).
  - Scenario-level authorization with optional explicit, unexpired grants (`ScenarioAccessGrant`).
- **M16A.6 (Frontend Authentication & RBAC Integration)**:
  - **In-Memory Token Storage**: Strict isolation in JavaScript memory (`auth.ts`); zero tokens written to `localStorage` or `sessionStorage`.
  - **HttpOnly Refresh Cookies & CSRF**: Automatic `credentials: 'include'` and `X-CSRF-Token` injection on mutating requests.
  - **Concurrent Refresh Deduplication**: Atomic promise deduplication prevents replay-protection revocation from simultaneous 401s.
  - **Centralized Auth State**: `AuthProvider` supporting `loading`, `authenticated`, `unauthenticated`, and `session-expired` states.
  - **Role-Aware UI & Action Guarding**: Dynamic role badges (`ADMIN`, `OPERATOR`, `VIEWER`), locked sidebar tabs for restricted modules, "Run Analysis" permission checks, and `UnauthorizedView`.
  - **Testing**: 250 backend pytest tests + 30 frontend Vitest integration tests.
- **M16A.7 (Cross-Tab Authentication Coordination & Session Hardening)**:
  - **Web Locks Exclusive Refresh Coordination**: Implemented `navigator.locks.request('climaforge_refresh_lock', ...)` to guarantee strict FIFO mutual exclusion for token refresh across all open browser tabs.
  - **Shared Cookie Jar Synchronization**: Sequential lock acquisition ensures waiting tabs send the freshly rotated refresh token cookie, completely eliminating concurrent refresh-token replay collisions and accidental token-family revocations.
  - **Zero-Secret Cross-Tab Event Bus**: Implemented `new BroadcastChannel('climaforge_auth')` transmitting exclusively non-sensitive lifecycle events (`REFRESH_COMPLETED`, `AUTH_LOGOUT`, `SESSION_EXPIRED`, `AUTH_LOGIN`).
  - **Strict Bearer Token Isolation**: Access tokens exist exclusively in the private JavaScript heap memory of each tab. Access tokens, refresh tokens, cookies, passwords, and CSRF secrets are **NEVER** broadcast over BroadcastChannel and **NEVER** persisted to web storage.
  - **Multi-Tab Lifecycle Synchronization**: Immediate cross-tab logout and session expiration propagation without redirect loops or stale credential restoration.
  - **Safe Browser Compatibility Fallback**: Automatic feature detection and graceful fallback execution for environments lacking Web Locks or BroadcastChannel.
  - **Multi-Context Test Suite**: 43 frontend tests (including genuine multi-context browser tab simulation with concurrent lock contention and backend replay verification) + 250 backend tests.

---

## Milestone 5: Advisory AI Gateway (Nugen)

Milestone 5 delivers a modular, secure, server-side Nugen Advisory AI Gateway providing non-authoritative decision support, grounded explanations, and intervention recommendations:

- **Strict Authority Separation**:
  - The deterministic risk engine (Algorithms 0–13) remains 100% authoritative.
  - Nugen acts strictly as an advisory layer; it cannot change risk scores, mutate severity bands, alter cascade propagation probabilities, bypass resource budget checks, reorder feasible interventions, or modify scenario definitions.
  - All Nugen outputs carry explicit non-authoritative markers (`NON-AUTHORITATIVE ADVISORY`) and mandatory human-review disclaimers in API responses and frontend views.
- **Modular Server-Side Provider Adapters**:
  - **Deterministic Mock Provider**: Offline, reproducible advisory recommendations and natural language explanations based on grounded scenario context.
  - **OpenAI-Compatible Chat Completions Provider**: Live server-side LLM connectivity with configurable timeouts (`NUGEN_TIMEOUT_SECONDS`), models, and credentials.
  - **Deterministic Fallback Provider**: Activated automatically when the live provider times out, returns HTTP 5xx errors, encounters connection refusal, is disabled, or returns malformed/unparseable JSON. Grounded entirely in verified Algorithm 0–13 outputs without hallucinations.
- **Algorithms 10 & 13 Integration**:
  - Algorithm 10 evaluates `nugen_agreement` against the top-ranked feasible action without altering deterministic ranking.
  - Algorithm 13 embeds advisory metadata (`ai_status`, `nugen_advisory_status`, `nugen_recommendation`, `human_review_warning`) into the Command Decision Card.
- **Grounded Chatbot API & Gateway Status**:
  - `POST /api/chatbot/message`: Backward-compatible grounded decision support endpoint protected by `PERM_CHATBOT_ASK`.
  - `GET /api/chatbot/status`: Public capability and mode inspection endpoint reporting provider configuration without leaking credentials.
- **Secret Isolation**:
  - API keys (`NUGEN_API_KEY`, `CHATBOT_API_KEY`) are isolated to backend server configuration and never exposed to the frontend or included in API responses.
- **Test Suite**:
  - 15 dedicated scenarios covering mock, OpenAI-compatible completions, timeout fallback, unavailable 503 fallback, invalid response fallback, network failure fallback, grounded content verification, missing telemetry handling, disabled mode, authority preservation, RBAC enforcement, secret isolation, chatbot compatibility, and Alg 0–13 regression.

---

## Milestone 6: Emergency Chatbot Online (Alert & Safe Route)

Milestone 6 delivers citizen-accessible hazard warnings, deterministic evacuation routing, and emergency shelter discovery grounded in authoritative scenario risk and cascade outputs:

- **Pre-Calamity Citizen Alert System**:
  - Classifies hazard severity into citizen-facing tiers: `CRITICAL` ($\ge 75.0$), `HIGH` ($50.0 \le \text{score} < 75.0$), `MEDIUM` ($25.0 \le \text{score} < 50.0$), and `LOW` ($< 25.0$).
  - Directly extracts dominant physical hazard causes (`dominant_cause`) from Algorithm 1/2 factor breakdowns without hallucination.
  - Generates clear, non-alarmist warning descriptions and actionable emergency instructions.
- **Safe Evacuation Routing Engine**:
  - Calculates deterministic shortest safe paths from hazard zones to confirmed shelters (`SafePoint`) using NetworkX Dijkstra traversal.
  - Dynamically prunes flooded/impaired transportation nodes identified as `FAILING` ($p \ge \tau = 0.30$) in Algorithm 5 cascade analysis.
  - Automatically identifies and diverts onto safe elevated perimeter bypass corridors (e.g. `ROAD-PERIM-01`) when low-elevation arterial roads are flooded.
  - Fail-Closed Safety: Returns explicit status `BLOCKED` with detailed obstacle listings and shelter-in-place instructions when all exit corridors are severed.
  - Strictly asserts `is_live_confirmed: false` and `is_simulated: true` across all route plans.
- **Authenticated Scenario-Scoped API Endpoints**:
  - `GET /api/scenarios/{scenario_id}/alerts`: Pre-calamity alerts guarded by `PERM_SCENARIO_READ`.
  - `GET /api/scenarios/{scenario_id}/safe-points`: Shelter discovery guarded by `PERM_SCENARIO_READ`.
  - `POST /api/scenarios/{scenario_id}/evacuation-route`: Route planning guarded by `PERM_CHATBOT_ASK`.
  - `GET /api/scenarios/{scenario_id}/evacuation-route/{route_id}`: Cached route plan retrieval.
- **Frontend Emergency UI Integration**:
  - `EmergencyChatbotTab.tsx`: Citizen alert warning cards, interactive shelter routing selector, turn-by-turn waypoint guidance, and simulation badges.
  - `RiskMapTab.tsx`: Active evacuation corridor overlays and designated safe refuge inspector cards.
- **Automated Verification**:
  - 18 new automated backend tests (total 288 passed, 0 failed).
  - 4 new frontend tests (total 48 passed, 0 failed).
  - 7 genuine Playwright Chromium E2E tests (100% passed).

## Milestone 7: Panic Phase, Offline Cache & Client SOS Outbox

Milestone 7 delivers mission-critical offline resilience, browser IndexedDB storage, and duplicate-safe emergency SOS distress dispatch for network-interrupted disaster environments:

- **Native Client IndexedDB Offline Store (`frontend/src/services/offlineStorage.ts`)**:
  - `climaforge_offline_store` (v1) with three typed object stores:
    - `scenario_cache`: Persists scenario metadata, pre-calamity alerts, and emergency shelters with expiration timestamps.
    - `route_cache`: Persists active evacuation corridors, turn-by-turn waypoints, and hazard bypass geometries.
    - `sos_outbox`: Durable FIFO queue for pending citizen SOS distress reports with UUID keys and state tracking (`NOT_SENT` vs `ACKNOWLEDGED`).
  - Strict security boundary: Zero access tokens, refresh tokens, or user credentials stored in IndexedDB.
  - Graceful degradation: Explicit warnings when IndexedDB is blocked or disabled by private browsing modes.
- **Offline Synchronization Service (`frontend/src/services/offlineSync.ts`)**:
  - Online/offline window event listeners with real-time connectivity status subscriptions.
  - Automatic reconnection outbox drainage: Transmits pending distress signals upon network restoration without user intervention.
  - Retry-safe outbox retention: Incidents remain durably queued as `NOT_SENT` during network or server failures (zero silent loss).
- **High-Contrast Panic Phase UI (`frontend/src/components/EmergencyChatbotTab.tsx`)**:
  - Dedicated "Enter Panic Phase (Offline SOS)" toggle and "Simulate Offline / Network Loss" controls.
  - Prominent "OFFLINE SURVIVAL MODE" banner displaying cache age and emergency instructions.
  - Citizen SOS Distress Dispatch form supporting incident categorization (`RISING_WATER`, `MEDICAL_EMERGENCY`, `STRANDED_PERSONS`, `ROAD_BLOCKED`), urgency rating (`CRITICAL`, `HIGH`, `MEDIUM`), and coordinates.
  - Real-time client outbox queue inspector visualizing synchronization states (`NOT_SENT` in amber, `ACKNOWLEDGED` in emerald).
- **Authenticated, Idempotent Incident Synchronization API (`backend/app/routers/incidents.py`)**:
  - `POST /api/scenarios/{scenario_id}/incidents/sync`: Accepts batch incident synchronization payloads guarded by `PERM_SCENARIO_READ`.
  - `GET /api/scenarios/{scenario_id}/incidents`: Retrieves registered scenario incidents.
  - Durable SQLite persistence: `incidents` table managed via Alembic migration (`0004_incidents_table.py`) with unique client UUID `incident_id`.
  - Idempotency & Deduplication: Atomic duplicate recognition and safe handling of concurrent identical submissions without HTTP 500 crashes.
  - Cross-scenario isolation: Prevents incident identifier collisions across distinct emergency scenarios.
  - Audit logging: Emits authentic `INCIDENT_SYNC` events to `SESSION_AUDIT_LOGS` only after durable database commit.
- **Automated Verification**:
  - 14 new automated backend tests (`test_incidents_and_offline.py` — total 302 passed, 0 failed, 100%).
  - 8 new frontend unit/integration tests (`m7_offline_sos.test.tsx` — total 56 passed, 0 failed, 100%).
  - 7 genuine Playwright Chromium multi-tab E2E tests (100% passed).
  - Frontend build: TypeScript & Vite production bundle compiled in <1s with 0 errors.


---

## Milestone 8: Final System Integration, Complete Project Validation & Hackathon Submission Readiness

Milestone 8 completes the CLIMAFORGE platform with end-to-end multi-scene integration, automated real-browser demonstration suites, complete technical documentation, and a final hackathon submission package:

- **6-Scene End-to-End Operational Integration**:
  - **Scene 1 (Baseline Catchment Monitoring)**: `scenario-baseline`, zero hotspots, `SKIPPED_MONITORING_ONLY` status, 100% operational assets.
  - **Scene 2 (Flash Flood Risk Escalation)**: `scenario-flash-flood`, Alg 1 risk score 82.4 `CRITICAL`, dominant hazard cause analysis, active inundation zones.
  - **Scene 3 (Probabilistic Infrastructure Cascade)**: Alg 4/5 Noisy-OR failure propagation, substation and water treatment plant failures, DFS cycle safety verification.
  - **Scene 4 (Tactical Intervention Knapsack & Decision Card)**: Alg 8 0/1 Knapsack resource allocation, Alg 10 multi-criteria ranking, Alg 13 Command Decision Card synthesis, strict Nugen advisory AI separation.
  - **Scene 5 (Citizen Pre-Calamity Alerts & Evacuation Routing)**: Citizen-facing severity tiers, Dijkstra shortest-safe-path hazard-avoidance routing avoiding flooded arterial corridors, turn-by-turn guidance, simulation disclaimers.
  - **Scene 6 (Offline Panic Resilience & Client SOS Outbox)**: Native IndexedDB caching, offline panic survival mode, client SOS outbox queuing `NOT_SENT` reports, automatic background reconnection sync `ACKNOWLEDGED`, duplicate prevention.
- **Automated Real-Browser Demonstration Suite (`frontend/e2e/m8_end_to_end_demo.spec.ts`)**:
  - Executes the complete 6-scene operational workflow in real headless Chromium via Playwright in ~2.3 seconds.
  - 100% deterministic assertion coverage verifying API contracts, state transitions, DOM elements, and accessibility attributes.
- **Demonstration & Rehearsal Package (`docs/demo/`)**:
  - `DEMO_RUNBOOK.md`: Step-by-step instructions for live presentation or video recording across all 6 scenes.
  - `SCENARIO_MATRIX.md`: Comprehensive reference matrix for `scenario-baseline`, `scenario-flash-flood`, and `scenario-monsoon-alert`.
  - `REHEARSAL_CHECKLIST.md`: Pre-flight, in-run, and contingency playbooks for live pitching.
- **Comprehensive Hackathon Video Production Package (`docs/hackathon_video/`)**:
  - `VIDEO_SCRIPT.md`: 5:30 word-for-word voiceover script with audio cues and timing markers.
  - `VIDEO_STORYBOARD.md`: Shot-by-shot visual breakdown, camera pans, and UI callout overlays.
  - `DEMO_RUNBOOK.md`, `SCREEN_RECORDING_CHECKLIST.md`, `JUDGING_CRITERIA_MAPPING.md`, `VIDEO_EVIDENCE_CHECKLIST.md`.
- **Hackathon Submission Package (`docs/hackathon_submission/`)**:
  - `PROJECT_OVERVIEW.md`, `TECHNICAL_ARCHITECTURE.md`, `INNOVATION_AND_IMPACT.md`, `DEMO_GUIDE.md`, `LIMITATIONS_AND_FUTURE_SCOPE.md`, `FINAL_TEST_REPORT.md`, `SUBMISSION_CHECKLIST.md`.
- **Full Quality Gate Verification**:
  - **Backend Pytest**: 302/302 tests passed (100%).
  - **Frontend Vitest**: 56/56 unit and integration tests passed (100%).
  - **Playwright E2E**: 8/8 real Chromium tests passed (7 multi-tab auth + 1 end-to-end demo, 100%).
  - **ESLint**: Clean; 0 errors.
  - **Frontend Production Build**: Vite + TypeScript compiled successfully.
