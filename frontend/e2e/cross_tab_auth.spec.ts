import { test, expect, type BrowserContext, type Page } from '@playwright/test';

/**
 * Genuine Real-Browser Multi-Tab E2E Verification Suite for M16A.7.
 *
 * Runs in genuine headless Chromium with two independent browser tabs
 * sharing the same browser context, origin, and cookie jar.
 */

interface MockBackendState {
  activeRefreshToken: string;
  revokedTokens: Set<string>;
  familyRevoked: boolean;
  replayDetected: boolean;
  rotationCount: number;
  tokenCounter: number;
}

function createBackendState(): MockBackendState {
  return {
    activeRefreshToken: 'rt_seed_valid_token_100',
    revokedTokens: new Set(),
    familyRevoked: false,
    replayDetected: false,
    rotationCount: 0,
    tokenCounter: 1,
  };
}

const CORS_HEADERS = {
  'Access-Control-Allow-Origin': 'http://localhost:5173',
  'Access-Control-Allow-Credentials': 'true',
  'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
  'Access-Control-Allow-Headers': 'Content-Type, Authorization, X-CSRF-Token, Accept',
};

/**
 * Configure Playwright context-level network routing to simulate the backend
 * with exact refresh-token rotation, replay detection, and family revocation.
 */
async function setupContextAuthRouting(context: BrowserContext, state: MockBackendState) {
  await context.route('**/api/auth/**', async (route) => {
    const request = route.request();
    const url = request.url();
    const method = request.method();

    // Handle CORS preflight
    if (method === 'OPTIONS') {
      return route.fulfill({
        status: 204,
        headers: CORS_HEADERS,
      });
    }

    // 1. Refresh endpoint: POST /api/auth/refresh
    if (url.includes('/api/auth/refresh') && method === 'POST') {
      // Small delay (30ms) to test Web Locks mutual exclusion under real concurrent contention
      await new Promise((resolve) => setTimeout(resolve, 30));

      const cookieHeader = request.headers()['cookie'] || '';
      const match = cookieHeader.match(/climaforge_refresh_token=([^;]+)/);
      const suppliedToken = match ? decodeURIComponent(match[1]) : null;

      if (!suppliedToken) {
        return route.fulfill({
          status: 401,
          contentType: 'application/json',
          headers: CORS_HEADERS,
          body: JSON.stringify({ detail: 'Missing refresh token cookie' }),
        });
      }

      if (state.familyRevoked) {
        return route.fulfill({
          status: 401,
          contentType: 'application/json',
          headers: CORS_HEADERS,
          body: JSON.stringify({ detail: 'Token family revoked' }),
        });
      }

      // Replay Detection
      if (state.revokedTokens.has(suppliedToken)) {
        state.replayDetected = true;
        state.familyRevoked = true;
        return route.fulfill({
          status: 401,
          contentType: 'application/json',
          headers: CORS_HEADERS,
          body: JSON.stringify({ detail: 'Replay detected: token already consumed' }),
        });
      }

      if (suppliedToken !== state.activeRefreshToken) {
        return route.fulfill({
          status: 401,
          contentType: 'application/json',
          headers: CORS_HEADERS,
          body: JSON.stringify({ detail: 'Invalid refresh token' }),
        });
      }

      // Rotate token atomically
      state.revokedTokens.add(suppliedToken);
      const newRefreshToken = `rt_rotated_${state.tokenCounter++}`;
      state.activeRefreshToken = newRefreshToken;
      state.rotationCount++;

      const newAccessToken = `jwt_access_token_${state.tokenCounter}`;

      return route.fulfill({
        status: 200,
        contentType: 'application/json',
        headers: {
          ...CORS_HEADERS,
          'Set-Cookie': `climaforge_refresh_token=${newRefreshToken}; Path=/; HttpOnly; SameSite=Lax`,
        },
        body: JSON.stringify({
          access_token: newAccessToken,
          token_type: 'bearer',
          expires_in: 900,
        }),
      });
    }

    // 2. Login endpoint: POST /api/auth/login
    if (url.includes('/api/auth/login') && method === 'POST') {
      const newRefreshToken = `rt_login_${state.tokenCounter++}`;
      state.activeRefreshToken = newRefreshToken;
      const newAccessToken = `jwt_login_${state.tokenCounter}`;

      return route.fulfill({
        status: 200,
        contentType: 'application/json',
        headers: {
          ...CORS_HEADERS,
          'Set-Cookie': `climaforge_refresh_token=${newRefreshToken}; Path=/; HttpOnly; SameSite=Lax`,
        },
        body: JSON.stringify({
          access_token: newAccessToken,
          token_type: 'bearer',
          expires_in: 900,
        }),
      });
    }

    // 3. User profile endpoint: GET /api/auth/me
    if (url.includes('/api/auth/me') && method === 'GET') {
      const authHeader = request.headers()['authorization'] || '';
      if (!authHeader.startsWith('Bearer ')) {
        return route.fulfill({
          status: 401,
          contentType: 'application/json',
          headers: CORS_HEADERS,
          body: JSON.stringify({ detail: 'Missing or invalid token' }),
        });
      }
      return route.fulfill({
        status: 200,
        contentType: 'application/json',
        headers: CORS_HEADERS,
        body: JSON.stringify({
          id: 'usr_test_123',
          email: 'operator@climaforge.org',
          role: 'OPERATOR',
          is_active: true,
          created_at: new Date().toISOString(),
          last_login_at: new Date().toISOString(),
        }),
      });
    }

    // 4. Logout endpoint: POST /api/auth/logout
    if (url.includes('/api/auth/logout') && method === 'POST') {
      state.familyRevoked = true;
      return route.fulfill({
        status: 200,
        contentType: 'application/json',
        headers: {
          ...CORS_HEADERS,
          'Set-Cookie': 'climaforge_refresh_token=; Path=/; Expires=Thu, 01 Jan 1970 00:00:00 GMT',
        },
        body: JSON.stringify({ message: 'Logged out successfully' }),
      });
    }

    return route.continue();
  });
}

test.describe('M16A.7 Real-Browser Multi-Tab E2E Verification (Playwright + Chromium)', () => {
  let context: BrowserContext;
  let page1: Page;
  let page2: Page;
  let backendState: MockBackendState;

  test.beforeEach(async ({ browser }) => {
    backendState = createBackendState();
    context = await browser.newContext();
    await setupContextAuthRouting(context, backendState);

    // Seed the initial refresh token in the shared browser cookie jar
    await context.addCookies([
      {
        name: 'climaforge_refresh_token',
        value: backendState.activeRefreshToken,
        domain: 'localhost',
        path: '/',
        httpOnly: true,
        sameSite: 'Lax',
      },
      {
        name: 'csrf_token',
        value: 'csrf_valid_secret_xyz',
        domain: 'localhost',
        path: '/',
        httpOnly: false,
        sameSite: 'Lax',
      },
    ]);

    // Open two genuine independent tabs in the same Chromium browser context
    page1 = await context.newPage();
    page2 = await context.newPage();

    await page1.goto('/');
    await page2.goto('/');

    // Wait for any initial restoreSession calls to settle
    await page1.waitForTimeout(100);
    await page2.waitForTimeout(100);
  });

  test.afterEach(async () => {
    await context.close();
  });

  // --------------------------------------------------------------------------
  // Scenario 1, 2, 3, 4: Simultaneous Refresh, Web Locks & Token Isolation
  // --------------------------------------------------------------------------
  test('1-4. Coordinates simultaneous refresh across two tabs using Web Locks without replay detection', async () => {
    // Clear tokens in both tabs so they start in a clean state
    await page1.evaluate(() => window.__CLIMAFORGE_AUTH__.clearAccessToken());
    await page2.evaluate(() => window.__CLIMAFORGE_AUTH__.clearAccessToken());

    expect(await page1.evaluate(() => window.__CLIMAFORGE_AUTH__.getAccessToken())).toBeNull();
    expect(await page2.evaluate(() => window.__CLIMAFORGE_AUTH__.getAccessToken())).toBeNull();

    // Trigger simultaneous refresh in both Chromium tabs concurrently
    const [token1, token2] = await Promise.all([
      page1.evaluate(() => window.__CLIMAFORGE_AUTH__.refreshAccessToken()),
      page2.evaluate(() => window.__CLIMAFORGE_AUTH__.refreshAccessToken()),
    ]);

    // 1. Both tabs successfully received access tokens
    expect(token1).toBeTruthy();
    expect(token2).toBeTruthy();

    // 2. Web Locks ensured exclusive serial execution:
    // Tab 1 rotated token 1 -> token 2.
    // Tab 2 sequentially executed with the updated cookie, rotating token 2 -> token 3.
    expect(backendState.replayDetected).toBe(false);
    expect(backendState.familyRevoked).toBe(false);
    expect(backendState.rotationCount).toBeGreaterThanOrEqual(2);

    // 3. Independent JavaScript heap memory verification:
    // Each page holds its own token in private memory
    const memoryToken1 = await page1.evaluate(() => window.__CLIMAFORGE_AUTH__.getAccessToken());
    const memoryToken2 = await page2.evaluate(() => window.__CLIMAFORGE_AUTH__.getAccessToken());
    expect(memoryToken1).toBe(token1);
    expect(memoryToken2).toBe(token2);
    expect(memoryToken1).not.toBe(memoryToken2);
  });

  // --------------------------------------------------------------------------
  // Scenario 5 & 9: Zero Secret Leakage on BroadcastChannel
  // --------------------------------------------------------------------------
  test('5 & 9. Verifies REFRESH_COMPLETED never transfers credentials and BroadcastChannel payloads contain zero secrets', async () => {
    // Inject listener on page2 to capture all BroadcastChannel messages
    await page2.evaluate(() => {
      (window as unknown as { __capturedMessages__: unknown[] }).__capturedMessages__ = [];
      const bc = new BroadcastChannel('climaforge_auth');
      bc.onmessage = (e) => {
        (window as unknown as { __capturedMessages__: unknown[] }).__capturedMessages__.push(e.data);
      };
    });

    // Execute refresh on page1
    await page1.evaluate(() => window.__CLIMAFORGE_AUTH__.refreshAccessToken());

    // Wait for cross-tab broadcast delivery
    await page2.waitForTimeout(100);

    const capturedMessages = await page2.evaluate(() => {
      return (window as unknown as { __capturedMessages__: Record<string, unknown>[] }).__capturedMessages__;
    });

    expect(capturedMessages.length).toBeGreaterThanOrEqual(1);

    for (const msg of capturedMessages) {
      const serialized = JSON.stringify(msg).toLowerCase();

      // Zero bearer credentials or access tokens
      expect(serialized).not.toContain('access_token');
      expect(serialized).not.toContain('bearer');
      expect(serialized).not.toContain('jwt');

      // Zero refresh tokens or cookies
      expect(serialized).not.toContain('refresh_token');
      expect(serialized).not.toContain('cookie');
      expect(serialized).not.toContain('csrf');

      // Zero passwords or secrets
      expect(serialized).not.toContain('password');
      expect(serialized).not.toContain('secret');
    }
  });

  // --------------------------------------------------------------------------
  // Scenario 6: Cross-Tab Logout Synchronization
  // --------------------------------------------------------------------------
  test('6. Propagates logout across tabs, purging in-memory access tokens in both pages', async () => {
    // Authenticate Tab 1 and Tab 2
    await page1.evaluate(() => window.__CLIMAFORGE_AUTH__.refreshAccessToken());
    await page2.evaluate(() => window.__CLIMAFORGE_AUTH__.refreshAccessToken());

    expect(await page1.evaluate(() => window.__CLIMAFORGE_AUTH__.getAccessToken())).toBeTruthy();
    expect(await page2.evaluate(() => window.__CLIMAFORGE_AUTH__.getAccessToken())).toBeTruthy();

    // Trigger logout in Tab 1
    await page1.evaluate(() => window.__CLIMAFORGE_AUTH__.logoutUser());

    // Allow cross-tab BroadcastChannel dispatch
    await page2.waitForTimeout(150);

    // Both tabs have cleared in-memory tokens
    const p1Token = await page1.evaluate(() => window.__CLIMAFORGE_AUTH__.getAccessToken());
    const p2Token = await page2.evaluate(() => window.__CLIMAFORGE_AUTH__.getAccessToken());
    expect(p1Token).toBeNull();
    expect(p2Token).toBeNull();
  });

  // --------------------------------------------------------------------------
  // Scenario 7 & 12: Session Expiration & Stale Tab Rejection
  // --------------------------------------------------------------------------
  test('7 & 12. Propagates session expiration and prevents stale tabs from restoring revoked sessions', async () => {
    // Revoke the backend session
    backendState.familyRevoked = true;

    // Tab 1 attempts refresh and receives 401
    const res1 = await page1.evaluate(() => window.__CLIMAFORGE_AUTH__.refreshAccessToken());
    expect(res1).toBeNull();

    await page2.waitForTimeout(100);

    // Tab 2 has received SESSION_EXPIRED and its memory token is null
    const p2Token = await page2.evaluate(() => window.__CLIMAFORGE_AUTH__.getAccessToken());
    expect(p2Token).toBeNull();

    // Stale tab (Tab 2) attempts refresh; isRecentCrossTabSessionExpired blocks redundant call
    const res2 = await page2.evaluate(() => window.__CLIMAFORGE_AUTH__.refreshAccessToken());
    expect(res2).toBeNull();
  });

  // --------------------------------------------------------------------------
  // Scenario 8: Cross-Tab Login Synchronization
  // --------------------------------------------------------------------------
  test('8. Synchronizes login state across tabs without transferring credentials', async () => {
    // Start with cleared tokens
    await page1.evaluate(() => window.__CLIMAFORGE_AUTH__.clearAccessToken());
    await page2.evaluate(() => window.__CLIMAFORGE_AUTH__.clearAccessToken());

    // Tab 1 executes login
    const loginResult = await page1.evaluate(() =>
      window.__CLIMAFORGE_AUTH__.loginUser('operator@climaforge.org', 'SecurePassword123!')
    );
    expect(loginResult.token).toBeTruthy();

    const p1Token = await page1.evaluate(() => window.__CLIMAFORGE_AUTH__.getAccessToken());
    expect(p1Token).toBe(loginResult.token);

    await page2.waitForTimeout(150);

    // Tab 2 was notified of AUTH_LOGIN without receiving Tab 1's access token
    const p2Token = await page2.evaluate(() => window.__CLIMAFORGE_AUTH__.getAccessToken());
    expect(p2Token).not.toBe(p1Token);
  });

  // --------------------------------------------------------------------------
  // Scenario 10: Zero Credentials Persisted in Browser Storage
  // --------------------------------------------------------------------------
  test('10. Confirms zero access tokens or refresh tokens are persisted in localStorage or sessionStorage', async () => {
    // Perform refresh to populate tokens in memory
    await page1.evaluate(() => window.__CLIMAFORGE_AUTH__.refreshAccessToken());

    const storageInspection = await page1.evaluate(() => {
      const localKeys = Object.keys(localStorage);
      const sessionKeys = Object.keys(sessionStorage);
      const localValues = localKeys.map((k) => localStorage.getItem(k) || '');
      const sessionValues = sessionKeys.map((k) => sessionStorage.getItem(k) || '');
      return { localKeys, sessionKeys, localValues, sessionValues };
    });

    const allStoredText = JSON.stringify(storageInspection).toLowerCase();
    expect(allStoredText).not.toContain('access_token');
    expect(allStoredText).not.toContain('refresh_token');
    expect(allStoredText).not.toContain('climaforge_refresh_token');
    expect(allStoredText).not.toContain('jwt_');
  });

  // --------------------------------------------------------------------------
  // Scenario 11: Fail-Closed Behavior for Unsupported APIs
  // --------------------------------------------------------------------------
  test('11. Fails closed safely when safe cross-tab coordination cannot be guaranteed', async () => {
    const result = await page1.evaluate(async () => {
      // Temporarily simulate missing navigator.locks
      const originalLocks = navigator.locks;
      Object.defineProperty(navigator, 'locks', {
        value: undefined,
        configurable: true,
      });

      try {
        // If localStorage is also unavailable, fail closed
        const originalLocalStorage = window.localStorage;
        Object.defineProperty(window, 'localStorage', {
          value: undefined,
          configurable: true,
        });

        try {
          await window.__CLIMAFORGE_AUTHSYNC__.executeWithRefreshLock(async () => {
            return 'should-not-run';
          });
          return { failedClosed: false, message: '' };
        } catch (err) {
          return { failedClosed: true, message: (err as Error).message };
        } finally {
          Object.defineProperty(window, 'localStorage', {
            value: originalLocalStorage,
            configurable: true,
          });
        }
      } finally {
        Object.defineProperty(navigator, 'locks', {
          value: originalLocks,
          configurable: true,
        });
      }
    });

    expect(result.failedClosed).toBe(true);
    expect(result.message).toContain('Safe cross-tab refresh coordination unavailable: failing closed');
  });
});
