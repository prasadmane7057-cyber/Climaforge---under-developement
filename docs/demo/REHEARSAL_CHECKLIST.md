# CLIMAFORGE — Live Rehearsal & Demonstration Checklist
## Pre-Flight, In-Run, and Post-Run Quality Gate

This checklist is designed for live rehearsals, hackathon stage demos, and evaluators running CLIMAFORGE demonstrations.

---

### 1. PRE-FLIGHT SYSTEM VERIFICATION (T-15 MINUTES)
- [ ] **Backend Service Active**:
  - Command: `python -m uvicorn app.main:app --port 8000`
  - Verification: `curl http://127.0.0.1:8000/health` returns `{"status":"ok"}`.
- [ ] **Frontend Dev Server Active**:
  - Command: `npm run dev -- --port 5173`
  - Verification: Open `http://localhost:5173/` in Chrome; dashboard loads without errors.
- [ ] **Database Integrity**:
  - SQLite table `incidents` exists and migrations are current (`0004_incidents_table.py`).
- [ ] **Browser Environment**:
  - Google Chrome / Chromium in normal profile (not guest/incognito so IndexedDB has full persistence).
  - Browser zoom reset to 100% (`Ctrl + 0`).
  - Dark mode activated across application and OS.
  - DevTools docked cleanly to bottom or right (Network tab open).
- [ ] **Audio / Recording (If capturing media)**:
  - Condenser microphone selected, test audio level peaks between -12dB and -6dB.
  - Recording resolution locked to 1920x1080 @ 60fps.

---

### 2. SCENE-BY-SCENE REHEARSAL VERIFICATION

| Scene | Demonstrated Capability | Verification Check |
| :---: | :--- | :--- |
| **Scene 1** | Baseline Monitoring (`scenario-baseline`) | [ ] Scenario loads with 4 zones and 0 hotspots.<br>[ ] "Run Flood Analysis" completes instantly.<br>[ ] Cascade status shows `SKIPPED_MONITORING_ONLY`. |
| **Scene 2** | Flood Risk Escalation (`scenario-flash-flood`) | [ ] Scenario loads with Riverside Industrial District (`ZONE-001`).<br>[ ] "Run Flood Analysis" yields Canonical Score **82.4 / 100 (CRITICAL)**.<br>[ ] Dominant cause displays: **Extreme Precipitation (Rainfall)**. |
| **Scene 3** | Infrastructure Cascade (M3) | [ ] Consequence Graph Tab renders NetworkX dependency graph.<br>[ ] Red failing nodes visible: `Drainage Network` ($p=0.85$) and `Arterial Road Network` ($p=0.72$).<br>[ ] Telemetry drawer confirms #1 Critical Node is `Drainage Network`. |
| **Scene 4** | Intervention Optimization (M4) | [ ] Interventions Tab displays depot inventory ($42,000, 4 pumps).<br>[ ] Candidate `I1: Mobile Pumping` is ranked #1 (Score: 0.862).<br>[ ] Counterfactual table proves **-58.7% risk reduction** and cascade length drops to 0.<br>[ ] Command Decision Card renders with Nugen advisory tag. |
| **Scene 5** | Citizen Emergency Routing (M6) | [ ] Emergency Chatbot Tab displays Pre-Calamity Citizen Alerts.<br>[ ] Route planning from `ZONE-001` to `SP-01` produces 11.7 km safe path.<br>[ ] Hazard tag confirms: **Avoided 1 flooded/failing infrastructure asset: Arterial Road Network (Road)**.<br>[ ] Simulation disclaimer is visible. |
| **Scene 6** | Panic Phase & Offline SOS (M7) | [ ] Click "Enter Panic Phase" -> Amber "OFFLINE SURVIVAL MODE" banner appears.<br>[ ] Submit SOS report -> Queued with amber `NOT_SENT` pill.<br>[ ] Page reload (F5) preserves pending outbox record from IndexedDB.<br>[ ] Click "Exit Panic Phase" -> Automatic sync transitions badge to emerald `ACKNOWLEDGED`. |

---

### 3. DIAGNOSTICS & CONTINGENCY PLAYBOOK

| Symptom | Diagnostic Step | Instant Recovery Action |
| :--- | :--- | :--- |
| **Backend returns 500 on incident sync** | Check database write lock or UUID conflict | Verify Alembic migration is current: `python -m alembic upgrade head`. Test sync router with fresh UUID. |
| **IndexedDB shows "Storage Unavailable"** | Private browsing restrictions blocking IndexedDB | Open in standard Google Chrome profile where IndexedDB is enabled. |
| **Emergency route returns BLOCKED** | Expected behavior if all exit corridors are severed | Confirm origin is `ZONE-001` and destination is `SP-01`. If demonstrating blocked routes intentionally, observe shelter-in-place instructions. |
| **Browser DevTools offline toggle fails** | Browser throttling artifact | Use in-app panic button: click **Enter Panic Phase (Offline SOS)** in the tab header. |

---

### 4. POST-REHEARSAL CLEANUP
- [ ] In Emergency Chatbot Tab, click trash icon **Clear Acknowledged** to reset outbox.
- [ ] Confirm terminal servers can be cleanly halted (`Ctrl + C`) without leaving orphan processes.

