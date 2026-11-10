import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import {
  getAccessToken,
  setAccessToken,
  clearAccessToken,
  getCsrfToken,
  refreshAccessToken,
  loginUser,
  logoutUser,
  restoreSession,
  onSessionExpired,
  notifySessionExpired,
} from '../services/auth';

describe('Auth Service & In-Memory Token Management', () => {
  beforeEach(() => {
    clearAccessToken();
    // Clear cookies
    document.cookie = 'csrf_token=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;';
    document.cookie = 'climaforge_refresh_token=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;';
    vi.restoreAllMocks();
  });

  afterEach(() => {
    clearAccessToken();
    vi.restoreAllMocks();
  });

  it('stores access token strictly in-memory and never in web storage', () => {
    const localStorageSpy = vi.spyOn(Storage.prototype, 'setItem');
    const sessionStorageSpy = vi.spyOn(sessionStorage, 'setItem');

    expect(getAccessToken()).toBeNull();

    setAccessToken('test-access-token-123');
    expect(getAccessToken()).toBe('test-access-token-123');

    clearAccessToken();
    expect(getAccessToken()).toBeNull();

    // Verify localStorage and sessionStorage were never accessed
    expect(localStorageSpy).not.toHaveBeenCalled();
    expect(sessionStorageSpy).not.toHaveBeenCalled();
  });

  it('extracts CSRF token accurately from document.cookie', () => {
    expect(getCsrfToken()).toBeNull();

    document.cookie = 'theme=dark; path=/;';
    expect(getCsrfToken()).toBeNull();

    document.cookie = 'csrf_token=csrf-test-secret-value; path=/;';
    expect(getCsrfToken()).toBe('csrf-test-secret-value');

    document.cookie = 'other_cookie=123; path=/;';
    expect(getCsrfToken()).toBe('csrf-test-secret-value');
  });

  it('notifies session-expired listeners and clears in-memory token', () => {
    setAccessToken('valid-token');
    const listener = vi.fn();
    const unsubscribe = onSessionExpired(listener);

    notifySessionExpired();
    expect(listener).toHaveBeenCalledTimes(1);
    expect(getAccessToken()).toBeNull();

    // After unsubscribe, listener should not be called again
    unsubscribe();
    notifySessionExpired();
    expect(listener).toHaveBeenCalledTimes(1);
  });

  it('refreshes token with credentials:include and CSRF header', async () => {
    document.cookie = 'csrf_token=my-csrf-header-value; path=/;';

    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({
        access_token: 'new-rotated-token',
        token_type: 'bearer',
        expires_in: 900,
      }),
    });
    globalThis.fetch = fetchMock;

    const token = await refreshAccessToken();
    expect(token).toBe('new-rotated-token');
    expect(getAccessToken()).toBe('new-rotated-token');

    expect(fetchMock).toHaveBeenCalledTimes(1);
    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toContain('/api/auth/refresh');
    expect(init.method).toBe('POST');
    expect(init.credentials).toBe('include');
    expect(init.headers['X-CSRF-Token']).toBe('my-csrf-header-value');
  });

  it('deduplicates concurrent refresh requests to prevent replay token revocation', async () => {
    document.cookie = 'csrf_token=csrf-123; path=/;';

    let resolvePromise: (value: unknown) => void;
    const pendingPromise = new Promise((resolve) => {
      resolvePromise = resolve;
    });

    const fetchMock = vi.fn().mockImplementation(() =>
      pendingPromise.then(() => ({
        ok: true,
        status: 200,
        json: async () => ({
          access_token: 'deduped-token-xyz',
          token_type: 'bearer',
          expires_in: 900,
        }),
      }))
    );
    globalThis.fetch = fetchMock;

    // Trigger three simultaneous refresh calls
    const p1 = refreshAccessToken();
    const p2 = refreshAccessToken();
    const p3 = refreshAccessToken();

    // Resolve the single pending network call
    resolvePromise!(null);

    const [t1, t2, t3] = await Promise.all([p1, p2, p3]);

    expect(t1).toBe('deduped-token-xyz');
    expect(t2).toBe('deduped-token-xyz');
    expect(t3).toBe('deduped-token-xyz');

    // Crucial: exactly ONE network fetch call was made!
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });

  it('handles refresh failure gracefully by clearing token and returning null', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: false,
      status: 401,
      json: async () => ({ detail: 'Authentication required' }),
    });
    globalThis.fetch = fetchMock;
    setAccessToken('stale-token');

    const result = await refreshAccessToken();
    expect(result).toBeNull();
    expect(getAccessToken()).toBeNull();
  });

  it('executes successful login and retrieves authenticated user profile', async () => {
    const userProfile = {
      id: 'usr-10',
      email: 'operator@climaforge.local',
      full_name: 'Lead Operator',
      role: 'operator',
      is_active: true,
      created_at: '2026-01-01T00:00:00Z',
    };

    const fetchMock = vi.fn().mockImplementation((url: string) => {
      if (url.includes('/api/auth/login')) {
        return Promise.resolve({
          ok: true,
          status: 200,
          json: async () => ({
            access_token: 'jwt-access-token-abc',
            token_type: 'bearer',
            expires_in: 900,
          }),
        });
      }
      if (url.includes('/api/auth/me')) {
        return Promise.resolve({
          ok: true,
          status: 200,
          json: async () => userProfile,
        });
      }
      return Promise.reject(new Error(`Unhandled URL: ${url}`));
    });
    globalThis.fetch = fetchMock;

    const result = await loginUser('Operator@Climaforge.LOCAL', 'CorrectPassword123!');

    expect(result.token).toBe('jwt-access-token-abc');
    expect(result.user).toEqual(userProfile);
    expect(getAccessToken()).toBe('jwt-access-token-abc');

    // Verify email was normalized to lowercase
    const loginCall = fetchMock.mock.calls.find(([u]) => u.includes('/api/auth/login'));
    expect(loginCall).toBeDefined();
    const loginBody = JSON.parse(loginCall![1].body as string);
    expect(loginBody.email).toBe('operator@climaforge.local');
    expect(loginCall![1].credentials).toBe('include');
  });

  it('throws specific error on invalid credentials (HTTP 401)', async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 401,
      json: async () => ({ detail: 'Invalid credentials' }),
    });

    await expect(loginUser('test@climaforge.local', 'WrongPassword')).rejects.toThrow(
      'Invalid email or password.'
    );
  });

  it('throws specific error on inactive account (HTTP 403)', async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 403,
      json: async () => ({ detail: 'Account is inactive' }),
    });

    await expect(loginUser('inactive@climaforge.local', 'Password123')).rejects.toThrow(
      'Account is deactivated. Contact an administrator.'
    );
  });

  it('throws rate limit error with retry-after header (HTTP 429)', async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 429,
      headers: new Headers({ 'Retry-After': '60' }),
      json: async () => ({ detail: 'Too many login attempts' }),
    });

    await expect(loginUser('test@climaforge.local', 'Password123')).rejects.toThrow(
      'Too many login attempts. Please retry after 60 seconds.'
    );
  });

  it('logs out securely by notifying server with CSRF token and clearing in-memory token', async () => {
    document.cookie = 'csrf_token=csrf-logout-token; path=/;';
    setAccessToken('active-token-to-be-cleared');

    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({ message: 'Logged out successfully' }),
    });
    globalThis.fetch = fetchMock;

    await logoutUser();

    expect(getAccessToken()).toBeNull();
    expect(fetchMock).toHaveBeenCalledTimes(1);
    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toContain('/api/auth/logout');
    expect(init.method).toBe('POST');
    expect(init.credentials).toBe('include');
    expect(init.headers['X-CSRF-Token']).toBe('csrf-logout-token');
  });

  it('restores session when valid refresh cookie exists', async () => {
    const userProfile = {
      id: 'usr-restore',
      email: 'restored@climaforge.local',
      full_name: 'Restored User',
      role: 'analyst',
      is_active: true,
      created_at: '2026-01-01T00:00:00Z',
    };

    globalThis.fetch = vi.fn().mockImplementation((url: string) => {
      if (url.includes('/api/auth/refresh')) {
        return Promise.resolve({
          ok: true,
          status: 200,
          json: async () => ({
            access_token: 'restored-jwt-token',
            token_type: 'bearer',
            expires_in: 900,
          }),
        });
      }
      if (url.includes('/api/auth/me')) {
        return Promise.resolve({
          ok: true,
          status: 200,
          json: async () => userProfile,
        });
      }
      return Promise.reject(new Error(`Unhandled URL: ${url}`));
    });

    const user = await restoreSession();
    expect(user).toEqual(userProfile);
    expect(getAccessToken()).toBe('restored-jwt-token');
  });

  it('returns null on session restore when unauthenticated', async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 401,
      json: async () => ({ detail: 'Authentication required' }),
    });

    const user = await restoreSession();
    expect(user).toBeNull();
    expect(getAccessToken()).toBeNull();
  });
});
