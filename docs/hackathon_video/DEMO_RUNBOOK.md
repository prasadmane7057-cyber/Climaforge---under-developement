# CLIMAFORGE — Hackathon Demonstration Runbook & Recording Guide
## Operational Execution Procedures for Video Demonstrations

**Target Video Duration:** 5:45 (345 Seconds) | **Resolution:** 1080p (1920x1080 @ 60fps)  
**Applicable Hackathon:** Round 2 Prototype Video Submission  
**Canonical Reference:** Aligned with `VIDEO_SCRIPT.md` and `VIDEO_STORYBOARD.md`

---

### PRE-FLIGHT SYSTEM SETUP & ENVIRONMENT PREPARATION

#### 1. Software & Tooling Prerequisites
* **Web Browser**: Google Chrome or Chromium (latest stable).
* **Screen Recording Software**: OBS Studio or Windows Game Bar (`Win+Alt+R`) configured to:
  * Resolution: 1920x1080 (1080p).
  * Frame Rate: 60 fps (or 30 fps consistent).
  * Audio: Clear condenser microphone input, noise suppression enabled.
* **Terminal Emulator**: Windows Terminal with PowerShell 7+ or Command Prompt.
* **Working Directory**: `c:\Users\x\Desktop\New folder\Climaforge---under-developement-ui-redesign`

#### 2. Clean Service Initialization
Before starting the recording session, launch the backend and frontend in separate clean terminals:

**Terminal 1 — Authoritative Backend API Server**:
```powershell
cd "c:\Users\x\Desktop\New folder\Climaforge---under-developement-ui-redesign\backend"
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```
*Verification*: Open `http://127.0.0.1:8000/health` -> HTTP 200 `{"status": "ok", "version": "0.1.0"}`.

**Terminal 2 — Frontend Operations Center**:
```powershell
cd "c:\Users\x\Desktop\New folder\Climaforge---under-developement-ui-redesign\frontend"
npm run dev
```
*Verification*: Open `http://localhost:5173/` -> CLIMAFORGE Command Dashboard displays cleanly in dark theme.

#### 3. Browser State Preparation
* Reset browser zoom to **100%** (`Ctrl+0`).
* Open DevTools (`F12`) docked to the right or bottom; navigate to **Network** tab (to prepare for offline toggling in Scene 6).
* Clear any stale IndexedDB test databases: DevTools -> Application -> Storage -> Clear site data (or run `indexedDB.deleteDatabase('climaforge_offline_store')` in console).
* Ensure no personal bookmarks bar or private tabs are visible.

---

### SCENE-BY-SCENE DEMONSTRATION RUNBOOK

#### SCENE 1: HOOK — THE CLIMATE CRISIS & EARLY WARNING URGENCY (0:00 – 0:35)
* **Screen to Open**: Title slide or CLIMAFORGE Overview dashboard (`http://localhost:5173/`).
* **Interaction**:
  * Keep camera on speaker or display title overlay (*CLIMAFORGE: Hyperlocal Climate Risk Engine & Resilient Emergency Operations*).
  * At 0:20, smoothly cross-fade to the live CLIMAFORGE Operations Dashboard showing the tactical map and scenario header.
* **Expected Visible Result**: Clean, dark-mode command center with active scenario `scenario-flash-flood` or baseline.
* **Narration to Speak**: See `VIDEO_SCRIPT.md` Scene 1.
* **Evidence Shown**: Headline climate vulnerability metrics and initial view of the dark-mode operations dashboard.

---

#### SCENE 2: CLIMAFORGE INTRO & DUAL-TIER SYSTEM ARCHITECTURE (0:35 – 1:15)
* **Screen to Open**: Main Dashboard (`http://localhost:5173/`).
* **Interaction**:
  1. Hover over the left sidebar navigation items: Overview, Risk Map, Cascade, Interventions, Emergency Assistant.
  2. Click on the Scenario Dropdown in the top header; reveal the available typed scenarios (`Flash Flood Emergency`, `River Surge`, `Urban Runoff`). Select `Flash Flood Emergency`.
  3. Mouse hover over the architectural safety banner at the top of the tab.
* **Expected Visible Result**: Scenario details populate with Riverside Industrial District, Central Ward, and Valley Heights telemetry.
* **Narration to Speak**: See `VIDEO_SCRIPT.md` Scene 2 (Explain the strict separation between deterministic math and advisory AI).
* **Evidence Shown**: Clean decoupled UI, live backend connectivity status (`Online - Connected`), scenario metadata card.

---

#### SCENE 3: FLOOD-RISK SCORING, HOTSPOTS & CONSEQUENCE CASCADE (1:15 – 2:05)
* **Screen to Open**: Overview Tab -> Consequence Graph Tab.
* **Interaction**:
  1. *Overview Tab*: Click the primary action button: **Run Flood Analysis**.
     * *Result*: KPI tiles update immediately; Riverside District displays Risk Score **82.4 / 100 (CRITICAL)**, Dominant Cause: **Extreme Precipitation Runoff**.
  2. *Sidebar*: Click **Consequence Graph**.
     * *Result*: Interactive NetworkX graph renders. Seed `Flood` node links to failing infrastructure nodes.
     * Click the red node `Drainage Network`. Drawer slides open showing failure probability $0.85$ and downstream connections.
     * Point to the cycle-breaking notice and Noisy-OR cascade transmission banner ($p=0.85$ to Drainage, $p=0.72$ to Hospital).
* **Narration to Speak**: See `VIDEO_SCRIPT.md` Scene 3.
* **Evidence Shown**: Live calculation output, mathematical cascade probabilities, cycle-safe topological traversal.

---

#### SCENE 4: INTERVENTION OPTIMIZATION & NUGEN ADVISORY ASSISTANT (2:05 – 2:50)
* **Screen to Open**: Interventions Tab (`http://localhost:5173/`).
* **Interaction**:
  1. Scroll through Feasible Interventions table, showing cost vs impact metrics.
  2. Highlight Intervention `I1: Deploy High-Capacity Mobile Pumping Units` ($42,000, 58.7% risk reduction, cascade length shrunk to 0).
  3. Highlight the **Command Decision Card** and point to the Nugen advisory badge showing agreement status and explicit non-authoritative disclaimers.
* **Narration to Speak**: See `VIDEO_SCRIPT.md` Scene 4.
* **Evidence Shown**: Alg 8/10/11/13 optimization tables, counterfactual simulation before/after metrics, Nugen advisory disclaimers.

---

#### SCENE 5: CITIZEN PRE-CALAMITY ALERTS & HAZARD-AVOIDANCE ROUTING (2:50 – 3:45)
* **Screen to Open**: Click sidebar item **Emergency Assistant** (`EmergencyChatbotTab.tsx`).
* **Interaction**:
  1. Show the top **Pre-Calamity Citizen Alerts**:
     * Riverside Industrial: `CRITICAL` alert card with flood warnings and dominant cause citation.
     * Valley Heights: `LOW / WATCH` alert card.
  2. Scroll to the **Safe Evacuation Route Planner**:
     * Origin Zone: Select `ZONE-001: Riverside Industrial District (Elev: 4.5m)`.
     * Destination Safe Refuge: Select `Auto-Select Nearest Safe Shelter` (or `Northern High School`).
     * Click **Find Safe Route** (Button label: `Find Safe Route`).
  3. Inspect the resulting Route Card:
     * Status pill: **`CONFIRMED SAFE (SIMULATED)`**.
     * Metrics: Distance `11.7 km`, Time `~16 mins`.
     * Hazard Avoidance Banner: `Avoided 1 flooded/failing infrastructure asset: Arterial Road Network (Road)`.
     * Turn-by-Turn Waypoint Strip: Rerouted through elevated perimeter bypass corridors.
     * Point out the simulation notice: `is_live_confirmed: false` and the explicit disclaimer.
* **Narration to Speak**: See `VIDEO_SCRIPT.md` Scene 5.
* **Evidence Shown**: Shortest safe path calculation, hazard node avoidance list, safe refuge facility details, and turn-by-turn waypoint guidance.

---

#### SCENE 6: OFFLINE PANIC PHASE, SOS QUEUE & AUTOMATIC SYNC (3:45 – 4:40)
* **Screen to Open**: Emergency Assistant Tab (`http://localhost:5173/`).
* **Interaction**:
  1. *Simulate Disconnection*:
     * Open browser DevTools Network tab -> change 'No throttling' to **Offline** (OR click the button **Enter Panic Phase (Offline SOS)**).
     * *Result*: The prominent amber banner appears:
       `OFFLINE SURVIVAL MODE: Live communications interrupted. Guidance served from local device cache.`
  2. *Demonstrate Cached Data*:
     * Point out that pre-calamity alerts and evacuation route waypoints remain fully accessible from `climaforge_offline_store` without blanking out.
  3. *Submit Offline SOS Distress Report*:
     * In the **Emergency SOS Distress Dispatch** form:
       * Incident Type: Select `RISING_WATER (Water Intrusion)`.
       * Urgency Priority: Select `CRITICAL (Immediate Life Threat)`.
       * Location Zone: Select `ZONE-001: Riverside Industrial District`.
       * Distress Situation: Type: `Rapid flood inundation reaching second floor, family trapped on roof.`
     * Click **Record Emergency SOS (Queue Outbox)**.
     * *Result*: The report appears immediately in the **Client SOS Outbox Queue** with an amber pill: **`NOT_SENT`** and UUID.
  4. *Demonstrate Durability*:
     * Refresh the browser page (`F5`) while still offline.
     * *Result*: The page loads, the outbox immediately rehydrates from IndexedDB, and the item remains safely intact with status `NOT_SENT`.
  5. *Simulate Reconnection & Automatic Sync*:
     * In DevTools Network tab, switch from **Offline** back to **No throttling** (Online) (or click **Sync Outbox**).
     * *Result*: The online listener fires immediately. The background service calls `POST /api/scenarios/{id}/incidents/sync`.
     * The status badge on the queued incident transitions smoothly from amber `NOT_SENT` to emerald **`ACKNOWLEDGED`**.
     * Green feedback notification appears confirming successful batch synchronization.
* **Narration to Speak**: See `VIDEO_SCRIPT.md` Scene 6.
* **Evidence Shown**: Network disconnection simulation, IndexedDB storage persistence, durable outbox queue, automatic background synchronization, and idempotent backend acknowledgement.

---

#### SCENE 7: TECHNICAL VERIFICATION & AUTOMATED TESTING (4:40 – 5:15)
* **Screen to Open**: Split screen showing running Terminal outputs and Swagger UI (`http://127.0.0.1:8000/docs`).
* **Interaction**:
  1. In Terminal, show completed test runs:
     * `python -m pytest backend/tests -q`: `302 passed in 34s`.
     * `npm --prefix frontend test -- --run`: `56 passed in 5s`.
     * `npm --prefix frontend run test:e2e`: `8 passed in 16s` (including full 6-scene operational workflow demo and Web Locks multi-tab coordination).
     * `npm --prefix frontend run build`: `Built in 747ms (0 errors)`.
  2. Point out that all data is durably stored in the SQLite database table `incidents` with RFC 4122 UUID primary keys and Alembic migration tracking.
* **Narration to Speak**: See `VIDEO_SCRIPT.md` Scene 7.
* **Evidence Shown**: Authentic terminal outputs with timestamps, passing test summaries, and zero compilation errors.

---

#### SCENE 8: CLIMATE IMPACT, FEASIBILITY, LIMITATIONS & CLOSING (5:15 – 5:45)
* **Screen to Open**: Presenter camera or closing infographic slide.
* **Interaction**:
  * Presenter speaks directly to camera.
  * Display project GitHub repository URL, MIT license badge, and team acknowledgments.
  * State limitations honestly: prototype relies on synthetic GIS topology and lumped hydrology; production deployment requires certified municipal LiDAR DEMs and CAD 911/112 links.
* **Narration to Speak**: See `VIDEO_SCRIPT.md` Scene 8.
* **Evidence Shown**: Impact metrics, project repository links, open-source license.

---

### FALLBACK CONTINGENCY PROCEDURES

If an unexpected condition arises during live recording, apply these pre-tested fallbacks immediately without restarting the entire shoot:

| Potential Failure Mode | Root Cause | Instant Fallback Procedure |
| :--- | :--- | :--- |
| **Backend server fails to start or crashes** | Port conflict on 8000 or unapplied migration | 1. Run `python -m alembic upgrade head` inside `backend/`.<br>2. Run `Get-Process python \| Stop-Process -Force` to clear stale locks.<br>3. Restart uvicorn on port 8000. |
| **Internet connection unavailable during recording** | Offline venue / network drops | No issue: CLIMAFORGE is 100% self-contained! All deterministic algorithms, SQLite database, mock Nugen provider, and IndexedDB operate completely offline on `localhost`. |
| **Nugen LLM API key / provider unreachable** | External API rate limit or outage | CLIMAFORGE features built-in **Deterministic Fallback Engine** (`mode="deterministic_fallback"`). The chatbot will continue responding grounded in Alg 0–13 outputs without error. |
| **Browser DevTools Offline mode fails to trigger event** | Browser throttle bug | Use the in-app toggle: Click **Enter Panic Phase (Offline SOS)** in the Emergency tab header. This triggers the same survival mode and local outbox workflows programmatically. |
| **IndexedDB blocked by Incognito / Private Window** | Browser privacy policy | Switch to a standard browser profile window where IndexedDB has full disk persistence rights. |
