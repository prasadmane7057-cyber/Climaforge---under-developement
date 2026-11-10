import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import {
  authenticatedFetch,
  fetchScenarioDetail,
  fetchAuditLogs,
  runScenarioAnalysis,
  predictFloodRisk,
  askGroundedChatbot,
} from '../services/api';
import {
  setAccessToken,
  clearAccessToken,
  onSessionExpired,
} from '../services/auth';

describe('Authenticated Fetch Interceptor & API Services', () => {
  beforeEach(() => {
    clearAccessToken();
    document.cookie = 'csrf_token=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;';
    vi.restoreAllMocks();
  });

  afterEach(() => {
    clearAccessToken();
    vi.restoreAllMocks();
  });

  it('attaches credentials:include and Authorization bearer header when token exists', async () => {
    setAccessToken('bearer-token-abc');

    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({ status: 'ok' }),
    });
    globalThis.fetch = fetchMock;

    await authenticatedFetch('http://localhost:8000/api/test');

    expect(fetchMock).toHaveBeenCalledTimes(1);
    const [, init] = fetchMock.mock.calls[0];
    expect(init.credentials).toBe('include');
    expect((init.headers as Headers).get('Authorization')).toBe('Bearer bearer-token-abc');
  });

  it('attaches X-CSRF-Token header on POST/PUT/DELETE when csrf cookie is present', async () => {
    document.cookie = 'csrf_token=double-submit-secret; path=/;';

    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({}),
    });
    globalThis.fetch = fetchMock;

    // 1. POST request
    await authenticatedFetch('http://localhost:8000/api/resource', { method: 'POST' });
    let [, init] = fetchMock.mock.calls[0];
    expect((init.headers as Headers).get('X-CSRF-Token')).toBe('double-submit-secret');

    // 2. GET request should NOT attach X-CSRF-Token
    await authenticatedFetch('http://localhost:8000/api/resource', { method: 'GET' });
    [, init] = fetchMock.mock.calls[1];
    expect((init.headers as Headers).get('X-CSRF-Token')).toBeNull();
  });

  it('transparently rotates token on 401 and retries original request once', async () => {
    setAccessToken('expired-access-token');
    document.cookie = 'csrf_token=my-csrf; path=/;';

    let originalRequestAttempt = 0;
    const fetchMock = vi.fn().mockImplementation((url: string) => {
      if (url.includes('/api/auth/refresh')) {
        return Promise.resolve({
          ok: true,
          status: 200,
          json: async () => ({
            access_token: 'fresh-new-token-xyz',
            token_type: 'bearer',
            expires_in: 900,
          }),
        });
      }
      if (url.includes('/api/scenarios/scenario-1/analyze')) {
        originalRequestAttempt++;
        if (originalRequestAttempt === 1) {
          // First attempt fails with 401
          return Promise.resolve({
            ok: false,
            status: 401,
            json: async () => ({ detail: 'Token expired' }),
          });
        }
        // Retry attempt succeeds with 200
        return Promise.resolve({
          ok: true,
          status: 200,
          json: async () => ({ scenario_id: 'scenario-1', pipeline_status: 'SUCCESS' }),
        });
      }
      return Promise.reject(new Error(`Unknown url: ${url}`));
    });
    globalThis.fetch = fetchMock;

    const result = await runScenarioAnalysis('scenario-1');

    expect(result.pipeline_status).toBe('SUCCESS');
    expect(originalRequestAttempt).toBe(2);

    // Verify refresh was called between attempt 1 and attempt 2
    const refreshCall = fetchMock.mock.calls.find(([u]) => u.includes('/api/auth/refresh'));
    expect(refreshCall).toBeDefined();

    // Verify retry used the new token
    const secondAnalyzeCall = fetchMock.mock.calls[2];
    expect((secondAnalyzeCall[1].headers as Headers).get('Authorization')).toBe(
      'Bearer fresh-new-token-xyz'
    );
  });

  it('notifies session expiration and does not loop if refresh fails on 401', async () => {
    setAccessToken('invalid-token');
    const sessionExpiredSpy = vi.fn();
    const unsubscribe = onSessionExpired(sessionExpiredSpy);

    const fetchMock = vi.fn().mockImplementation((url: string) => {
      if (url.includes('/api/auth/refresh')) {
        return Promise.resolve({
          ok: false,
          status: 401,
          json: async () => ({ detail: 'Refresh token invalid' }),
        });
      }
      return Promise.resolve({
        ok: false,
        status: 401,
        json: async () => ({ detail: 'Authentication required' }),
      });
    });
    globalThis.fetch = fetchMock;

    const response = await authenticatedFetch('http://localhost:8000/api/scenarios');

    expect(response.status).toBe(401);
    expect(sessionExpiredSpy).toHaveBeenCalledTimes(1);

    unsubscribe();
  });

  it('passes authenticated requests from domain services', async () => {
    setAccessToken('valid-bearer');
    const fetchMock = vi.fn().mockImplementation((url: string) => {
      if (url.includes('/api/scenarios/test-sc')) {
        return Promise.resolve({
          ok: true,
          status: 200,
          json: async () => ({ scenario_id: 'test-sc', name: 'Test Scenario' }),
        });
      }
      if (url.includes('/api/audit-logs')) {
        return Promise.resolve({
          ok: true,
          status: 200,
          json: async () => [{ event_id: 'EVT-1' }],
        });
      }
      if (url.includes('/api/ml/flood/predict')) {
        return Promise.resolve({
          ok: true,
          status: 200,
          json: async () => ({ predicted_risk_class: 'HIGH', confidence: 0.88 }),
        });
      }
      if (url.includes('/api/chatbot/message')) {
        return Promise.resolve({
          ok: true,
          status: 200,
          json: async () => ({ answer: 'Safe route identified', source: 'DETERMINISTIC_FALLBACK' }),
        });
      }
      return Promise.resolve({ ok: true, status: 200, json: async () => [] });
    });
    globalThis.fetch = fetchMock;

    const sc = await fetchScenarioDetail('test-sc');
    expect(sc.scenario_id).toBe('test-sc');

    const logs = await fetchAuditLogs();
    expect(logs).toHaveLength(1);

    const ml = await predictFloodRisk({
      prcp_mm: 50,
      tmax_c: 25,
      tmin_c: 15,
      snow_mm: 0,
      prcp_lag1_mm: 40,
      prcp_rolling_3d_mean_mm: 45,
      prcp_rolling_7d_mean_mm: 40,
      prcp_rolling_14d_mean_mm: 35,
    });
    expect(ml.predicted_risk_class).toBe('HIGH');

    const chat = await askGroundedChatbot('test-sc', 'Where are the safe zones?');
    expect(chat.answer).toBe('Safe route identified');
  });
});
