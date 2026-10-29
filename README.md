# CLIMAFORGE — Climate-Flood Decision-Support Prototype

CLIMAFORGE is an emergency operations and decision-support prototype engineered to deliver deterministic, explainable calculations for flood risk, critical infrastructure cascades, intervention feasibility, and citizen emergency guidance.

> **IMPORTANT DISCLAIMER**  
> All demo data, threshold parameters, and risk values in Milestone 0 are **SYNTHETIC / ILLUSTRATIVE ONLY**.  
> The system does not claim real-world prediction accuracy, guaranteed evacuation times, or real-world emergency dispatch.

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
