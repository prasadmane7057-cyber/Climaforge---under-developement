# CLIMAFORGE — Complete Integration & Demonstration Runbook
## Milestone 8: End-to-End Operational Workflow & Live Rehearsal

This runbook guides operators, presenters, and evaluators through a repeatable, end-to-end demonstration of the six core operational scenes in CLIMAFORGE.

---

### PRE-FLIGHT VERIFICATION & ENVIRONMENT STARTUP

#### 1. Start Backend Server
```powershell
cd "c:\Users\x\Desktop\New folder\Climaforge---under-developement-ui-redesign\backend"
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```
- Health Check: Open `http://127.0.0.1:8000/health` -> verify status is `ok`.

#### 2. Start Frontend Server
```powershell
cd "c:\Users\x\Desktop\New folder\Climaforge---under-developement-ui-redesign\frontend"
npm run dev -- --port 5173
```
- Open `http://localhost:5173/` in Google Chrome or Chromium.

---

### SCENE-BY-SCENE REPEATABLE DEMONSTRATION WORKFLOW

#### SCENE 1: BASELINE MONITORING & ZERO-HOTSPOT HANDLING
1. **Select Baseline Scenario**:
   - In the header scenario selector dropdown, select `Dry Season Baseline (Nominal Flow)` (`scenario-baseline`).
2. **Observe Nominal State**:
   - Note the scenario summary: 4 zones, 0 hotspots, highest risk score 0.18 (`LOW`).
   - Notice the telemetry table shows all zones with low rainfall ($4.0\text{--}18.0\text{ mm}$) and safe water levels ($0.1\text{--}0.3\text{ m}$).
3. **Trigger Deterministic Analysis**:
   - Click the blue button **Run Flood Analysis**.
   - *Expected Result*: The calculation finishes instantly.
   - Hotspot count remains `0`.
   - Algorithm 2 evaluates threshold $\tau_{\text{hotspot}} = 50.0$ and finds no zones qualify.
   - The cascade engine displays status: `SKIPPED_MONITORING_ONLY`.
   - No unnecessary alerts or emergency orders are generated.

---

#### SCENE 2: FLOOD RISK ESCALATION & HAZARD DRIVERS
1. **Select Flood Scenario**:
   - In the header scenario selector, switch to `Extreme Monsoonal Inundation & River Surge (Flash Flood Emergency)` (`scenario-flash-flood`).
2. **Execute Deterministic Risk Core**:
   - Click **Run Flood Analysis**.
3. **Inspect Escalation Metrics**:
   - Overall scenario risk jumps to **CRITICAL**.
   - Riverside Industrial District (`ZONE-001`) registers canonical risk score **82.4 / 100 (CRITICAL)**.
   - Dominant Hazard Cause is clearly identified: **Extreme Precipitation (Rainfall)** with $112.5\text{ mm/hr}$ inflow.
   - Algorithm 2 qualifies `ZONE-001` as Hotspot #1, transitioning the pipeline into cascade and intervention evaluation.

---

#### SCENE 3: INFRASTRUCTURE CASCADE & NOISY-OR PROPAGATION
1. **Navigate to Consequence Graph Tab**:
   - In the sidebar, click **Consequence Graph** (`M3`).
2. **Inspect Interactive Network Topology**:
   - Observe the directed dependency graph: Seed node `Flood` links directly to `Drainage Network` and `River Basin`.
   - Observe failing infrastructure nodes marked in bold crimson:
     - `Drainage Network`: Failure probability $p = 0.85$ (`FAILING`).
     - `Arterial Road Network`: Failure probability $p = 0.72$ (`FAILING`).
     - `Emergency Access Route`: Failure probability $p = 0.55$ (`FAILING`).
     - `Hospital Emergency Hub`: Failure probability $p = 0.38$ (`WATCH`).
3. **Inspect Node Criticality & Cycle Handling**:
   - Click on the node `Drainage Network` to open the telemetry drawer.
   - Review Algorithm 6 Criticality Ranking: `Drainage Network` is ranked #1 Critical Node with composite score $0.88$.
   - Point to the Cycle Audit Log demonstrating that deterministic DFS cycle breaking pruned recursive loops without corrupting topological traversal.

---

#### SCENE 4: INTERVENTION DECISION SUPPORT & NUGEN ADVISORY
1. **Navigate to Interventions Tab**:
   - In the sidebar, click **Interventions** (`M4`).
2. **Review Resource Allocation & Feasibility**:
   - Review the depot inventory allocation ($42,000 budget, 4 pump units).
   - Algorithm 10 evaluates feasibility and budget constraints across candidate actions ($I_1, I_2, I_3, I_4$).
3. **Inspect Multi-Criteria Ranking & Counterfactuals**:
   - Observe top-ranked candidate: **I1: Deploy High-Capacity Mobile Pumping Units** with composite score $0.862$.
   - Review the Counterfactual What-If table:
     - Baseline Cascade Risk: $0.628$ $\rightarrow$ Mitigated Risk: $0.259$ (**-58.7% relative reduction**).
     - Cascade Length: reduced from $3 \rightarrow 0$.
     - Surviving infrastructure assets: increased from $3 \rightarrow 7$.
4. **Inspect Authoritative Command Decision Card**:
   - View the synthesized Decision Card with operational sign-off requirements.
   - Point to the Nugen advisory badge: clearly explain that Nugen confirms agreement, but Algorithms 0–13 remain the sole mathematical authority.

---

#### SCENE 5: CITIZEN EMERGENCY RESPONSE & SAFE EVACUATION ROUTING
1. **Navigate to Emergency Chatbot Tab**:
   - In the sidebar, click **Emergency Chatbot** (`M5`).
2. **Review Citizen Pre-Calamity Alerts**:
   - Riverside Industrial: `CRITICAL` alert warning citizens of rapid flash flooding and canal overtopping.
   - Valley Heights: `LOW / WATCH` advisory.
3. **Calculate Safe Evacuation Route**:
   - In the Evacuation Route Planner:
     - Origin Zone: `ZONE-001: Riverside Industrial District`.
     - Destination Shelter: `SP-01: Northern High School Evacuation Shelter`.
     - Click **Calculate Safe Evacuation Route**.
4. **Inspect Flood-Pruned Shortest Safe Path**:
   - The route card renders with distance `11.7 km`, travel time `~16.4 mins`, and status `CONFIRMED SAFE (SIMULATED)`.
   - Point out the hazard avoidance tag: **Avoided 1 flooded/failing infrastructure asset: Arterial Road Network (Road)**.
   - The router automatically diverted traffic onto the elevated perimeter corridor (`ROAD-PERIM-01`).
   - Emphasize the simulation disclaimer: *Illustrative topological simulation data only.*

---

#### SCENE 6: OFFLINE PANIC RESILIENCE & SOS OUTBOX DRAINAGE
1. **Engage Panic Phase / Simulate Disconnection**:
   - Click the header button **Enter Panic Phase (Offline SOS)** (or toggle Chrome DevTools Network to 'Offline').
   - Observe the prominent amber banner:
     `OFFLINE SURVIVAL MODE: Live communications interrupted. Guidance served from local device cache.`
2. **Verify Offline Cache**:
   - Confirm that pre-calamity alerts, safe-point coordinates, and evacuation route waypoints remain readable directly from `climaforge_offline_store`.
3. **Queue Offline Distress Report**:
   - In the Emergency SOS form:
     - Incident Type: `RISING_WATER (Water Intrusion)`.
     - Urgency Priority: `CRITICAL (Immediate Life Threat)`.
     - Location Zone: `ZONE-001`.
     - Distress Description: `Floodwaters breaching front door, 4 citizens trapped on upper level.`
   - Click **Record Emergency SOS (Queue Outbox)**.
   - The report appears in the Client SOS Outbox Queue with an amber badge: `NOT_SENT`.
4. **Test Page Reload Durability**:
   - Refresh the browser (F5) while offline.
   - The outbox immediately rehydrates from IndexedDB; the distress report is intact and still marked `NOT_SENT`.
5. **Restore Connectivity & Verify Automatic Synchronization**:
   - Click **Exit Panic Phase** (or set DevTools Network back to 'Online').
   - Within 1–2 seconds, the background synchronization service fires automatically.
   - The status badge transitions from `NOT_SENT` to emerald **ACKNOWLEDGED**.
   - Confirmation notice appears: `Auto-sync complete: 1 incident(s) acknowledged`.
   - City dispatchers now have the record durably persisted in SQLite table `incidents` with zero duplicates.

---

### SAFE CLEANUP PROCEDURES
To return the environment to a pristine initial state after completing the demonstration:
1. In the Emergency Chatbot Tab, click the trash icon **Clear Acknowledged** in the outbox header to prune synced records from local IndexedDB.
2. If resetting the backend database is desired, restart the server; the persistent SQLite `app.db` maintains full data integrity.
3. No production or user configuration files are altered during this demonstration.

