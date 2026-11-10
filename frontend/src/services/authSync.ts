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
// Web Locks Exclusive Execution Wrapper (Fail-Closed Architecture)
// ============================================================================

/**
 * Execute an asynchronous action within the exclusive Web Lock 'climaforge_refresh_lock'.
 * Ensures only one browser tab can execute the refresh operation at any instant.
 *
 * Security Architecture (Fail-Closed):
 * - In modern browsers, `navigator.locks` provides atomic FIFO mutual exclusion across tabs.
 * - Ad-hoc software mutexes over `localStorage` (such as timestamp flags) are fundamentally unsafe:
 *   they suffer from non-atomic read-then-write (TOCTOU) races where competing tabs both
 *   believe they own the lock, leading to concurrent refresh requests that trigger backend
 *   replay detection and revoke the user's session family.
 * - Therefore, when Web Locks API is unavailable in a browser environment, this function
 *   fails closed by rejecting rather than permitting uncoordinated concurrent refresh requests.
 * - Single-tab concurrency within each tab remains protected by `activeRefreshPromise`.
 * - Backend refresh-token replay detection remains 100% authoritative and unweakened.
 */
export async function executeWithRefreshLock<T>(action: () => Promise<T>): Promise<T> {
  if (isWebLocksSupported()) {
    return navigator.locks.request(REFRESH_LOCK_NAME, async () => {
      return action();
    });
  }

  // Fail closed in multi-tab browser environments when Web Locks API is unavailable:
  // Refuse to permit uncoordinated concurrent refresh requests across tabs.
  if (typeof window !== 'undefined') {
    throw new Error('Web Locks API unavailable: safe cross-tab refresh coordination cannot be guaranteed');
  }

  // Non-browser / SSR environment where multi-tab concurrency does not exist
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
