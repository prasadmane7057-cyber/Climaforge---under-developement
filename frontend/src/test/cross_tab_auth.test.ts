import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import {
  refreshAccessToken,
  getAccessToken,
  setAccessToken,
  clearAccessToken,
  logoutUser,
  notifySessionExpired,
} from '../services/auth';
import {
  isWebLocksSupported,
  isBroadcastChannelSupported,
  executeWithRefreshLock,
  broadcastAuthEvent,
  onAuthBroadcast,
  clearCrossTabState,
  initBroadcastChannel,
  closeAuthBroadcastChannel,
  recordRefreshCompletedCrossTab,
  recordLogoutCrossTab,
  recordSessionExpiredCrossTab,
  recordLoginCrossTab,
  isRecentCrossTabSessionExpired,
  AUTH_CHANNEL_NAME,
  type AuthSyncMessage,
} from '../services/authSync';

// ============================================================================
// Multi-Context Browser Tab Simulation Infrastructure
// ============================================================================

/**
 * Represents the shared browser-level cookie storage for the origin.
 * In a real browser, when one tab receives `Set-Cookie`, the updated cookie
 * is automatically stored and shared across all tabs on that origin.
 */
interface SimulatedCookieJar {
  refreshToken: string | null;
}

/**
 * Represents the backend refresh token service and database,
 * implementing exact rotation, replay detection, and family revocation.
 */
class SimulatedBackend {
  private activeFamilyToken: string = 'initial_valid_refresh_token';
  private revokedTokens: Set<string> = new Set();
  public familyRevoked: boolean = false;
  public replayDetected: boolean = false;
  public rotationCount: number = 0;
  private nextId = 1;

  async handleRefresh(
    suppliedToken: string | null,
    tabId: string
  ): Promise<{ ok: boolean; accessToken?: string; newRefreshToken?: string; status: number }> {
    // Artificial small delay to simulate real network request and test lock contention
    await new Promise((resolve) => setTimeout(resolve, 15));

    if (!suppliedToken) {
      return { ok: false, status: 401 };
    }

    if (this.familyRevoked) {
      return { ok: false, status: 401 };
    }

    // 1. Replay Detection: Check if already revoked
    if (this.revokedTokens.has(suppliedToken)) {
      this.replayDetected = true;
      this.familyRevoked = true;
      return { ok: false, status: 401 };
    }

    // 2. Validate against current active token
    if (suppliedToken !== this.activeFamilyToken) {
      return { ok: false, status: 401 };
    }

    // 3. Rotate token
    this.revokedTokens.add(suppliedToken);
    const newRefreshToken = `rotated_rt_${this.nextId++}`;
    this.activeFamilyToken = newRefreshToken;
    this.rotationCount++;

    const accessToken = `isolated_jwt_${tabId}_${this.nextId}`;
    return {
      ok: true,
      accessToken,
      newRefreshToken,
      status: 200,
    };
  }

  reset(initialToken = 'initial_valid_refresh_token') {
    this.activeFamilyToken = initialToken;
    this.revokedTokens.clear();
    this.familyRevoked = false;
    this.replayDetected = false;
    this.rotationCount = 0;
    this.nextId = 1;
  }
}

/**
 * Represents an independent browser tab with:
 * - Its own isolated JS heap memory (inMemoryAccessToken)
 * - Its own activeRefreshPromise
 * - Its own BroadcastChannel instance
 * - Shared cookie jar and shared Web Locks coordinator
 */
class SimulatedBrowserTab {
  readonly tabId: string;
  inMemoryAccessToken: string | null = null;
  activeRefreshPromise: Promise<string | null> | null = null;
  broadcastChannel: BroadcastChannel;
  receivedBroadcasts: AuthSyncMessage[] = [];
  status: 'authenticated' | 'unauthenticated' | 'session-expired' = 'unauthenticated';
  private cookieJar: SimulatedCookieJar;
  private backend: SimulatedBackend;

  constructor(
    tabId: string,
    cookieJar: SimulatedCookieJar,
    backend: SimulatedBackend
  ) {
    this.tabId = tabId;
    this.cookieJar = cookieJar;
    this.backend = backend;
    this.broadcastChannel = new BroadcastChannel(AUTH_CHANNEL_NAME);
    this.broadcastChannel.onmessage = (event: MessageEvent<AuthSyncMessage>) => {
      this.receivedBroadcasts.push(event.data);
      this.handleIncomingBroadcast(event.data);
    };
  }

  private handleIncomingBroadcast(msg: AuthSyncMessage) {
    if (msg.type === 'AUTH_LOGOUT') {
      this.inMemoryAccessToken = null;
      this.status = 'unauthenticated';
    } else if (msg.type === 'SESSION_EXPIRED') {
      this.inMemoryAccessToken = null;
      this.status = 'session-expired';
    } else if (msg.type === 'AUTH_LOGIN') {
      // In a real app, tab can trigger session check
      this.status = 'authenticated';
    }
  }

  async refreshAccessToken(): Promise<string | null> {
    if (this.activeRefreshPromise) {
      return this.activeRefreshPromise;
    }

    this.activeRefreshPromise = (async () => {
      try {
        return await executeWithRefreshLock(async () => {
          // If another tab reported the session expired while we waited for the lock, abort
          if (isRecentCrossTabSessionExpired()) {
            this.inMemoryAccessToken = null;
            this.status = 'session-expired';
            return null;
          }

          // Use the latest cookie from the shared browser cookie jar
          const currentCookie = this.cookieJar.refreshToken;
          const result = await this.backend.handleRefresh(currentCookie, this.tabId);

          if (!result.ok) {
            this.inMemoryAccessToken = null;
            this.status = 'session-expired';
            recordSessionExpiredCrossTab();
            return null;
          }

          // Browser updates shared cookie jar from Set-Cookie header
          this.cookieJar.refreshToken = result.newRefreshToken!;
          // Tab stores access token STRICTLY in its own private memory
          this.inMemoryAccessToken = result.accessToken!;
          this.status = 'authenticated';

          // Broadcast non-sensitive completion signal (timestamp only, NO tokens/secrets)
          recordRefreshCompletedCrossTab();
          return result.accessToken!;
        });
      } finally {
        this.activeRefreshPromise = null;
      }
    })();

    return this.activeRefreshPromise;
  }

  close() {
    this.broadcastChannel.close();
  }
}

// ============================================================================
// Test Suite
// ============================================================================

describe('M16A.7 Cross-Tab Authentication Coordination & Session Hardening', () => {
  beforeEach(() => {
    clearAccessToken();
    clearCrossTabState();
    initBroadcastChannel();
    vi.restoreAllMocks();
  });

  afterEach(() => {
    clearAccessToken();
    clearCrossTabState();
    vi.restoreAllMocks();
  });

  // ==========================================================================
  // 1. Feature Detection & Browser Compatibility Fallbacks
  // ==========================================================================
  describe('Browser Compatibility & Safe Fallbacks', () => {
    it('detects Web Locks and BroadcastChannel availability accurately', () => {
      expect(typeof isWebLocksSupported()).toBe('boolean');
      expect(typeof isBroadcastChannelSupported()).toBe('boolean');
    });

    it('falls back seamlessly when Web Locks API is unsupported', async () => {
      const originalLocks = navigator.locks;
      Object.defineProperty(navigator, 'locks', {
        value: undefined,
        configurable: true,
      });

      try {
        expect(isWebLocksSupported()).toBe(false);

        let actionExecuted = false;
        const result = await executeWithRefreshLock(async () => {
          actionExecuted = true;
          return 'direct-execution-fallback';
        });

        expect(actionExecuted).toBe(true);
        expect(result).toBe('direct-execution-fallback');
      } finally {
        Object.defineProperty(navigator, 'locks', {
          value: originalLocks,
          configurable: true,
        });
      }
    });

    it('falls back seamlessly when BroadcastChannel is unsupported', () => {
      closeAuthBroadcastChannel();
      const originalBC = globalThis.BroadcastChannel;
      // @ts-expect-error simulating legacy browser without BroadcastChannel
      delete globalThis.BroadcastChannel;

      try {
        expect(isBroadcastChannelSupported()).toBe(false);

        // Neither post nor listen should throw
        expect(() => {
          broadcastAuthEvent({
            type: 'REFRESH_COMPLETED',
            timestamp: Date.now(),
          });
        }).not.toThrow();

        const unsubscribe = onAuthBroadcast(() => {});
        expect(typeof unsubscribe).toBe('function');
        expect(() => unsubscribe()).not.toThrow();
      } finally {
        globalThis.BroadcastChannel = originalBC;
        initBroadcastChannel();
      }
    });
  });

  // ==========================================================================
  // 2. Real Multi-Context Independent Tab Coordination
  // ==========================================================================
  describe('Real Multi-Context Tab Coordination (Web Locks & Token Isolation)', () => {
    it('demonstrates that simultaneous refresh WITHOUT locks triggers replay detection and revokes session', async () => {
      const backend = new SimulatedBackend();
      const cookieJar: SimulatedCookieJar = {
        refreshToken: 'initial_valid_refresh_token',
      };

      // Both tabs read the same cookie simultaneously (racing without locks)
      const tokenSentByTab1 = cookieJar.refreshToken;
      const tokenSentByTab2 = cookieJar.refreshToken;

      // Both send to backend concurrently without Web Locks mutual exclusion
      const [res1, res2] = await Promise.all([
        backend.handleRefresh(tokenSentByTab1, 'tab1'),
        backend.handleRefresh(tokenSentByTab2, 'tab2'),
      ]);

      // Exactly one succeeds, the other hits replay detection and revokes the entire family!
      expect(backend.replayDetected).toBe(true);
      expect(backend.familyRevoked).toBe(true);
      expect(res1.ok && res2.ok).toBe(false);
    });

    it('coordinates simultaneous refresh from two independent tabs using Web Locks to prevent replay detection', async () => {
      const backend = new SimulatedBackend();
      const cookieJar: SimulatedCookieJar = {
        refreshToken: 'initial_valid_refresh_token',
      };

      const tab1 = new SimulatedBrowserTab('tab_1', cookieJar, backend);
      const tab2 = new SimulatedBrowserTab('tab_2', cookieJar, backend);

      try {
        // Tab 1 and Tab 2 initiate refresh at the EXACT same millisecond
        const [tokenTab1, tokenTab2] = await Promise.all([
          tab1.refreshAccessToken(),
          tab2.refreshAccessToken(),
        ]);

        // CRITICAL REPLAY PROTECTION VERIFICATION:
        // 1. Replay detection was NOT triggered!
        expect(backend.replayDetected).toBe(false);
        // 2. Token family was NOT revoked!
        expect(backend.familyRevoked).toBe(false);
        // 3. Both tabs successfully received access tokens
        expect(tokenTab1).toBeTruthy();
        expect(tokenTab2).toBeTruthy();
        expect(tokenTab1).not.toBe(tokenTab2); // Distinct access tokens per tab memory
        // 4. Tab 1 holds only Tab 1's token
        expect(tab1.inMemoryAccessToken).toBe(tokenTab1);
        // 5. Tab 2 holds only Tab 2's token
        expect(tab2.inMemoryAccessToken).toBe(tokenTab2);
        // 6. Exactly 2 sequential rotations occurred (no race, no collision)
        expect(backend.rotationCount).toBe(2);
      } finally {
        tab1.close();
        tab2.close();
      }
    });

    it('verifies Web Locks contention: Tab 2 waits until Tab 1 releases the lock', async () => {
      const executionOrder: string[] = [];

      const tab1Action = executeWithRefreshLock(async () => {
        executionOrder.push('tab1_lock_acquired');
        await new Promise((r) => setTimeout(r, 40));
        executionOrder.push('tab1_lock_released');
      });

      const tab2Action = executeWithRefreshLock(async () => {
        executionOrder.push('tab2_lock_acquired');
        await new Promise((r) => setTimeout(r, 10));
        executionOrder.push('tab2_lock_released');
      });

      await Promise.all([tab1Action, tab2Action]);

      // Strict FIFO mutual exclusion guaranteed by Web Locks
      expect(executionOrder).toEqual([
        'tab1_lock_acquired',
        'tab1_lock_released',
        'tab2_lock_acquired',
        'tab2_lock_released',
      ]);
    });
  });

  // ==========================================================================
  // 3. Multi-Tab Lifecycle Synchronization (Logout, Expiry, Login)
  // ==========================================================================
  describe('Cross-Tab State Synchronization', () => {
    it('propagates logout across independent tabs and purges in-memory credentials', async () => {
      const cookieJar: SimulatedCookieJar = { refreshToken: 'valid_cookie' };
      const backend = new SimulatedBackend();

      const tab1 = new SimulatedBrowserTab('tab_1', cookieJar, backend);
      const tab2 = new SimulatedBrowserTab('tab_2', cookieJar, backend);

      try {
        tab1.inMemoryAccessToken = 'active-token-tab-1';
        tab2.inMemoryAccessToken = 'active-token-tab-2';
        tab1.status = 'authenticated';
        tab2.status = 'authenticated';

        // Tab 1 executes logout
        recordLogoutCrossTab();

        // Allow message dispatch
        await new Promise((resolve) => setTimeout(resolve, 30));

        // Tab 2 has purged its in-memory access token and transitioned to unauthenticated
        expect(tab2.inMemoryAccessToken).toBeNull();
        expect(tab2.status).toBe('unauthenticated');
        expect(tab2.receivedBroadcasts.some((m) => m.type === 'AUTH_LOGOUT')).toBe(true);
      } finally {
        tab1.close();
        tab2.close();
      }
    });

    it('propagates session expiration across tabs and prevents redundant refresh calls', async () => {
      const cookieJar: SimulatedCookieJar = { refreshToken: 'expired_cookie' };
      const backend = new SimulatedBackend();
      // Configure backend as already revoked
      backend.familyRevoked = true;

      const tab1 = new SimulatedBrowserTab('tab_1', cookieJar, backend);
      const tab2 = new SimulatedBrowserTab('tab_2', cookieJar, backend);

      try {
        tab1.inMemoryAccessToken = 'stale-token-1';
        tab2.inMemoryAccessToken = 'stale-token-2';

        // Tab 1 attempts refresh and gets 401
        const res1 = await tab1.refreshAccessToken();
        expect(res1).toBeNull();
        expect(tab1.inMemoryAccessToken).toBeNull();
        expect(tab1.status).toBe('session-expired');

        // Allow broadcast delivery
        await new Promise((resolve) => setTimeout(resolve, 30));

        // Tab 2 transitioned to session-expired
        expect(tab2.inMemoryAccessToken).toBeNull();
        expect(tab2.status).toBe('session-expired');

        // When Tab 2 attempts refresh, isRecentCrossTabSessionExpired blocks the network call
        const backendCallsBefore = backend.rotationCount;
        const res2 = await tab2.refreshAccessToken();
        expect(res2).toBeNull();
        expect(backend.rotationCount).toBe(backendCallsBefore); // Zero network calls made by Tab 2
      } finally {
        tab1.close();
        tab2.close();
      }
    });

    it('propagates login across tabs to trigger session restoration', async () => {
      const cookieJar: SimulatedCookieJar = { refreshToken: 'newly_logged_in_cookie' };
      const backend = new SimulatedBackend();

      const tab1 = new SimulatedBrowserTab('tab_1', cookieJar, backend);
      const tab2 = new SimulatedBrowserTab('tab_2', cookieJar, backend);

      try {
        tab2.status = 'unauthenticated';

        // Tab 1 logs in
        recordLoginCrossTab();

        await new Promise((resolve) => setTimeout(resolve, 30));

        expect(tab2.receivedBroadcasts.some((m) => m.type === 'AUTH_LOGIN')).toBe(true);
        expect(tab2.status).toBe('authenticated');
      } finally {
        tab1.close();
        tab2.close();
      }
    });
  });

  // ==========================================================================
  // 4. Critical Security Audit: Strict Zero-Secret BroadcastChannel Policy
  // ==========================================================================
  describe('Security Audit — Strict Zero-Secret BroadcastChannel Policy', () => {
    it('verifies that BroadcastChannel payloads NEVER contain access tokens, refresh tokens, cookies, or secrets', () => {
      const capturedPayloads: unknown[] = [];

      const originalPostMessage = BroadcastChannel.prototype.postMessage;
      vi.spyOn(BroadcastChannel.prototype, 'postMessage').mockImplementation(function (
        this: BroadcastChannel,
        message: unknown
      ) {
        capturedPayloads.push(message);
        return originalPostMessage.call(this, message);
      });

      // 1. Trigger token refresh completion broadcast
      recordRefreshCompletedCrossTab();

      // 2. Trigger logout broadcast
      recordLogoutCrossTab();

      // 3. Trigger session expired broadcast
      recordSessionExpiredCrossTab();

      // 4. Trigger login broadcast
      recordLoginCrossTab();

      expect(capturedPayloads.length).toBeGreaterThanOrEqual(4);

      for (const payload of capturedPayloads) {
        const jsonStr = JSON.stringify(payload).toLowerCase();

        // MUST NEVER leak access tokens or bearer credentials
        expect(jsonStr).not.toContain('access_token');
        expect(jsonStr).not.toContain('bearer');
        expect(jsonStr).not.toContain('jwt');

        // MUST NEVER leak refresh tokens
        expect(jsonStr).not.toContain('refresh_token');
        expect(jsonStr).not.toContain('climaforge_refresh_token');

        // MUST NEVER leak cookies or CSRF tokens
        expect(jsonStr).not.toContain('cookie');
        expect(jsonStr).not.toContain('csrf');

        // MUST NEVER leak passwords or credentials
        expect(jsonStr).not.toContain('password');
        expect(jsonStr).not.toContain('secret');
      }
    });
  });

  // ==========================================================================
  // 5. Integration with auth.ts Module Services
  // ==========================================================================
  describe('auth.ts Module Integration with Web Locks and Zero-Secret Events', () => {
    it('refreshAccessToken uses Web Locks and broadcasts non-sensitive completion signal', async () => {
      const fetchMock = vi.fn().mockResolvedValue({
        ok: true,
        status: 200,
        json: async () => ({
          access_token: 'auth-ts-private-access-token',
          token_type: 'bearer',
          expires_in: 900,
        }),
      });
      globalThis.fetch = fetchMock;

      const receivedMessages: AuthSyncMessage[] = [];
      const testChannel = new BroadcastChannel(AUTH_CHANNEL_NAME);
      testChannel.onmessage = (e) => {
        receivedMessages.push(e.data);
      };

      try {
        const token = await refreshAccessToken();

        expect(token).toBe('auth-ts-private-access-token');
        expect(getAccessToken()).toBe('auth-ts-private-access-token');

        await new Promise((r) => setTimeout(r, 30));

        // Event was broadcast, but ONLY with non-sensitive type REFRESH_COMPLETED
        const refreshMsg = receivedMessages.find((m) => m.type === 'REFRESH_COMPLETED');
        expect(refreshMsg).toBeDefined();
        // @ts-expect-error verifying property does not exist
        expect(refreshMsg?.access_token).toBeUndefined();
      } finally {
        testChannel.close();
      }
    });

    it('logoutUser clears in-memory state and broadcasts AUTH_LOGOUT', async () => {
      globalThis.fetch = vi.fn().mockResolvedValue({
        ok: true,
        status: 200,
        json: async () => ({ message: 'Logged out successfully' }),
      });

      const receivedMessages: AuthSyncMessage[] = [];
      const testChannel = new BroadcastChannel(AUTH_CHANNEL_NAME);
      testChannel.onmessage = (e) => {
        receivedMessages.push(e.data);
      };

      try {
        setAccessToken('token-before-logout');
        expect(getAccessToken()).toBe('token-before-logout');

        await logoutUser();

        expect(getAccessToken()).toBeNull();

        await new Promise((r) => setTimeout(r, 30));
        expect(receivedMessages.some((m) => m.type === 'AUTH_LOGOUT')).toBe(true);
      } finally {
        testChannel.close();
      }
    });

    it('notifySessionExpired clears in-memory state and broadcasts SESSION_EXPIRED', async () => {
      const receivedMessages: AuthSyncMessage[] = [];
      const testChannel = new BroadcastChannel(AUTH_CHANNEL_NAME);
      testChannel.onmessage = (e) => {
        receivedMessages.push(e.data);
      };

      try {
        setAccessToken('token-before-expiry');
        notifySessionExpired(true);

        expect(getAccessToken()).toBeNull();

        await new Promise((r) => setTimeout(r, 30));
        expect(receivedMessages.some((m) => m.type === 'SESSION_EXPIRED')).toBe(true);
      } finally {
        testChannel.close();
      }
    });
  });
});
