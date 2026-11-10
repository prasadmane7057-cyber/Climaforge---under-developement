/**
 * Authentication and secure session client for CLIMAFORGE M16A.6 / M16A.7.
 *
 * Security Principles:
 * - Access tokens are stored exclusively in-memory (never in localStorage or sessionStorage).
 * - Refresh tokens are handled via HttpOnly, SameSite cookies managed by the browser.
 * - CSRF double-submit protection: reads the `csrf_token` cookie and attaches `X-CSRF-Token` header.
 * - Single-tab refresh deduplication: concurrent refresh attempts share a single inflight promise.
 * - Cross-tab refresh coordination: uses Web Locks API ('climaforge_refresh_lock') and
 *   BroadcastChannel ('climaforge_auth') to ensure only one tab rotates tokens at a time,
 *   preventing replay-protection family revocation across multiple browser tabs.
 * - Passwords, refresh tokens, and cookies are never logged or broadcast.
 */

import type { UserProfile, TokenResponse } from '../types/auth';
import { getApiBaseUrl } from './api';
import {
  executeWithRefreshLock,
  isRecentCrossTabSessionExpired,
  clearCrossTabState,
  recordRefreshCompletedCrossTab,
  recordSessionExpiredCrossTab,
  recordLogoutCrossTab,
  recordLoginCrossTab,
  onAuthBroadcast,
} from './authSync';

// ============================================================================
// In-Memory Token Storage (Strict Isolation)
// ============================================================================
let inMemoryAccessToken: string | null = null;

export function getAccessToken(): string | null {
  return inMemoryAccessToken;
}

export function setAccessToken(token: string | null): void {
  inMemoryAccessToken = token;
}

export function clearAccessToken(): void {
  inMemoryAccessToken = null;
  clearCrossTabState();
}

// Wire listener so cross-tab broadcasts update in-memory state automatically
export function setupAuthCrossTabSync(): () => void {
  return onAuthBroadcast((msg) => {
    if (msg.type === 'AUTH_LOGOUT') {
      clearAccessToken();
    } else if (msg.type === 'SESSION_EXPIRED') {
      clearAccessToken();
    }
  });
}

if (typeof window !== 'undefined') {
  setupAuthCrossTabSync();
}

// ============================================================================
// CSRF Cookie Extraction
// ============================================================================
export function getCsrfToken(): string | null {
  if (typeof document === 'undefined' || !document.cookie) {
    return null;
  }
  const match = document.cookie.match(/(?:^|;\s*)csrf_token=([^;]+)/);
  if (!match) {
    return null;
  }
  return decodeURIComponent(match[1]);
}

// ============================================================================
// Session Expiration Event Bus
// ============================================================================
type SessionExpiredListener = () => void;
const sessionExpiredListeners: Set<SessionExpiredListener> = new Set();

export function onSessionExpired(listener: SessionExpiredListener): () => void {
  sessionExpiredListeners.add(listener);
  return () => {
    sessionExpiredListeners.delete(listener);
  };
}

export function notifySessionExpired(broadcast = true): void {
  clearAccessToken();
  if (broadcast) {
    recordSessionExpiredCrossTab();
  }
  sessionExpiredListeners.forEach((listener) => {
    try {
      listener();
    } catch {
      // Prevent listener failure from propagating
    }
  });
}

// ============================================================================
// Cross-Tab & Single-Tab Refresh Coordination (M16A.7)
// ============================================================================
let activeRefreshPromise: Promise<string | null> | null = null;

/**
 * Execute silent token refresh with Web Locks exclusive cross-tab coordination
 * and within-tab single-flight promise deduplication.
 *
 * Guarantees:
 * 1. Only ONE tab executes the network refresh call at any given moment via Web Locks.
 * 2. When Tab A finishes, the browser cookie jar contains the newly rotated refresh token.
 * 3. Waiting tabs execute sequentially using the updated cookie jar — preventing replay detection.
 * 4. Zero credentials (access token, refresh token, cookie, password) are ever broadcast.
 * 5. Access tokens exist STRICTLY within the private JavaScript memory of each tab context.
 */
export async function refreshAccessToken(): Promise<string | null> {
  // If a refresh is already in flight within this tab, reuse its promise
  if (activeRefreshPromise) {
    return activeRefreshPromise;
  }

  activeRefreshPromise = (async () => {
    try {
      return await executeWithRefreshLock(async () => {
        // 1. If another tab discovered the session was expired/revoked, abort immediately
        if (isRecentCrossTabSessionExpired()) {
          clearAccessToken();
          return null;
        }

        // 2. Issue the actual network refresh request with exclusive lock
        const baseUrl = getApiBaseUrl();
        const csrfToken = getCsrfToken();
        const headers: Record<string, string> = {
          Accept: 'application/json',
        };
        if (csrfToken) {
          headers['X-CSRF-Token'] = csrfToken;
        }

        const response = await fetch(`${baseUrl}/api/auth/refresh`, {
          method: 'POST',
          headers,
          credentials: 'include',
        });

        if (!response.ok) {
          clearAccessToken();
          recordSessionExpiredCrossTab();
          return null;
        }

        const data: TokenResponse = await response.json();
        // Access token is stored ONLY in this tab context's private memory
        setAccessToken(data.access_token);
        // Broadcast non-sensitive completion signal (timestamp only, NO tokens/secrets)
        recordRefreshCompletedCrossTab();
        return data.access_token;
      });
    } catch {
      clearAccessToken();
      return null;
    } finally {
      activeRefreshPromise = null;
    }
  })();

  return activeRefreshPromise;
}

// ============================================================================
// Authentication API Operations
// ============================================================================

export interface LoginResult {
  user: UserProfile;
  token: string;
}

/**
 * Submit user credentials to POST /api/auth/login.
 * On success, stores access token in memory, synchronizes across tabs,
 * and loads current user profile. Never logs credentials.
 */
export async function loginUser(email: string, password: string): Promise<LoginResult> {
  const baseUrl = getApiBaseUrl();

  let response: Response;
  try {
    response = await fetch(`${baseUrl}/api/auth/login`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Accept: 'application/json',
      },
      credentials: 'include',
      body: JSON.stringify({ email: email.trim().toLowerCase(), password }),
    });
  } catch (err) {
    const msg = err instanceof Error ? err.message : 'Network error';
    throw new Error(`Authentication service unavailable: ${msg}`);
  }

  if (!response.ok) {
    if (response.status === 401) {
      throw new Error('Invalid email or password.');
    }
    if (response.status === 403) {
      throw new Error('Account is deactivated. Contact an administrator.');
    }
    if (response.status === 429) {
      const retryAfter = response.headers.get('Retry-After');
      const waitMsg = retryAfter ? ` Please retry after ${retryAfter} seconds.` : ' Please try again later.';
      throw new Error(`Too many login attempts.${waitMsg}`);
    }
    let detailMsg = 'Authentication failed';
    try {
      const errJson = await response.json();
      if (errJson?.detail && typeof errJson.detail === 'string') {
        detailMsg = errJson.detail;
      }
    } catch {
      // Ignore body parsing error
    }
    throw new Error(detailMsg);
  }

  const tokenData: TokenResponse = await response.json();
  setAccessToken(tokenData.access_token);

  // Synchronize login state across tabs (never broadcasts credentials)
  recordLoginCrossTab();

  // Retrieve authenticated profile
  const user = await fetchCurrentUser();
  return { user, token: tokenData.access_token };
}

/**
 * Revoke the current refresh session and clear cookies via POST /api/auth/logout.
 * Idempotent: unconditionally clears client-side in-memory token and notifies all tabs.
 */
export async function logoutUser(): Promise<void> {
  const baseUrl = getApiBaseUrl();
  const csrfToken = getCsrfToken();
  const headers: Record<string, string> = {
    Accept: 'application/json',
  };
  if (csrfToken) {
    headers['X-CSRF-Token'] = csrfToken;
  }

  try {
    await fetch(`${baseUrl}/api/auth/logout`, {
      method: 'POST',
      headers,
      credentials: 'include',
    });
  } catch {
    // Logout always succeeds on client side even if server is unreachable
  } finally {
    clearAccessToken();
    recordLogoutCrossTab();
  }
}

/**
 * Fetch authenticated user profile via GET /api/auth/me.
 */
export async function fetchCurrentUser(): Promise<UserProfile> {
  const baseUrl = getApiBaseUrl();
  const token = getAccessToken();

  const headers: Record<string, string> = {
    Accept: 'application/json',
  };
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const response = await fetch(`${baseUrl}/api/auth/me`, {
    method: 'GET',
    headers,
    credentials: 'include',
  });

  if (!response.ok) {
    throw new Error(`Failed to load user profile (HTTP ${response.status})`);
  }

  return response.json();
}

/**
 * Attempt session restoration on application initialization.
 * Rotates refresh token if cookie exists and retrieves authenticated profile.
 * Returns null if unauthenticated or refresh token is invalid.
 */
export async function restoreSession(): Promise<UserProfile | null> {
  try {
    const token = await refreshAccessToken();
    if (!token) {
      return null;
    }
    return await fetchCurrentUser();
  } catch {
    clearAccessToken();
    return null;
  }
}

// Attach dev helpers in development mode for genuine browser E2E inspection
if (typeof window !== 'undefined' && import.meta.env.DEV) {
  (window as unknown as Record<string, unknown>).__CLIMAFORGE_AUTH__ = {
    getAccessToken,
    setAccessToken,
    clearAccessToken,
    refreshAccessToken,
    loginUser,
    logoutUser,
    fetchCurrentUser,
    restoreSession,
  };
}
