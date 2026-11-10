# CLIMAFORGE — Hackathon Round 2 Canonical Video Script
## Theme: AI For Climate Change | Target Runtime: 5:45 (345 Seconds)

> **Presenter Guidance**:
> - Pacing: Steady conversational speed (~130 words per minute).
> - Tone: Confident, mission-driven, and scientifically honest.
> - Transparency: Clearly state that all road networks and evacuation shelters in the prototype are synthetic simulation fixtures, not certified municipal facilities.

---

### SCENE 1: HOOK — THE CLIMATE CRISIS & EARLY WARNING URGENCY (0:00 – 0:35)
**Visual**: Presenter on camera or high-contrast title screen (*CLIMAFORGE: Hyperlocal Climate Risk Engine & Resilient Emergency Operations*). Transition quickly to satellite cloudburst radar overlay and the dark-mode CLIMAFORGE operations overview.

**Spoken Narration (0:00 – 0:35)**:
"Climate change is turning once-in-a-century cloudbursts into regular urban disasters. In low-elevation river catchments and dense cities, just forty-five minutes of extreme rainfall can submerge critical substations, drown drainage networks, and cut off lifeline hospitals.

The greatest danger isn’t just the rising water—it’s cascading infrastructure paralysis and delayed, uncoordinated decision-making. Emergency managers face fragmented spreadsheets, while citizens are left with vague alerts—or worse, total silence when cellular grids collapse.

We built **CLIMAFORGE**—an AI-assisted climate risk intelligence and disaster decision-support platform designed to protect both city commanders and vulnerable citizens during catastrophic floods."

---

### SCENE 2: CLIMAFORGE INTRO & DUAL-TIER SYSTEM ARCHITECTURE (0:35 – 1:15)
**Visual**: Full-screen CLIMAFORGE Command Dashboard at `http://localhost:5173/`. Presenter hovers over the left navigation bar (Overview, Risk Map, Cascade, Interventions, Emergency Assistant) and highlights the architecture callout.

**Spoken Narration (0:35 – 1:15)**:
"This is the CLIMAFORGE operational center, built with a high-performance Python FastAPI backend and a responsive React TypeScript frontend.

Our core architectural breakthrough is **The Strict Separation of Mathematical Authority and AI Advisory Guidance**.

In life-and-death disaster response, probabilistic generative AI models hallucinate. An LLM cannot be trusted to calculate flood depths or verify whether a bridge has collapsed.

CLIMAFORGE solves this with a two-tier design:
First, a **Deterministic Calculation Core**—fourteen rigorously engineered closed-form mathematical algorithms, Algorithms 0 through 13, computing flood risk, infrastructure cascades, and resource knapsacks with 100% reproducible precision.

Second, **Nugen**, our grounded Advisory AI Gateway. Nugen provides plain-language briefings and strategic advice to commanders, but it is strictly non-authoritative. It can never alter mathematical outputs, route coordinates, or safety classifications."

---

### SCENE 3: FLOOD-RISK SCORING, HOTSPOTS & CONSEQUENCE CASCADE (1:15 – 2:05)
**Visual**: Select `scenario-flash-flood`. Click **Run Flood Analysis**. Overview tab updates with KPI metrics. Switch to **Cascade Tab** showing the interactive NetworkX infrastructure graph; click the red `Drainage Network` node to open the inspector drawer.

**Spoken Narration (1:15 – 2:05)**:
"Let’s see the engine in action during an active cloudburst scenario.

Selecting our Flash Flood Emergency scenario, Algorithms 0 through 3 ingest rainfall, soil saturation, and river stage telemetry. Riverside Industrial District immediately registers a **CRITICAL risk score of 82.4 out of 100**, driven by severe precipitation runoff.

Moving to the **Cascade Tab**, Algorithms 4 and 5 construct a probabilistic Noisy-OR dependency graph. Notice how the initial river overflow propagates directly into the Drainage Network with an 85% failure probability. This in turn triggers failures at the electrical substation and arterial road junctions, threatening emergency power at the regional hospital.

Crucially, our graph engine includes depth-first search cycle detection, guaranteeing that cyclic asset dependencies terminate cleanly without infinite recursion loops."

---

### SCENE 4: INTERVENTION OPTIMIZATION & NUGEN ADVISORY ASSISTANT (2:05 – 2:50)
**Visual**: Navigate to **Interventions Tab**. Highlight the Feasible Interventions table, showing budget allocation and counterfactual impact deltas. Scroll to the **Command Decision Card** and point out the Nugen advisory panel with its non-authoritative simulation badge.

**Spoken Narration (2:05 – 2:50)**:
"In the **Interventions Tab**, emergency logistics become actionable.

Algorithm 8 executes a 0/1 Knapsack optimization against depot inventory and municipal budgets. Algorithm 10 ranks candidate actions, selecting **Intervention I1: Deploy Heavy Mobile Pumping Units** at a cost of $42,000.

Algorithm 11 runs a non-mutating counterfactual simulation: deploying these pumps cuts cascade failure length to zero and delivers a 58.7% reduction in systemic risk.

Algorithm 13 compiles the authoritative **Command Decision Card**. Notice below it: the Nugen Advisory Assistant provides operational rationale and agreement validation, but is prominently marked as non-authoritative with mandatory human sign-off warnings."

---

### SCENE 5: CITIZEN PRE-CALAMITY ALERTS & HAZARD-AVOIDANCE ROUTING (2:50 – 3:45)
**Visual**: Navigate to **Emergency Chatbot Tab**. Show the Pre-Calamity Citizen Alerts grid with severity pills. In the Safe Evacuation Route Planner, select origin `ZONE-001 (Riverside Industrial)` and click **Find Safe Route**. Show route card highlighting avoided flooded roads and turn-by-turn guidance.

**Spoken Narration (2:50 – 3:45)**:
"While incident commanders manage logistics, CLIMAFORGE translates hydrological engineering directly into civilian protection.

Citizens receive automated **Pre-Calamity Alerts**. Riverside residents see an immediate CRITICAL alert explaining the exact physical driver—extreme rainfall runoff—and specific safety recommendations.

When a citizen requests an evacuation route, our engine runs a dynamic Dijkstra pathfinder. It ingests the failing infrastructure nodes identified in our cascade model and dynamically prunes the flooded Arterial Road from traversable corridors.

The system diverts the resident along the elevated Perimeter Ridge bypass to the Northern High School shelter—an 11.7-kilometer journey estimated at 16 minutes.

If floodwaters completely cut off all escape paths, the engine fails closed safely, reporting 'Route Blocked' with explicit shelter-in-place instructions rather than leading citizens into dangerous flood waters.

*Note: In this prototype, road corridors and shelter locations are synthetic simulation fixtures designed to validate algorithm behavior, rather than certified municipal facilities.*"

---

### SCENE 6: OFFLINE PANIC PHASE, SOS QUEUE & AUTOMATIC RECONNECTION SYNC (3:45 – 4:40)
**Visual**: In the Emergency Chatbot Tab, toggle DevTools Network to 'Offline' (or click 'Simulate Offline'). Show the amber `OFFLINE SURVIVAL MODE` banner. Demonstrate cached alerts and routes remain readable. Fill out the Emergency SOS form (Rising water, Critical urgency, trapped persons) and submit. Show the outbox entry in amber `NOT_SENT` status. Reconnect network; show instant transition to emerald `ACKNOWLEDGED`.

**Spoken Narration (3:45 – 4:40)**:
"Now consider the ultimate real-world failure mode: **Total Communications Collapse**.

When severe storms knock out cellular towers and power lines, standard cloud apps crash and leave citizens with blank screens.

CLIMAFORGE is engineered for offline survival.

Watch as I simulate a complete network blackout.

The platform immediately activates **Offline Survival Mode**. Powered by our native client-side **IndexedDB store**—`climaforge_offline_store`—the citizen retains instant access to pre-calamity alerts, shelter locations, and evacuation waypoints directly from local flash storage.

Even more vital is our **Client SOS Outbox**.

Stranded residents can submit emergency distress reports completely offline. They select incident type, urgency priority, and location details. Clicking 'Record Emergency SOS' stores the report locally with status **NOT_SENT** and a client-generated UUID. It persists across reboots and battery saves. Zero access tokens or passwords are ever stored in IndexedDB.

Now, as emergency cellular restore trucks arrive and connectivity returns—watch:
The background synchronization service detects the connection, drains the outbox, and submits the batch to our backend. The server processes the reports within an idempotent transaction, preventing duplicate ticket creation.

The status immediately turns to **ACKNOWLEDGED**. City dispatchers now have exact coordinates for rescue prioritization."

---

### SCENE 7: TECHNICAL VERIFICATION & AUTOMATED TESTING (4:40 – 5:15)
**Visual**: Quick, focused 25-second showcase of verified technical evidence: terminal displaying 302 backend pytest passes, 56 frontend vitest passes, and 8 Playwright Chromium E2E passes. Show multi-tab Web Locks architecture slide.

**Spoken Narration (4:40 – 5:15)**:
"To ensure CLIMAFORGE is bulletproof under operational stress, we subjected the codebase to exhaustive automated testing:

- **302 automated backend pytest tests** passing at 100%, verifying mathematical algorithms, database transactions, and idempotent synchronization.
- **56 frontend unit and integration tests** in Vitest validating offline state transitions and RBAC permissions.
- And **8 real-browser Playwright E2E tests** running in headless Chromium, executing both our full 6-scene operational workflow and verifying Web Locks multi-tab refresh synchronization without token replay.

The entire frontend production build compiles in under one second with zero errors."

---

### SCENE 8: CLIMATE IMPACT, FEASIBILITY, LIMITATIONS & CLOSING (5:15 – 5:45)
**Visual**: Presenter on camera or closing summary card with the CLIMAFORGE emblem, project repository link, and key impact metrics (Decision Speed, Zero Blackout Data Loss, Explainable AI).

**Spoken Narration (5:15 – 5:45)**:
"CLIMAFORGE bridges the critical gap between climate science, urban resilience, and civilian survival:
- It compresses municipal disaster triage from hours to seconds.
- It uncovers hidden lifeline infrastructure cascades before they fail.
- And through offline PWA architecture, it guarantees that even in total blackout, citizens have a clear path to safety and a voice that reaches help.

While real-world deployment will require certified municipal LiDAR DEMs and Computer-Aided Dispatch links, our deterministic core and offline architecture are pilot-ready.

CLIMAFORGE: *Deterministic Climate Intelligence. Resilient Human Safety.*

Thank you."
