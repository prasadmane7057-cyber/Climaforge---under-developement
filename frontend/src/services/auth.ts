/**
 * Authentication and secure session client for CLIMAFORGE M16A.6.
 *
 * Security Principles:
 * - Access tokens are stored exclusively in-memory (never in localStorage or sessionStorage).
 * - Refresh tokens are handled via HttpOnly, SameSite cookies managed by the browser.
 * - CSRF double-submit protection: reads the `csrf_token` cookie and attaches `X-CSRF-Token` header.
 * - Refresh deduplication: concurrent refresh attempts share a single inflight promise to prevent
 *   replay-protection family revocation races on the backend.
 * - Passwords and raw tokens are never logged.
 */

import type { UserProfile, TokenResponse } from '../types/auth';
import { getApiBaseUrl } from './api';

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

export function notifySessionExpired(): void {
  clearAccessToken();
  sessionExpiredListeners.forEach((listener) => {
    try {
      listener();
    } catch {
      // Prevent listener failure from propagating
    }
  });
}

// ============================================================================
// Concurrent Refresh Deduplication
// ============================================================================
let activeRefreshPromise: Promise<string | null> | null = null;

/**
 * Execute silent token refresh with atomic promise deduplication.
 * Concurrency guard prevents replay-protection revocation from simultaneous 401s.
 */
export async function refreshAccessToken(): Promise<string | null> {
  if (activeRefreshPromise) {
    return activeRefreshPromise;
  }

  activeRefreshPromise = (async () => {
    try {
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
        return null;
      }

      const data: TokenResponse = await response.json();
      setAccessToken(data.access_token);
      return data.access_token;
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
 * On success, stores access token in memory and loads current user profile.
 * Never logs credentials.
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

  // Retrieve authenticated profile
  const user = await fetchCurrentUser();
  return { user, token: tokenData.access_token };
}

/**
 * Revoke the current refresh session and clear cookies via POST /api/auth/logout.
 * Idempotent: unconditionally clears client-side in-memory token.
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

