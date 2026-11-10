# CLIMAFORGE Frontend — React 19 + TypeScript + Vite

Tactical operations center and flood decision-support dashboard for CLIMAFORGE. Built with React 19, TypeScript, and Vite.

---

## M16A.6 Frontend Authentication & RBAC Architecture

The frontend integrates directly with the FastAPI authentication and Role-Based Access Control (RBAC) backend introduced in milestones M16A.1–M16A.5.

### 1. In-Memory Token Security Model
- **Strict Isolation**: Access tokens are kept exclusively in JavaScript memory (`auth.ts`). They are **NEVER** persisted to `localStorage`, `sessionStorage`, or IndexedDB.
- **Refresh Cookies**: Refresh tokens are managed entirely by the browser via secure, environment-aware `HttpOnly`, `SameSite=Lax/Strict` cookies (`climaforge_refresh_token`). JavaScript never has access to raw refresh tokens.
- **CSRF Protection**: State-mutating requests and session operations use the double-submit cookie pattern. The frontend reads the `csrf_token` cookie and injects the `X-CSRF-Token` header.
- **Deduplicated Silent Refresh**: When multiple concurrent API calls encounter HTTP 401, a centralized promise deduplicator coordinates a single refresh call against `POST /api/auth/refresh`. This prevents token replay-protection race conditions that would otherwise revoke the user's active session family.

### 2. Authentication State Machine
Centralized in `AuthProvider` / `useAuth`:
- `loading`: Initial application boot verifying session presence.
- `authenticated`: Valid access token in memory with loaded `UserProfile`.
- `unauthenticated`: Public demonstrator mode or logged-out state.
- `session-expired`: Session timed out or refresh token expired/revoked; surfaces non-blocking re-authentication prompt.

### 3. Canonical Roles & Permissions
Frontend permissions match the backend definitions in `backend/app/security/rbac.py`:

| Role | Default Permissions | Navigation / Action Capabilities |
| :--- | :--- | :--- |
| **VIEWER** | `scenario.read`, `chatbot.ask`, `audit.read` | Public/Observer access: view telemetry, ask citizen chatbot, view audit logs. Analysis execution disabled. |
| **ANALYST** | VIEWER + `scenario.run`, `scenario.run_adhoc`, `ml.predict` | Run deterministic flood simulations (Algorithms 0–13) and ML risk predictions. |
| **OPERATOR** | ANALYST + `intervention.recommend`, `intervention.approve`, `audit.create` | Command station access: evaluate candidate interventions and approve mitigations. |
| **AUDITOR** | `audit.read` | Specialized audit officer: inspect chronological audit trail. Direct scenario runs restricted. |
| **ADMIN** | All system permissions + `admin.users`, `admin.roles`, `admin.scenario_grants` | Full operational and administrative control. |

*Note: `intervention.deploy` is restricted under least-privilege defaults and requires explicit authorization policy.*

### 4. Navigation & Route Guarding
- **Role-Aware Sidebar**: Navigation items indicate required permissions and display lock indicators when restricted.
- **Action Guarding**: "Run Flood Analysis" and mitigation buttons check `hasPermission('scenario.run')`.
- **Unauthorized View**: Unauthorized tab navigation renders `UnauthorizedView` with clear required vs current role details and a quick return button.

---

## M16A.7 Cross-Tab Authentication Coordination & Session Hardening

- **Web Locks Exclusive Refresh Coordination**: Implemented `navigator.locks.request('climaforge_refresh_lock', ...)` to guarantee strict FIFO mutual exclusion for token refresh across all open browser tabs.
- **Shared Cookie Jar Synchronization**: Sequential lock acquisition ensures waiting tabs send the freshly rotated refresh token cookie, completely eliminating concurrent refresh-token replay collisions and accidental token-family revocations.
- **Zero-Secret Cross-Tab Event Bus**: Implemented `new BroadcastChannel('climaforge_auth')` transmitting exclusively non-sensitive lifecycle events (`REFRESH_COMPLETED`, `AUTH_LOGOUT`, `SESSION_EXPIRED`, `AUTH_LOGIN`).
- **Strict Bearer Token Isolation**: Access tokens exist exclusively in the private JavaScript heap memory of each tab. Access tokens, refresh tokens, cookies, passwords, and CSRF secrets are **NEVER** broadcast over BroadcastChannel and **NEVER** persisted to web storage.
- **Multi-Tab Lifecycle Synchronization**: Immediate cross-tab logout and session expiration propagation without redirect loops or stale credential restoration.
- **Safe Browser Compatibility Fallback**: Automatic feature detection and graceful fallback execution for environments lacking Web Locks or BroadcastChannel.

---

## Development & Verification

### Install Dependencies
```bash
npm install
```

### Run Unit & Integration Tests (Vitest)
```bash
npm test
```
Runs 43 comprehensive frontend tests covering:
- In-memory token security and storage isolation
- CSRF token parsing and header injection
- Deduplicated silent refresh on concurrent 401s within a single tab
- Multi-tab Web Locks mutual exclusion and contention
- Multi-tab refresh-token rotation without replay-triggered token-family revocation
- Multi-tab logout, session expiration, and login synchronization
- Strict security audit: zero secret leakage on BroadcastChannel
- Feature detection and graceful fallbacks for missing browser APIs
- Login credential submission and error handling (401, 403, 429)
- Idempotent logout and cookie clearance
- Role and permission evaluation across all canonical roles
- AuthContext state transitions (`loading` -> `authenticated` / `unauthenticated` / `session-expired`)
- Component rendering: `Header`, `Sidebar`, `LoginModal`, `UnauthorizedView`

### Lint
```bash
npm run lint
```

### Production Build
```bash
npm run build
```

### Start Development Server
```bash
npm run dev
```
Runs on `http://localhost:5173`.
