/**
 * Offline Synchronization Service for CLIMAFORGE Milestone 7.
 *
 * Coordinates:
 * - Browser online/offline connection state detection.
 * - Idempotent SOS outbox drainage upon reconnection.
 * - Atomic state transitions from NOT_SENT to ACKNOWLEDGED.
 * - Concurrent sync protection and retry-safe failure retention.
 */

import { syncIncidents } from './api';
import {
  getQueuedIncidents,
  markIncidentsAcknowledged,
  type QueuedIncidentItem,
} from './offlineStorage';
import type { IncidentRecord, IncidentSyncResponse } from '../types/api';

export type SyncStatusListener = (state: {
  isOnline: boolean;
  isSyncing: boolean;
  lastSyncAt: Date | null;
  lastSyncError: string | null;
  outboxCount: number;
}) => void;

let isSyncing = false;
let lastSyncAt: Date | null = null;
let lastSyncError: string | null = null;
const listeners = new Set<SyncStatusListener>();

/**
 * Determine current browser connectivity status.
 */
export function getIsOnline(): boolean {
  if (typeof navigator !== 'undefined' && typeof navigator.onLine === 'boolean') {
    return navigator.onLine;
  }
  return true;
}

/**
 * Register a listener for synchronization state changes.
 */
export function subscribeSyncStatus(listener: SyncStatusListener): () => void {
  listeners.add(listener);
  return () => {
    listeners.delete(listener);
  };
}

function notifyListeners(outboxCount: number): void {
  const state = {
    isOnline: getIsOnline(),
    isSyncing,
    lastSyncAt,
    lastSyncError,
    outboxCount,
  };
  listeners.forEach((listener) => {
    try {
      listener(state);
    } catch {
      // Ignore listener error
    }
  });
}

/**
 * Synchronize all pending outbox records for a designated scenario.
 */
export async function syncOutbox(scenarioId: string): Promise<IncidentSyncResponse | null> {
  if (!scenarioId) {
    return null;
  }

  // Prevent concurrent sync collisions
  if (isSyncing) {
    return null;
  }

  if (!getIsOnline()) {
    lastSyncError = 'Cannot synchronize: Device is currently offline.';
    const queued = await getQueuedIncidents(scenarioId);
    notifyListeners(queued.length);
    return null;
  }

  isSyncing = true;
  lastSyncError = null;

  try {
    const queued: QueuedIncidentItem[] = await getQueuedIncidents(scenarioId);
    const pending = queued.filter((item) => item.status !== 'ACKNOWLEDGED');

    notifyListeners(queued.length);

    if (pending.length === 0) {
      isSyncing = false;
      notifyListeners(queued.length);
      return null;
    }

    // Convert to domain IncidentRecord payload
    const payload: IncidentRecord[] = pending.map((item) => ({
      incident_id: item.incident_id,
      reported_at: item.reported_at,
      zone_id: item.zone_id,
      latitude: item.latitude,
      longitude: item.longitude,
      incident_type: item.incident_type,
      urgency: item.urgency,
      status: item.status,
      description: item.description,
    }));

    // Execute backend sync
    const receipt: IncidentSyncResponse = await syncIncidents(scenarioId, payload);

    // Mark newly stored AND already existing duplicates as ACKNOWLEDGED in local outbox
    const successfulIds = [
      ...(receipt.synced_incident_ids || []),
      ...(receipt.duplicate_incident_ids || []),
    ];

    if (successfulIds.length > 0) {
      await markIncidentsAcknowledged(successfulIds);
    }

    lastSyncAt = new Date();
    lastSyncError = null;
    isSyncing = false;

    // Refresh count and notify listeners
    const updatedQueued = await getQueuedIncidents(scenarioId);
    notifyListeners(updatedQueued.length);

    return receipt;
  } catch (error) {
    isSyncing = false;
    lastSyncError = error instanceof Error ? error.message : String(error);
    const queued = await getQueuedIncidents(scenarioId).catch(() => []);
    notifyListeners(queued.length);
    throw error;
  }
}

/**
 * Initialize window network connectivity listeners for automatic reconnect sync.
 */
export function initOfflineSync(
  getActiveScenarioId: () => string,
  onAutoSyncCompleted?: (receipt: IncidentSyncResponse) => void,
): () => void {
  if (typeof window === 'undefined') {
    return () => {};
  }

  const handleOnline = async () => {
    const scenarioId = getActiveScenarioId();
    if (scenarioId) {
      try {
        const receipt = await syncOutbox(scenarioId);
        if (receipt && onAutoSyncCompleted) {
          onAutoSyncCompleted(receipt);
        }
      } catch {
        // Retain outbox items on error
      }
    }
  };

  const handleOffline = async () => {
    const scenarioId = getActiveScenarioId();
    const queued = scenarioId ? await getQueuedIncidents(scenarioId).catch(() => []) : [];
    notifyListeners(queued.length);
  };

  window.addEventListener('online', handleOnline);
  window.addEventListener('offline', handleOffline);

  return () => {
    window.removeEventListener('online', handleOnline);
    window.removeEventListener('offline', handleOffline);
  };
}

