# CLIMAFORGE: Live Demonstration & Video Guide
## Final Hackathon Submission Package — Demo Runbook

---

### 1. Quick Start & Demonstration Setup

The CLIMAFORGE demonstration can be executed in two ways:
1. **Automated Real-Browser Demonstration (Playwright):** Executes the entire 6-scene operational workflow in real Chromium in ~16 seconds.
2. **Interactive Manual Walkthrough:** Conducted via browser for live pitching or video recording.

#### Prerequisites
* Node.js v18+ and Python 3.11+
* Modern Chromium-based browser (Google Chrome, Microsoft Edge, Brave)
* Dependencies installed in `backend/` and `frontend/`

#### Launching the Servers for Manual Demonstration
```bash
# Terminal 1: Launch Backend (Port 8000)
cd backend
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload

# Terminal 2: Launch Frontend (Port 5173)
cd frontend
npm run dev
```
Navigate to `http://localhost:5173` in your browser.

#### Running the Automated Playwright Demonstration Suite
```bash
# Run headless automated demonstration covering all 6 scenes
npm --prefix frontend run test:e2e
```

---

### 2. Six-Scene Demonstration Workflow

```
+-----------------------------------------------------------------------------------------+
|                                6-SCENE DEMONSTRATION WORKFLOW                           |
+-----------------------------------------------------------------------------------------+
| Scene 1: Baseline Catchment Monitoring (Zero-risk calm conditions)                      |
| Scene 2: Extreme Flood Hazard Escalation (Alg 1 score 82.4 CRITICAL)                    |
| Scene 3: Probabilistic Infrastructure Cascade (Noisy-OR failure propagation)            |
| Scene 4: Tactical Intervention Knapsack & Decision Card (Alg 8 & Alg 13)               |
| Scene 5: Citizen Pre-Calamity Alerts & Hazard-Avoidance Routing (Dijkstra)             |
| Scene 6: Offline Panic Resilience & Client SOS Outbox Synchronization                   |
+-----------------------------------------------------------------------------------------+
```

---

#### Scene 1: Baseline Catchment Monitoring
* **Goal:** Demonstrate normal baseline municipal state before a storm.
* **Action:**
  1. In the top navigation bar, select scenario: **`scenario-baseline` (Baseline Catchment Monitoring)**.
  2. Inspect the **Overview** tab.
* **Observable Evidence:**
  * Risk Score: **`0.0 / 100`** with status **`LOW`**.
  * Hotspot Count: **`0`** active hotspots.
  * Status Badge: **`SKIPPED_MONITORING_ONLY`** (Algorithms skip expensive simulation when hazard thresholds are not breached).
  * Infrastructure Grid: 100% operational assets with green indicators.

---

#### Scene 2: Extreme Flood Hazard Escalation
* **Goal:** Demonstrate the deterministic multi-hazard physics engine during a catastrophic cloudburst.
* **Action:**
  1. Change scenario selector to: **`scenario-flash-flood` (Flash Flood Emergency)**.
  2. Inspect the updated metrics in the **Overview** and **Risk Map** tabs.
* **Observable Evidence:**
  * Authoritative Catchment Risk Score: **`82.4 / 100`** with badge **`CRITICAL`**.
  * Dominant Hazard Cause: **`Extreme Precipitation & Runoff Surges`**.
  * Active Hotspots: Multiple contiguous critical zones flagged in red (`ZONE-001: Riverside Industrial District`).
  * Risk Map Tab: Interactive SVG catchment topology highlighting elevation contours, river basins, and inundation vectors.

---

#### Scene 3: Probabilistic Infrastructure Cascade
* **Goal:** Reveal hidden lifeline vulnerabilities using Alg 4/5 Noisy-OR cascading failure modeling.
* **Action:**
  1. Navigate to the **Cascade** tab.
  2. Inspect the infrastructure dependency tree.
* **Observable Evidence:**
  * Initiating Event: Electrical Substation `INFRA-SUB-01` inundation.
  * Secondary Propagations: Water Treatment Plant `INFRA-WTP-01` loses power ($P = 0.85$), leading to Regional Hospital `INFRA-HOSP-01` entering emergency backup generator status ($P = 0.72$).
  * Cycle Safety: DFS cycle-prevention badge confirms zero infinite recursion risk across cyclic dependencies.

---

#### Scene 4: Tactical Intervention Knapsack & Decision Card
* **Goal:** Demonstrate Alg 8 0/1 Knapsack optimization and Alg 13 authoritative decision card synthesis, strictly separated from Nugen advisory AI.
* **Action:**
  1. Navigate to the **Interventions** tab.
  2. Inspect the Feasible Interventions table and the **Command Decision Card**.
* **Observable Evidence:**
  * Knapsack Allocation: Automatically selects optimal interventions within municipal budget limits (e.g., Deploy Inflatable Floodwall $75k, Mobilize High-Volume Dewatering Pumps $45k).
  * Expected Impact: Cascade length reduced by 2 hops; population at risk reduced by 64%.
  * Authoritative Separation: The Command Decision Card is marked as **Deterministic Engine Directive**. Below it, the **Nugen Advisory Panel** provides explanatory rationale with explicit **Non-Authoritative Simulation Disclaimers**.

---

#### Scene 5: Citizen Pre-Calamity Alerts & Hazard-Avoidance Routing
* **Goal:** Demonstrate citizen-facing safety features: pre-calamity alerts and Dijkstra hazard-pruned safe routing.
* **Action:**
  1. Navigate to the **Emergency Chatbot** tab.
  2. Review the **Pre-Calamity Citizen Alerts** grid.
  3. Under **Safe Evacuation Route Planner**, select Origin: `ZONE-001 (Riverside Industrial District)` and click **Find Safe Route**.
* **Observable Evidence:**
  * Pre-Calamity Alerts: Headline: *"CRITICAL FLASH FLOOD WARNING - IMMEDIATE ACTION REQUIRED"*; Driver: *"Extreme Precipitation"*; Disclaimer: *"SIMULATED ALERT ONLY"*.
  * Route Status: **`CONFIRMED SAFE (SIMULATED)`** with `is_live_confirmed: false`.
  * Hazard Bypass Active: Banner clearly states that the route dynamically avoided flooded zones and failing infrastructure (`ZONE-001`, `INFRA-SUB-01`), safely routing citizens via elevated ridge bypasses (`Arterial Bypass Corridors`).

---

#### Scene 6: Offline Panic Resilience & Client SOS Outbox Synchronization
* **Goal:** Prove that the platform survives complete network disconnection, queues emergency distress signals locally in IndexedDB, and synchronizes them idempotently upon reconnection.
* **Action:**
  1. In the **Emergency Chatbot** tab, locate the **Network Status & Offline Storage** badge.
  2. Fill out the **Report Emergency Distress (Panic SOS)** form:
     * Emergency Type: `RISING_WATER`
     * Urgency Priority: `CRITICAL`
     * Location Zone: `ZONE-001`
     * Description: *"Water rising past ground floor level. 4 residents trapped on roof."*
  3. Click **Record Emergency SOS (Queue Outbox)**.
  4. Inspect the **Client SOS Outbox Queue** card: the item is queued with status **`NOT_SENT`** and a unique UUID.
  5. Click **Sync Outbox** (simulating network reconnection).
* **Observable Evidence:**
  * Sync Feedback: *"Sync successful: 1 newly synced, 0 previously acknowledged."*
  * Outbox Status: The record transitions to green **`ACKNOWLEDGED`** with checkmark.
  * Deduplication Safety: Re-clicking Sync Outbox confirms zero duplicate records created on the backend.

---

### 3. Scenario Matrix Summary

| Scenario ID | Name | Risk Score | Severity | Hotspots | Intended Demo Purpose |
| :--- | :--- | :---: | :---: | :---: | :--- |
| `scenario-baseline` | Baseline Monitoring | 0.0 | LOW | 0 | Proves calm-state behavior & zero false alarms |
| `scenario-flash-flood` | Flash Flood Emergency | 82.4 | CRITICAL | 3 | Core demo: cascading failure, Knapsack, evacuation routing |
| `scenario-monsoon-alert` | Monsoon Surge Warning | 58.2 | MEDIUM | 1 | Demonstrates moderate warning and precautionary mitigation |

---

### 4. Troubleshooting & Rehearsal FAQ

* **Issue: Chatbot displays connection error.**
  * *Cause:* Advisory AI operates in mock mode if external OpenAI/Anthropic API keys are not supplied in `.env`.
  * *Fix:* The platform includes an automatic deterministic fallback mode that produces valid advisory responses even with zero API keys.
* **Issue: Browser reports Web Locks unsupported.**
  * *Cause:* Old browser or private window blocking storage APIs.
  * *Fix:* Use standard Google Chrome or Edge. The platform will fail closed safely rather than allowing corrupted state.
* **Issue: Port 8000 or 5173 in use.**
  * *Fix:* Terminate lingering python/node processes via PowerShell: `Get-Process python, node | Stop-Process -Force`.

