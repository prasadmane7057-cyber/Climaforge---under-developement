/**
 * Native IndexedDB Offline Storage Service for CLIMAFORGE Milestone 7.
 *
 * Provides client-side durable offline persistence for:
 * - Scenario metadata and pre-calamity alerts (`scenario_cache`)
 * - Safe evacuation routes and turn-by-turn waypoints (`route_cache`)
 * - Citizen emergency distress reports (`sos_outbox`)
 */

import type {
  CachedScenarioBundle,
  EvacuationRouteResponse,
  IncidentRecord,
} from '../types/api';

export type { CachedScenarioBundle, EvacuationRouteResponse };

const DB_NAME = 'climaforge_offline_store';
const DB_VERSION = 1;

export const STORES = {
  SCENARIO_CACHE: 'scenario_cache',
  ROUTE_CACHE: 'route_cache',
  SOS_OUTBOX: 'sos_outbox',
} as const;

let dbInstance: IDBDatabase | null = null;
let isStorageAvailable: boolean | null = null;

/**
 * Check whether IndexedDB is supported and accessible in the current runtime environment.
 */
export function isIndexedDBAvailable(): boolean {
  if (isStorageAvailable !== null) {
    return isStorageAvailable;
  }
  try {
    if (typeof window === 'undefined' || !window.indexedDB) {
      isStorageAvailable = false;
      return false;
    }
    isStorageAvailable = true;
    return true;
  } catch {
    isStorageAvailable = false;
    return false;
  }
}

/**
 * Open or initialize the native IndexedDB database instance.
 */
export async function getDb(): Promise<IDBDatabase> {
  if (dbInstance) {
    return dbInstance;
  }

  if (!isIndexedDBAvailable()) {
    throw new Error('IndexedDB offline storage is unavailable in this browser environment.');
  }

  return new Promise((resolve, reject) => {
    try {
      const request = window.indexedDB.open(DB_NAME, DB_VERSION);

      request.onupgradeneeded = (event) => {
        const db = (event.target as IDBOpenDBRequest).result;

        // 1. Scenario Cache Store
        if (!db.objectStoreNames.contains(STORES.SCENARIO_CACHE)) {
          db.createObjectStore(STORES.SCENARIO_CACHE, { keyPath: 'scenario_id' });
        }

        // 2. Evacuation Route Cache Store
        if (!db.objectStoreNames.contains(STORES.ROUTE_CACHE)) {
          db.createObjectStore(STORES.ROUTE_CACHE, { keyPath: 'scenario_id' });
        }

        // 3. SOS Outbox Store
        if (!db.objectStoreNames.contains(STORES.SOS_OUTBOX)) {
          const outboxStore = db.createObjectStore(STORES.SOS_OUTBOX, { keyPath: 'incident_id' });
          outboxStore.createIndex('scenario_id', 'scenario_id', { unique: false });
          outboxStore.createIndex('status', 'status', { unique: false });
        }
      };

      request.onsuccess = (event) => {
        dbInstance = (event.target as IDBOpenDBRequest).result;
        dbInstance.onclose = () => {
          dbInstance = null;
        };
        resolve(dbInstance);
      };

      request.onerror = (event) => {
        const err = (event.target as IDBOpenDBRequest).error;
        reject(new Error(`Failed to open IndexedDB '${DB_NAME}': ${err?.message || 'Unknown error'}`));
      };

      request.onblocked = () => {
        reject(new Error(`IndexedDB open blocked: Close other tabs running '${DB_NAME}'.`));
      };
    } catch (exc) {
      reject(exc instanceof Error ? exc : new Error(String(exc)));
    }
  });
}

/**
 * Reset database reference (useful for testing or reconnect).
 */
export function resetDbInstance(): void {
  if (dbInstance) {
    try {
      dbInstance.close();
    } catch {
      // Ignore
    }
    dbInstance = null;
  }
  isStorageAvailable = null;
}

// ----------------------------------------------------------------------------
// 1. Scenario Data Cache Operations
// ----------------------------------------------------------------------------

export async function cacheScenarioData(data: CachedScenarioBundle): Promise<void> {
  const db = await getDb();
  return new Promise((resolve, reject) => {
    const tx = db.transaction([STORES.SCENARIO_CACHE], 'readwrite');
    const store = tx.objectStore(STORES.SCENARIO_CACHE);
    const request = store.put(data);

    request.onsuccess = () => resolve();
    request.onerror = () => reject(request.error || new Error('Failed to cache scenario data.'));
  });
}

export async function getCachedScenarioData(scenarioId: string): Promise<CachedScenarioBundle | null> {
  const db = await getDb();
  return new Promise((resolve, reject) => {
    const tx = db.transaction([STORES.SCENARIO_CACHE], 'readonly');
    const store = tx.objectStore(STORES.SCENARIO_CACHE);
    const request = store.get(scenarioId);

    request.onsuccess = () => {
      resolve(request.result || null);
    };
    request.onerror = () => reject(request.error || new Error(`Failed to read cached scenario '${scenarioId}'.`));
  });
}

// ----------------------------------------------------------------------------
// 2. Evacuation Route Cache Operations
// ----------------------------------------------------------------------------

export async function cacheRoute(route: EvacuationRouteResponse): Promise<void> {
  const db = await getDb();
  return new Promise((resolve, reject) => {
    const tx = db.transaction([STORES.ROUTE_CACHE], 'readwrite');
    const store = tx.objectStore(STORES.ROUTE_CACHE);
    const request = store.put(route);

    request.onsuccess = () => resolve();
    request.onerror = () => reject(request.error || new Error('Failed to cache evacuation route.'));
  });
}

export async function getCachedRoute(scenarioId: string): Promise<EvacuationRouteResponse | null> {
  const db = await getDb();
  return new Promise((resolve, reject) => {
    const tx = db.transaction([STORES.ROUTE_CACHE], 'readonly');
    const store = tx.objectStore(STORES.ROUTE_CACHE);
    const request = store.get(scenarioId);

    request.onsuccess = () => {
      resolve(request.result || null);
    };
    request.onerror = () => reject(request.error || new Error(`Failed to read cached route for '${scenarioId}'.`));
  });
}

// ----------------------------------------------------------------------------
// 3. Client SOS Outbox Operations
// ----------------------------------------------------------------------------

export interface QueuedIncidentItem extends IncidentRecord {
  scenario_id: string;
}

export async function queueIncident(incident: QueuedIncidentItem): Promise<void> {
  const db = await getDb();
  return new Promise((resolve, reject) => {
    const tx = db.transaction([STORES.SOS_OUTBOX], 'readwrite');
    const store = tx.objectStore(STORES.SOS_OUTBOX);
    const request = store.put(incident);

    request.onsuccess = () => resolve();
    request.onerror = () => reject(request.error || new Error('Failed to queue incident into offline outbox.'));
  });
}

export async function getQueuedIncidents(scenarioId?: string): Promise<QueuedIncidentItem[]> {
  const db = await getDb();
  return new Promise((resolve, reject) => {
    const tx = db.transaction([STORES.SOS_OUTBOX], 'readonly');
    const store = tx.objectStore(STORES.SOS_OUTBOX);
    const request = store.getAll();

    request.onsuccess = () => {
      const all: QueuedIncidentItem[] = request.result || [];
      if (!scenarioId) {
        resolve(all);
      } else {
        resolve(all.filter((item) => item.scenario_id === scenarioId));
      }
    };
    request.onerror = () => reject(request.error || new Error('Failed to read queued outbox incidents.'));
  });
}

export async function markIncidentsAcknowledged(incidentIds: string[]): Promise<void> {
  if (!incidentIds.length) return;
  const db = await getDb();
  return new Promise((resolve, reject) => {
    const tx = db.transaction([STORES.SOS_OUTBOX], 'readwrite');
    const store = tx.objectStore(STORES.SOS_OUTBOX);

    let completed = 0;
    let hasError = false;

    incidentIds.forEach((id) => {
      const getReq = store.get(id);
      getReq.onsuccess = () => {
        if (getReq.result) {
          const item: QueuedIncidentItem = getReq.result;
          item.status = 'ACKNOWLEDGED';
          store.put(item);
        }
        completed += 1;
        if (completed === incidentIds.length && !hasError) {
          resolve();
        }
      };
      getReq.onerror = () => {
        hasError = true;
        reject(getReq.error || new Error(`Failed to update acknowledgment status for '${id}'.`));
      };
    });

    tx.oncomplete = () => {
      resolve();
    };
    tx.onerror = () => {
      reject(tx.error || new Error('Transaction failed while marking incidents acknowledged.'));
    };
  });
}

export async function clearAcknowledgedIncidents(scenarioId?: string): Promise<void> {
  const db = await getDb();
  const all = await getQueuedIncidents(scenarioId);
  const ackIds = all.filter((i) => i.status === 'ACKNOWLEDGED').map((i) => i.incident_id);

  if (!ackIds.length) return;

  return new Promise((resolve, reject) => {
    const tx = db.transaction([STORES.SOS_OUTBOX], 'readwrite');
    const store = tx.objectStore(STORES.SOS_OUTBOX);

    ackIds.forEach((id) => {
      store.delete(id);
    });

    tx.oncomplete = () => resolve();
    tx.onerror = () => reject(tx.error || new Error('Failed to clear acknowledged outbox records.'));
  });
}

