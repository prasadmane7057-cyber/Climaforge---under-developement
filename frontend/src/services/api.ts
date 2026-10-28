/**
 * API service client for CLIMAFORGE backend.
 */

import type { HealthResponse } from '../types/api';

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
