# CLIMAFORGE — Demonstration Scenario Matrix
## Milestone 8: Complete System Integration & Scenario Catalog

This document details the scenarios, hydrological parameters, expected deterministic algorithm outputs, cascade characteristics, and citizen emergency responses used throughout CLIMAFORGE demonstrations and automated tests.

---

### SCENARIO CATALOG & OPERATIONAL MATRIX

| Scenario Attribute | Scenario 1: Baseline Nominal | Scenario 2: Flash Flood Emergency | Scenario 3: Monsoon Pre-Calamity |
| :--- | :--- | :--- | :--- |
| **Identifier** | `scenario-baseline` | `scenario-flash-flood` | `scenario-monsoon-alert` |
| **Display Name** | Dry Season Baseline (Nominal Flow) | Extreme Monsoonal Inundation & River Surge | Catchment Monsoon Alert & Soil Saturation |
| **Operational Purpose** | Baseline monitoring & zero-hotspot verification | Full cascade, intervention, evacuation & offline SOS demo | Early-warning pre-calamity alerts and watch thresholds |
| **Zone Count** | 4 zones | 4 zones | 4 zones |
| **Critical Infrastructure Assets** | 16 monitored facilities | 16 monitored facilities | 16 monitored facilities |
| **Peak Rainfall (mm/hr)** | 18.0 mm/hr (Harbor) | 112.5 mm/hr (Riverside) | 68.0 mm/hr (Riverside) |
| **Max River Inflow (cms)** | 30.0 cms | 185.0 cms | 110.0 cms |
| **Algorithm 1 Canonical Risk** | Max: 0.18 / 100 (`LOW`) | **82.4 / 100 (`CRITICAL`)** | 56.2 / 100 (`HIGH`) |
| **Dominant Hazard Cause** | Nominal river flow | **Extreme Precipitation (Rainfall)** | Soil Saturation & Runoff |
| **Algorithm 2 Hotspots** | **0 Hotspots Qualified** | **1 Hotspot Qualified (ZONE-001)** | 1 Hotspot Qualified (ZONE-001) |
| **Pipeline Cascade Status** | `SKIPPED_MONITORING_ONLY` | **EXECUTED (7 Nodes, 9 Edges)** | EXECUTED (7 Nodes, 9 Edges) |
| **Algorithm 4/5 Failing Nodes** | None (All nodes `SAFE`) | `Drainage Network` ($p=0.85$), `Road` ($p=0.72$) | `Drainage Network` ($p=0.48$) |
| **Algorithm 6 #1 Critical Node** | Not evaluated | `Drainage Network` (Criticality 0.88) | `Drainage Network` (Criticality 0.74) |
| **Algorithm 7/10 Best Action** | No action required | `I1: Deploy High-Capacity Mobile Pumps` | `I2: Deploy Rapid Sandbag Barrier` |
| **Expected Risk Reduction** | N/A | **-58.7% Relative Risk Reduction** | -32.4% Relative Risk Reduction |
| **Cascade Length Delta** | N/A | $3 \rightarrow 0$ (Complete cascade severance) | $2 \rightarrow 1$ (Partial cascade dampening) |
| **Citizen Pre-Calamity Alert** | `LOW / MONITORING` across all zones | `CRITICAL` in Riverside, `WATCH` in Valley | `HIGH` in Riverside, `LOW` in Valley |
| **Evacuation Route Status** | `SAFE` (Direct transit available) | `SAFE (SIMULATED)` via `ROAD-PERIM-01` | `SAFE (SIMULATED)` via `ROAD-PERIM-01` |
| **Hazard Corridor Avoided** | None | **Avoided flooded Arterial Road Network** | None |
| **Offline Cache Availability** | Cached on first scenario fetch | Fully persistent in IndexedDB | Fully persistent in IndexedDB |
| **Offline SOS Outbox Support** | Available | Evaluated (Rising Water / Medical Emergency) | Available |

---

### DETAILED SCENARIO PROFILES

#### 1. Scenario 1: `scenario-baseline` (Dry Season Baseline)
- **Hydrological Profile**: Low seasonal rainfall ($4.0\text{--}18.0\text{ mm}$), dry soil saturation ($0.10\text{--}0.30$), river flow at $15\%\text{ capacity}$.
- **Engine Behavior**:
  - Algorithm 0 validates all ranges as nominal.
  - Algorithm 1 assigns risk scores $<20$ to all 4 zones.
  - Algorithm 2 evaluates threshold $\tau_{\text{hotspot}} = 50.0$. Because $\max(\text{score}) = 18.0 < 50.0$, 0 hotspots qualify.
  - **Deterministic Safety Halt**: The pipeline halts downstream cascade analysis, setting `cascade_status = "SKIPPED_MONITORING_ONLY"`.
  - Proves that the platform does not waste computational resources or issue false emergency alarms during safe weather.

#### 2. Scenario 2: `scenario-flash-flood` (Extreme Monsoonal Inundation)
- **Hydrological Profile**: Severe convective storm event delivering $112.5\text{ mm/hr}$ over Riverside Industrial District (`ZONE-001`), soil saturation at $0.92$, drainage canal capacity exceeded by $180\%$.
- **Engine Behavior**:
  - Algorithm 1 computes Canonical Score **82.4 / 100** (`CRITICAL`). Dominant cause: `Extreme Precipitation`.
  - Algorithm 2 qualifies `ZONE-001` as Hotspot #1.
  - Algorithm 3 calculates multi-factor vulnerability: normalized population exposure index $0.84$, infrastructure index $0.91$.
  - Algorithm 4 builds directed multigraph connecting `Flood` seed to infrastructure systems.
  - Algorithm 5 executes DFS cycle breaking and Noisy-OR propagation:
    - `Flood` $\rightarrow$ `Drainage Network` ($p=0.85$, state: `FAILING`).
    - `Drainage Network` $\rightarrow$ `Arterial Road Network` ($p=0.72$, state: `FAILING`).
    - `Arterial Road Network` $\rightarrow$ `Emergency Access Route` ($p=0.55$, state: `FAILING`).
    - `Hospital Emergency Hub` ($p=0.38$, state: `WATCH`).
  - Algorithm 6 scores `Drainage Network` as #1 Critical Node.
  - Algorithm 8 allocates $\$42,000$ depot budget and 4 mobile pump units to `ZONE-001`.
  - Algorithm 10 ranks candidate interventions: `I1` (Mobile Pumping) scores $0.862$ (Rank 1).
  - Algorithm 11 counterfactual simulation confirms: Absolute risk drops from $0.628$ to $0.259$ (-58.7% relative reduction), surviving nodes increase from 3 to 7.
  - Algorithm 13 generates authoritative Command Decision Card with advisory Nugen tag.
  - Evacuation routing calculates safe path to `SP-01` (Northern High School, elevation 42m), avoiding flooded `Arterial Road Network` via `ROAD-PERIM-01`.

#### 3. Scenario 3: `scenario-monsoon-alert` (Catchment Monsoon Alert)
- **Hydrological Profile**: Sustained moderate precipitation ($68.0\text{ mm/hr}$), soil moisture saturation rising to $0.78$, drainage operating at $90\%\text{ capacity}$.
- **Engine Behavior**:
  - Algorithm 1 assigns risk score $56.2$ (`HIGH`).
  - Algorithm 5 cascade reaches `Drainage Network` ($p=0.48$, state: `WATCH`), but arterial roads remain navigable.
  - Algorithm 10 ranks `I2: Deploy Rapid Sandbag Barrier` as optimal preventive intervention.
  - Generates citizen `HIGH` warning advising residents to review evacuation kits and monitor water levels.

