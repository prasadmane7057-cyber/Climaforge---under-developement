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

Run `pytest` to verify the `/health` endpoint and all Pydantic domain contracts:

```powershell
.\backend\.venv\Scripts\pytest backend
```

Expected output: `20 passed in ~1s`.

### 2. Verify Frontend Production Build

Run the TypeScript typechecker and Vite production bundler:

```powershell
cd frontend
npm run build
cd ..
```

Expected output: `✓ built in ~600ms` with 0 TypeScript diagnostics.

---

## Starting the Development Services

Run the backend and frontend services in separate Windows PowerShell terminals:

### Terminal 1: Backend Service (Port 8000)

```powershell
cd "C:\Users\Aditya\Desktop\Climaforge Workspace"
.\backend\.venv\Scripts\python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

- **Health Diagnostics**: [http://localhost:8000/health](http://localhost:8000/health)
- **Interactive OpenAPI Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)

### Terminal 2: Frontend Service (Port 5173)

```powershell
cd "C:\Users\Aditya\Desktop\Climaforge Workspace\frontend"
npm run dev
```

- **Operations Starter Screen**: [http://localhost:5173](http://localhost:5173)

---

## Verifying End-to-End Health in PowerShell

While the backend is running, verify the `/health` endpoint using PowerShell `Invoke-RestMethod`:

```powershell
Invoke-RestMethod -Uri "http://localhost:8000/health" | ConvertTo-Json -Depth 4
```

Example response:
```json
{
  "status": "healthy",
  "app_name": "CLIMAFORGE Backend",
  "version": "0.1.0",
  "environment": "development",
  "timestamp": "2026-10-28T12:50:00.000Z",
  "subsystems": {
    "api_server": "operational",
    "deterministic_calculation_core": "ready",
    "nugen_advisory_layer": "mock_provider (advisory only)",
    "persistence": "ready (in-memory / sqlite)"
  },
  "disclaimer": "SYNTHETIC / ILLUSTRATIVE DATA ONLY — Milestone 0 Prototype"
}
```

---

## Milestone 0 Status & Next Phase

- **Milestone 0**: Complete. Monorepo established, schemas validated, `/health` implemented, frontend connection screen built and verified.
- **Milestone 1**: Dashboard Shell and Navigation (scheduled next).
