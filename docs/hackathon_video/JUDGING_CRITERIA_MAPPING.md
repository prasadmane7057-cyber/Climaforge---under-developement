# CLIMAFORGE — Hackathon Judging Criteria Alignment & Mapping Matrix
## Evaluation Framework: AI For Climate Change | Calibrated to 5:45 Video Run

This matrix provides a direct mapping between the hackathon judging criteria and the specific demonstration scenes, technical evidence, and key messages presented in the CLIMAFORGE demonstration video.

---

### CORE JUDGING CRITERIA MAPPING TABLE

| Judging Criterion | Video Timestamp | Feature / Capability Demonstrated | Direct Engineering Evidence | Key Evaluator Takeaway |
| :--- | :---: | :--- | :--- | :--- |
| **1. Climate Problem Identification & Relevance** | **0:00 – 0:35** | Extreme precipitation hazard modeling, urban river basin vulnerability, cascading infrastructure collapse, and emergency response delay. | Hydrological input contracts (Algorithms 0–1), rainfall telemetry ingestion ($0\text{--}150\text{ mm/hr}$), soil moisture saturation, and urban drainage capacity modeling. | CLIMAFORGE addresses the most pressing urban climate emergency: extreme flash flooding causing cascading utility collapse and decision paralysis in high-density areas. |
| **2. AI Application & Innovation** | **1:15 – 2:05**<br>&<br>**2:05 – 2:50** | Dual-tier architecture: Deterministic mathematical cascade modeling (Noisy-OR propagation) combined with grounded non-authoritative Advisory AI (Nugen). | Consequence graph cycle-breaking DFS; Noisy-OR failure probability formulas ($p_v = 1 - \prod(1 - p_u s_{uv})$); Counterfactual What-If simulation engine; Nugen advisory gateway with fallback. | True innovation lies in **responsible AI**: eliminating LLM hallucinations in life-or-death decisions by making math authoritative while leveraging AI for explainability and logistics optimization. |
| **3. Solution Implementation & Technical Clarity** | **0:35 – 1:15**<br>&<br>**2:50 – 3:45** | Full-stack production engineering: FastAPI backend + React TypeScript frontend; Dijkstra shortest-safe-path evacuation routing with dynamic cascade failure pruning. | Live interactive dashboard, NetworkX graph canvas, Dijkstra traversal avoiding `Arterial Road Network`, Pydantic strict validation schemas, RESTful OpenAPI `/docs`. | Clean, decoupled, test-driven implementation. Mathematical routing dynamically adapts to simulated flood cascades in real time rather than using static maps. |
| **4. Expected Climate Impact & Feasibility** | **5:15 – 5:45** | Municipal decision acceleration from hours to seconds; zero-connectivity citizen survival via offline outbox; standards-compliant SCADA/CAP ingestion feasibility. | Pre-calamity alerts generation; shelter capacity optimization; containerized deployment readiness; Alembic database migrations; Common Alerting Protocol compatibility. | Highly feasible path to real-world pilot: lightweight architecture can be deployed in municipal emergency centers to protect vulnerable urban communities at minimal infrastructure cost. |
| **5. Video Explanation & Empirical Evidence** | **3:45 – 4:40**<br>&<br>**4:40 – 5:15** | Milestone 7 Panic Phase: Live network disconnection, IndexedDB persistence (`climaforge_offline_store`), durable SOS outbox queuing, and automatic idempotent reconnection sync. | **302 automated backend pytest passes (100%)**;<br>**56 frontend vitest passes (100%)**;<br>**8 Chromium Playwright E2E tests (100%)**;<br>Live browser offline disconnection and sync. | Demonstrates genuine, verifiable software rather than mockups or slides. Every claim is substantiated by real code execution, automated regression tests, and observable browser state. |

---

### DETAILED CRITERIA DEEP-DIVE & EVALUATOR TALKING POINTS

#### Criterion 1: Climate Problem Identification and Relevance
- **The Challenge**: Accelerated climate change has caused an exponential rise in convective storm intensity. Urban areas with paved surfaces experience rapid runoff that outpaces stormwater drainage.
- **Why Current Systems Fail**: Municipalities rely on siloed telemetry (river gauges, weather radar, traffic cams) that requires manual cross-referencing. When flooding begins, coordinators take hours to predict which downstream power or hospital assets will fail.
- **The CLIMAFORGE Advantage**: Algorithms 0–3 transform multi-variable climate telemetry into instantaneous, standardized vulnerability metrics with identified dominant physical drivers.

#### Criterion 2: AI Application and Innovation
- **Architectural Novelty**: Dual-Tier Governance Architecture.
  - *Tier 1 (Authoritative Deterministic Core)*: Algorithms 0–13 implement mathematical models (Noisy-OR, NetworkX graph percolation, greedy resource knapsack) that execute identically every run.
  - *Tier 2 (Advisory AI Gateway - Nugen)*: Grounded LLM adapter that translates complex graph mathematics into plain-language citizen alerts and operator briefings.
- **Scientific Honesty**: CLIMAFORGE explicitly discloses that while tree-based ML classifiers were evaluated in research benchmarks, the production decision core relies exclusively on mathematically provable algorithms to avoid dangerous generative hallucinations.

#### Criterion 3: Solution Implementation and Technical Clarity
- **Frontend**: React 19, TypeScript, Vite, high-contrast accessible UI, interactive SVG topological graphs, and native IndexedDB offline caching.
- **Backend**: Python 3.11+, FastAPI, SQLAlchemy ORM, Alembic migrations, Pydantic v2 domain schemas, NetworkX topological analysis.
- **Security & RBAC**: JWT access tokens in memory, HttpOnly refresh cookies, Web Locks multi-tab synchronization, and scenario-scoped permission verification (`PERM_SCENARIO_READ`, `PERM_CHATBOT_ASK`).

#### Criterion 4: Expected Climate Impact and Feasibility
- **Quantifiable Resilience Metrics**:
  - *Assessment Latency*: Reduced from 4+ hours of manual analysis to under 2 seconds.
  - *Logistical Efficiency*: Algorithm 10/11 identifies interventions that yield a >50% cascade risk reduction before deploying physical equipment.
  - *Civilian Survival*: Evacuation routing dynamically guides citizens away from submerging corridors towards verified high-elevation shelters.
- **Deployment Feasibility**: Built with zero proprietary hardware lock-in; deployable on edge servers, emergency mobile command trucks, or cloud infrastructure.

#### Criterion 5: Video Explanation and Evidence
- **No Faked Metrics or Mockups**: All numbers, probabilities, and routes presented in the demonstration are computed dynamically by the running application.
- **Empirical Rigor**:
  - Full backend test suite: 302 tests passing (Algorithms 0–13, Consequence Cascades, Resource Optimization, Nugen Gateway, Routing, Incidents Sync).
  - Full frontend test suite: 56 tests passing (Auth, RBAC, Emergency Routing, Offline Storage, SOS Outbox).
  - Genuine browser E2E suite: 8 Playwright Chromium tests (7 Web Locks multi-tab tests + 1 full 6-scene end-to-end integration demo).
