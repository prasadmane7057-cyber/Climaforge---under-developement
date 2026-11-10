/**
 * Cross-Tab Authentication Coordination & Session Synchronization (M16A.7).
 *
 * Implements:
 * - Web Locks API coordination via `navigator.locks.request('climaforge_refresh_lock', ...)`
 *   to ensure only one browser tab can initiate refresh-token rotation at a time.
 * - BroadcastChannel API coordination via `new BroadcastChannel('climaforge_auth')`
 *   to synchronize non-sensitive lifecycle events across tabs.
 * - Safe fallback for browsers/environments lacking Web Locks or BroadcastChannel.
 * - Strict security: NEVER broadcasts access tokens, refresh tokens, cookies, passwords, or secrets.
 *   Access tokens remain strictly isolated in JavaScript heap memory of each tab.
 */

export type AuthSyncMessage =
  | {
      type: 'REFRESH_COMPLETED';
      timestamp: number;
    }
  | {
      type: 'AUTH_LOGOUT';
      timestamp: number;
    }
  | {
      type: 'SESSION_EXPIRED';
      timestamp: number;
    }
  | {
      type: 'AUTH_LOGIN';
      timestamp: number;
    };

export type AuthSyncListener = (message: AuthSyncMessage) => void;

export const AUTH_CHANNEL_NAME = 'climaforge_auth';
export const REFRESH_LOCK_NAME = 'climaforge_refresh_lock';

/**
 * Window within which a cross-tab event is considered recent.
 */
export const REFRESH_GRACE_WINDOW_MS = 5000;

// ============================================================================
// Feature Detection
// ============================================================================

export function isWebLocksSupported(): boolean {
  return (
    typeof navigator !== 'undefined' &&
    'locks' in navigator &&
    typeof navigator.locks?.request === 'function'
  );
}

export function isBroadcastChannelSupported(): boolean {
  return typeof BroadcastChannel !== 'undefined';
}

// ============================================================================
// Cross-Tab State Tracking (Zero Sensitive Data)
// ============================================================================

let recentRefreshCompletedTimestamp = 0;
let recentSessionExpiredTimestamp = 0;

export function isRecentRefreshCompleted(withinMs = REFRESH_GRACE_WINDOW_MS): boolean {
  return (
    recentRefreshCompletedTimestamp > 0 &&
    Date.now() - recentRefreshCompletedTimestamp < withinMs
  );
}

export function isRecentCrossTabSessionExpired(withinMs = REFRESH_GRACE_WINDOW_MS): boolean {
  return (
    recentSessionExpiredTimestamp > 0 &&
    Date.now() - recentSessionExpiredTimestamp < withinMs
  );
}

export function clearCrossTabState(): void {
  recentRefreshCompletedTimestamp = 0;
  recentSessionExpiredTimestamp = 0;
}

// ============================================================================
// BroadcastChannel Singleton & Listener Registry
// ============================================================================

let broadcastChannelInstance: BroadcastChannel | null = null;
const syncListeners: Set<AuthSyncListener> = new Set();

export function initBroadcastChannel(): BroadcastChannel | null {
  if (!isBroadcastChannelSupported()) {
    return null;
  }
  if (!broadcastChannelInstance) {
    try {
      broadcastChannelInstance = new BroadcastChannel(AUTH_CHANNEL_NAME);
      broadcastChannelInstance.onmessage = (event: MessageEvent<AuthSyncMessage>) => {
        handleIncomingMessage(event.data);
      };
    } catch {
      broadcastChannelInstance = null;
    }
  }
  return broadcastChannelInstance;
}

if (typeof window !== 'undefined' && isBroadcastChannelSupported()) {
  initBroadcastChannel();
}

function handleIncomingMessage(data: AuthSyncMessage): void {
  if (!data || typeof data !== 'object' || !('type' in data)) {
    return;
  }

  // Update internal tracking based on non-sensitive event type
  if (data.type === 'REFRESH_COMPLETED') {
    recentRefreshCompletedTimestamp = data.timestamp || Date.now();
    recentSessionExpiredTimestamp = 0;
  } else if (data.type === 'AUTH_LOGOUT') {
    clearCrossTabState();
  } else if (data.type === 'SESSION_EXPIRED') {
    recentRefreshCompletedTimestamp = 0;
    recentSessionExpiredTimestamp = data.timestamp || Date.now();
  } else if (data.type === 'AUTH_LOGIN') {
    recentSessionExpiredTimestamp = 0;
  }

  // Notify registered listeners
  syncListeners.forEach((listener) => {
    try {
      listener(data);
    } catch {
      // Isolate listener error
    }
  });
}

export function broadcastAuthEvent(message: AuthSyncMessage): void {
  const channel = initBroadcastChannel();
  if (channel) {
    try {
      channel.postMessage(message);
    } catch {
      // Channel postMessage error handled safely
    }
  }
}

export function onAuthBroadcast(listener: AuthSyncListener): () => void {
  initBroadcastChannel();
  syncListeners.add(listener);
  return () => {
    syncListeners.delete(listener);
  };
}

export function closeAuthBroadcastChannel(): void {
  if (broadcastChannelInstance) {
    try {
      broadcastChannelInstance.close();
    } catch {
      // Ignore close error
    }
    broadcastChannelInstance = null;
  }
  clearCrossTabState();
}

// ============================================================================
// Event Dispatches (Strict Zero-Secret Payloads)
// ============================================================================

export function recordRefreshCompletedCrossTab(): void {
  const timestamp = Date.now();
  recentRefreshCompletedTimestamp = timestamp;
  recentSessionExpiredTimestamp = 0;

  broadcastAuthEvent({
    type: 'REFRESH_COMPLETED',
    timestamp,
  });
}

export function recordLogoutCrossTab(): void {
  clearCrossTabState();
  broadcastAuthEvent({
    type: 'AUTH_LOGOUT',
    timestamp: Date.now(),
  });
}

export function recordSessionExpiredCrossTab(): void {
  recentRefreshCompletedTimestamp = 0;
  recentSessionExpiredTimestamp = Date.now();
  broadcastAuthEvent({
    type: 'SESSION_EXPIRED',
    timestamp: Date.now(),
  });
}

export function recordLoginCrossTab(): void {
  recentSessionExpiredTimestamp = 0;
  broadcastAuthEvent({
    type: 'AUTH_LOGIN',
    timestamp: Date.now(),
  });
}

// ============================================================================
// Web Locks Exclusive Execution Wrapper (with Fail-Closed Fallback)
// ============================================================================

export const FALLBACK_LOCK_KEY = 'climaforge_refresh_lock_fallback';
export const FALLBACK_LOCK_TIMEOUT_MS = 5000;

/**
 * Execute an asynchronous action within the exclusive Web Lock 'climaforge_refresh_lock'.
 * Ensures only one browser tab can execute the refresh operation at any instant.
 *
 * If Web Locks API is unavailable:
 * - Coordinates via localStorage timestamp mutex (storing only numeric epoch, zero secrets).
 * - Where safe cross-tab coordination cannot be guaranteed, fails closed rather than
 *   permitting uncontrolled concurrent refresh requests that would trigger backend replay detection.
 */
export async function executeWithRefreshLock<T>(action: () => Promise<T>): Promise<T> {
  if (isWebLocksSupported()) {
    return navigator.locks.request(REFRESH_LOCK_NAME, async () => {
      return action();
    });
  }

  // Cross-tab fallback lock using localStorage monotonic timestamp (no secrets stored)
  if (typeof localStorage !== 'undefined') {
    const startTime = Date.now();
    let acquired = false;

    while (Date.now() - startTime < FALLBACK_LOCK_TIMEOUT_MS) {
      const existing = localStorage.getItem(FALLBACK_LOCK_KEY);
      const existingTime = existing ? parseInt(existing, 10) : 0;
      const isExpired = !existingTime || Date.now() - existingTime > FALLBACK_LOCK_TIMEOUT_MS;

      if (!existing || isExpired) {
        localStorage.setItem(FALLBACK_LOCK_KEY, String(Date.now()));
        acquired = true;
        break;
      }
      await new Promise((resolve) => setTimeout(resolve, 25));
    }

    if (!acquired) {
      // Fail closed: Refuse to permit uncontrolled concurrent refresh calls
      throw new Error('Cross-tab refresh lock acquisition timed out: failing closed to prevent replay collision');
    }

    try {
      return await action();
    } finally {
      try {
        localStorage.removeItem(FALLBACK_LOCK_KEY);
      } catch {
        // Ignore cleanup failure
      }
    }
  }

  // If running in an environment without Web Locks or localStorage where cross-tab
  // coordination cannot be safely guaranteed:
  // Fail closed if window is defined (multi-tab browser context)
  if (typeof window !== 'undefined') {
    throw new Error('Safe cross-tab refresh coordination unavailable: failing closed to prevent replay collision');
  }

  return action();
}

// Attach dev helpers in development mode for genuine browser E2E inspection
if (typeof window !== 'undefined' && import.meta.env.DEV) {
  (window as unknown as Record<string, unknown>).__CLIMAFORGE_AUTHSYNC__ = {
    isWebLocksSupported,
    isBroadcastChannelSupported,
    executeWithRefreshLock,
    clearCrossTabState,
    broadcastAuthEvent,
    onAuthBroadcast,
    recordRefreshCompletedCrossTab,
    recordLogoutCrossTab,
    recordSessionExpiredCrossTab,
    recordLoginCrossTab,
    isRecentRefreshCompleted,
    isRecentCrossTabSessionExpired,
  };
}
