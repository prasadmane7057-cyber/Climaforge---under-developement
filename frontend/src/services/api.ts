/**
 * API service client for CLIMAFORGE backend.
 */

import type {
  HealthResponse,
  ScenarioSummaryItem,
  ScenarioDetail,
  AuditEvent,
  ScenarioAnalysisResponse,
} from '../types/api';

const DEFAULT_API_URL = 'http://localhost:8000';

export function getApiBaseUrl(): string {
  const envUrl = import.meta.env.VITE_API_URL;
  if (envUrl && typeof envUrl === 'string' && envUrl.trim() !== '') {
    return envUrl.trim().replace(/\/+$/, '');
  }
  return DEFAULT_API_URL;
}

export interface HealthCheckResult {
  success: boolean;
  data?: HealthResponse;
  latencyMs?: number;
  errorMessage?: string;
  errorDetails?: string;
  targetUrl: string;
}

export async function checkBackendHealth(timeoutMs = 4000): Promise<HealthCheckResult> {
  const baseUrl = getApiBaseUrl();
  const targetUrl = `${baseUrl}/health`;
  const startTime = performance.now();

  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

  try {
    const response = await fetch(targetUrl, {
      method: 'GET',
      headers: {
        Accept: 'application/json',
      },
      signal: controller.signal,
    });

    clearTimeout(timeoutId);
    const latencyMs = Math.round(performance.now() - startTime);

    if (!response.ok) {
      return {
        success: false,
        latencyMs,
        targetUrl,
        errorMessage: `Backend returned HTTP ${response.status}: ${response.statusText}`,
        errorDetails: 'The backend server was reached but responded with an error code.',
      };
    }

    const data: HealthResponse = await response.json();
    return {
      success: true,
      data,
      latencyMs,
      targetUrl,
    };
  } catch (err: unknown) {
    clearTimeout(timeoutId);
    const latencyMs = Math.round(performance.now() - startTime);

    let errorMessage = 'Failed to connect to backend server';
    let errorDetails =
      'Ensure the FastAPI server is running at the configured URL and CORS allows connections from this origin.';

    if (err instanceof Error) {
      if (err.name === 'AbortError') {
        errorMessage = `Connection timed out after ${timeoutMs}ms`;
        errorDetails = `The server at ${targetUrl} did not respond in time. Verify the host and port.`;
      } else if (err.message.includes('Failed to fetch') || err.message.includes('NetworkError')) {
        errorMessage = 'Network connection refused';
        errorDetails =
          'Could not establish a connection to ' +
          targetUrl +
          '. Check that the backend uvicorn service is started on port 8000.';
      } else {
        errorMessage = err.message;
      }
    }

    return {
      success: false,
      latencyMs,
      targetUrl,
      errorMessage,
      errorDetails,
    };
  }
}

/**
 * Fetch list of all available demonstration scenarios.
 */
export async function fetchScenarios(): Promise<ScenarioSummaryItem[]> {
  const baseUrl = getApiBaseUrl();
  const response = await fetch(`${baseUrl}/api/scenarios`, {
    headers: { Accept: 'application/json' },
  });
  if (!response.ok) {
    throw new Error(`Failed to fetch scenarios (HTTP ${response.status})`);
  }
  return response.json();
}

/**
 * Fetch detailed metrics for a specific scenario.
 */
export async function fetchScenarioDetail(scenarioId: string): Promise<ScenarioDetail> {
  const baseUrl = getApiBaseUrl();
  const response = await fetch(`${baseUrl}/api/scenarios/${encodeURIComponent(scenarioId)}`, {
    headers: { Accept: 'application/json' },
  });
  if (!response.ok) {
    throw new Error(`Failed to fetch scenario details for '${scenarioId}' (HTTP ${response.status})`);
  }
  return response.json();
}

/**
 * Fetch recorded session audit logs.
 */
export async function fetchAuditLogs(): Promise<AuditEvent[]> {
  const baseUrl = getApiBaseUrl();
  const response = await fetch(`${baseUrl}/api/audit-logs`, {
    headers: { Accept: 'application/json' },
  });
  if (!response.ok) {
    throw new Error(`Failed to fetch audit logs (HTTP ${response.status})`);
  }
  return response.json();
}

/**
 * Record an authentic client-side operator event to the backend audit log.
 */
export async function recordClientAuditEvent(
  eventType: string,
  description: string,
  details: Record<string, string> = {}
): Promise<AuditEvent | null> {
  try {
    const baseUrl = getApiBaseUrl();
    const response = await fetch(`${baseUrl}/api/audit-logs`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Accept: 'application/json',
      },
      body: JSON.stringify({
        event_type: eventType,
        description,
        details,
      }),
    });
    if (response.ok) {
      return response.json();
    }
  } catch {
    // Fail silently on analytics/audit logging if disconnected
  }
  return null;
}

/**
 * Execute deterministic calculation pipeline (Algorithms 0–3) on the backend.
 */
export async function runScenarioAnalysis(scenarioId: string): Promise<ScenarioAnalysisResponse> {
  const baseUrl = getApiBaseUrl();
  const targetUrl = `${baseUrl}/api/scenarios/${encodeURIComponent(scenarioId)}/analyze`;

  const response = await fetch(targetUrl, {
    method: 'POST',
    headers: {
      Accept: 'application/json',
      'Content-Type': 'application/json',
    },
  });

  if (!response.ok) {
    let detailMsg = `HTTP ${response.status}: ${response.statusText}`;
    try {
      const errJson = await response.json();
      if (errJson && errJson.detail) {
        detailMsg = typeof errJson.detail === 'string' ? errJson.detail : JSON.stringify(errJson.detail);
      }
    } catch {
      // ignore json parse error
    }
    throw new Error(`Analysis run failed: ${detailMsg}`);
  }

  return response.json();
}
