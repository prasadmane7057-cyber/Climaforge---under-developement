# CLIMAFORGE — Screen Recording & Media Production Checklist
## Pre-Recording, In-Take, and Post-Production Verification (5:45 Target)

This checklist ensures that screen captures, camera feeds, audio recordings, and demonstrations comply with high-standard hackathon submission criteria.

---

### 1. VIDEO HARDWARE & ENVIRONMENT SETUP
- [ ] **Display Resolution**: Primary display set to exactly `1920x1080` (1080p).
  - *Note*: If using a high-DPI (4K or Retina) display, set OS display scaling to 100% or capture at 1080p to avoid fuzzy text.
- [ ] **Frame Rate**: Screen capture software set to a constant `60 FPS` (or `30 FPS`).
- [ ] **Audio Hardware**: External USB or XLR microphone configured as the primary audio input.
  - Test recording for 15 seconds to verify no echo, clipping, or HVAC fan hum.
- [ ] **Lighting & Camera**:
  - Presenter front-lit with soft natural or ring lighting.
  - Camera positioned at eye level.
  - Background tidy and non-distracting.
- [ ] **Clean Desktop**:
  - Hide desktop icons (Right-click desktop -> View -> Uncheck "Show desktop icons").
  - Auto-hide or minimize operating system taskbar if desired.
  - Close all unrelated apps (Slack, Discord, WhatsApp, Spotify, Email).

---

### 2. BROWSER & APPLICATION PREPARATION
- [ ] **Browser**: Clean Google Chrome or Chromium profile.
- [ ] **Address Bar & Bookmarks**:
  - Press `Ctrl + Shift + B` to hide the bookmarks bar.
  - Ensure zero personal bookmarks, extensions, or avatars are visible.
- [ ] **Browser Zoom**: Set exactly to `100%` (`Ctrl + 0`).
- [ ] **Theme**: Dark Mode enabled across browser and OS for high contrast and visual cohesion.
- [ ] **DevTools Position**:
  - Dock DevTools to the right or bottom of the screen (or keep in a separate monitor if doing window capture).
  - Pre-configure Network tab with **Offline** toggle readily accessible (or use UI "Simulate Offline" button).
- [ ] **Terminal Setup**:
  - Font: JetBrains Mono, Cascadia Code, or Fira Code, sized at `14pt` or `16pt` for crisp legibility.
  - Pre-clear terminal buffers (`Clear-Host` or `cls`).

---

### 3. PRIVACY & SECURITY GATE (ZERO-CREDENTIAL VERIFICATION)
- [ ] **No Secrets on Screen**:
  - Verify `.env` files are NOT open in any visible editor tab.
  - Verify terminal history does not print `JWT_SECRET_KEY`, `NUGEN_API_KEY`, or Bearer tokens.
  - Check that browser URL bar shows only `http://localhost:5173/` or `http://127.0.0.1:8000/`.
- [ ] **No Personal Identifiers**:
  - User profile in demo shows role `OPERATOR` or `MUNICIPAL_DISPATCHER`.
  - No personal email addresses shown (use `operator@climaforge.test` or demo accounts).

---

### 4. LIVE DEMONSTRATION STEP CHECKLIST (CALIBRATED TO 5:45)
Follow this sequence during the active recording:

| Check | Timestamp | Milestone / Feature | Action Required |
| :---: | :---: | :--- | :--- |
| [ ] | 0:00–0:35 | **Scene 1: Hook** | Clear statement of climate crisis, urban flooding, and infrastructure collapse. |
| [ ] | 0:35–1:15 | **Scene 2: Architecture** | Emphasize strict separation: Deterministic math (Alg 0–13) vs Non-authoritative AI (Nugen). |
| [ ] | 1:15–2:05 | **Scene 3: Risk & Cascades** | Overview: Run Flood Analysis -> Score 82.4 (CRITICAL). Cascade: Drainage failure (p=0.85), DFS cycle safe. |
| [ ] | 2:05–2:50 | **Scene 4: Interventions** | Interventions Tab -> Alg 8 Knapsack, Action I1 (-58.7% risk), Command Decision Card, Nugen advisory badge. |
| [ ] | 2:50–3:45 | **Scene 5: Citizen Safety** | Emergency Assistant -> Pre-Calamity Alerts -> Evacuation Route (11.7km, avoids flooded road). State simulation disclaimer! |
| [ ] | 3:45–4:40 | **Scene 6: Offline Resilience**| Toggle Offline -> Amber "OFFLINE SURVIVAL MODE". Submit SOS (Critical) -> `NOT_SENT`. Reconnect -> `ACKNOWLEDGED`. |
| [ ] | 4:40–5:15 | **Scene 7: Verification** | Show test suites: 302 backend pytest passes, 56 frontend vitest passes, 8 Playwright passes, Web Locks safety. |
| [ ] | 5:15–5:45 | **Scene 8: Impact & Closing**| Summarize climate impact pillars: Speed, Clarity, Resilience. Conclude on time at 5:45! |

---

### 5. POST-RECORDING QUALITY AUDIT
- [ ] **Total Run Time**: Exactly between `5:15` and `6:15` minutes (comfortably inside 3–8 minute hackathon regulation limit).
- [ ] **Audio Quality**:
  - Voice clearly audible over any background audio.
  - No clipping or popping (peak levels between -12dB and -6dB).
- [ ] **Visual Clarity**:
  - Text on dashboard tables and graphs is crisp and readable at 1080p.
  - Cursor movements are smooth and deliberate (no frantic mouse shaking).
- [ ] **Factual Accuracy**:
  - Algorithms 0–13 accurately described as authoritative.
  - Nugen described as advisory.
  - Road topology and shelters identified as illustrative simulation datasets.
  - No claims of live real-world civil defense certification.
- [ ] **Export Specifications**:
  - Format: MP4 (`H.264` video codec, `AAC` audio codec).
  - Bitrate: 8,000 – 12,000 kbps (1080p).
  - File Naming: `CLIMAFORGE_Hackathon_Round2_Demonstration_1080p.mp4`.
