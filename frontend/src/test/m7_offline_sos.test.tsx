import '@testing-library/jest-dom';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { EmergencyChatbotTab } from '../components/EmergencyChatbotTab';
import * as api from '../services/api';
import * as offlineStorage from '../services/offlineStorage';
import * as offlineSync from '../services/offlineSync';
import type {
  CachedScenarioBundle,
  IncidentSyncResponse,
} from '../types/api';
import type {
  QueuedIncidentItem,
} from '../services/offlineStorage';

// In-Memory Mock Implementation of IndexedDB for jsdom
class MockIDBObjectStore {
  data: Map<string, any>;
  keyPath: string;

  constructor(keyPath: string, initialData?: Map<string, any>) {
    this.keyPath = keyPath;
    this.data = initialData || new Map();
  }

  createIndex() {}

  put(item: any) {
    const key = item[this.keyPath];
    this.data.set(key, JSON.parse(JSON.stringify(item)));
    const req: any = { result: key };
    setTimeout(() => {
      if (req.onsuccess) req.onsuccess({ target: req });
    }, 0);
    return req;
  }

  get(key: string) {
    const item = this.data.get(key);
    const req: any = { result: item ? JSON.parse(JSON.stringify(item)) : undefined };
    setTimeout(() => {
      if (req.onsuccess) req.onsuccess({ target: req });
    }, 0);
    return req;
  }

  getAll() {
    const items = Array.from(this.data.values()).map((v) => JSON.parse(JSON.stringify(v)));
    const req: any = { result: items };
    setTimeout(() => {
      if (req.onsuccess) req.onsuccess({ target: req });
    }, 0);
    return req;
  }

  delete(key: string) {
    this.data.delete(key);
    const req: any = { result: undefined };
    setTimeout(() => {
      if (req.onsuccess) req.onsuccess({ target: req });
    }, 0);
    return req;
  }
}

class MockIDBDatabase {
  stores: Map<string, MockIDBObjectStore>;
  objectStoreNames: { contains: (name: string) => boolean };

  constructor(stores?: Map<string, MockIDBObjectStore>) {
    this.stores = stores || new Map();
    this.objectStoreNames = {
      contains: (name: string) => this.stores.has(name),
    };
  }

  createObjectStore(name: string, options: { keyPath: string }) {
    const store = new MockIDBObjectStore(options.keyPath);
    this.stores.set(name, store);
    return store;
  }

  transaction(storeNames: string[], _mode: string) {
    const store = this.stores.get(storeNames[0]);
    const tx: any = {
      objectStore: () => store,
      oncomplete: null,
      onerror: null,
    };
    setTimeout(() => {
      if (tx.oncomplete) tx.oncomplete();
    }, 5);
    return tx;
  }

  close() {}
}

function setupMockIndexedDB() {
  const sharedStores = new Map<string, MockIDBObjectStore>();

  const mockFactory: any = {
    open: vi.fn((_name: string, _version: number) => {
      const openReq: any = {
        result: null,
        error: null,
        onsuccess: null,
        onerror: null,
        onupgradeneeded: null,
      };

      setTimeout(() => {
        const db = new MockIDBDatabase(sharedStores);
        if (openReq.onupgradeneeded) {
          openReq.result = db;
          openReq.onupgradeneeded({ target: openReq });
        }
        openReq.result = db;
        if (openReq.onsuccess) {
          openReq.onsuccess({ target: openReq });
        }
      }, 0);

      return openReq;
    }),
  };

  (window as any).indexedDB = mockFactory;
  return sharedStores;
}

describe('Milestone 7: Panic Phase, Offline Cache & Client SOS Outbox', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    offlineStorage.resetDbInstance();
    setupMockIndexedDB();
  });

  afterEach(() => {
    offlineStorage.resetDbInstance();
  });

  it('initializes IndexedDB and executes scenario cache write and read', async () => {
    const bundle: CachedScenarioBundle = {
      scenario_id: 'scenario-flash-flood',
      scenario_name: 'Flash Flood Emergency',
      cached_at: new Date().toISOString(),
      alerts: [
        {
          alert_id: 'ALERT-001',
          scenario_id: 'scenario-flash-flood',
          zone_id: 'ZONE-001',
          zone_name: 'Riverside Industrial District',
          severity: 'CRITICAL',
          risk_score: 85.0,
          dominant_cause: 'Inundation',
          headline: 'Severe Flood Alert',
          description: 'Emergency warning',
          action_recommendation: 'Evacuate now',
          is_simulated: true,
          is_live_confirmed: false,
          disclaimer: 'SIMULATED',
          generated_at: new Date().toISOString(),
        },
      ],
      safe_points: [
        {
          safe_point_id: 'SP-01',
          name: 'City High School Shelter',
          zone_id: 'ZONE-003',
          capacity_persons: 1200,
          elevation_m: 35.0,
          label: 'SYNTHETIC',
          is_operational: true,
          amenities: ['First Aid'],
        },
      ],
    };

    await offlineStorage.cacheScenarioData(bundle);
    const retrieved = await offlineStorage.getCachedScenarioData('scenario-flash-flood');

    expect(retrieved).not.toBeNull();
    expect(retrieved?.scenario_id).toBe('scenario-flash-flood');
    expect(retrieved?.alerts.length).toBe(1);
    expect(retrieved?.safe_points[0].name).toBe('City High School Shelter');
  });

  it('queues emergency distress reports into outbox with NOT_SENT status', async () => {
    const incident: QueuedIncidentItem = {
      incident_id: '11111111-1111-4111-8111-111111111111',
      scenario_id: 'scenario-flash-flood',
      reported_at: new Date().toISOString(),
      zone_id: 'ZONE-001',
      incident_type: 'RISING_WATER',
      urgency: 'HIGH',
      status: 'NOT_SENT',
      description: 'Water breached defensive flood walls.',
      latitude: 40.71,
      longitude: -74.01,
    };

    await offlineStorage.queueIncident(incident);
    const queued = await offlineStorage.getQueuedIncidents('scenario-flash-flood');

    expect(queued.length).toBe(1);
    expect(queued[0].incident_id).toBe('11111111-1111-4111-8111-111111111111');
    expect(queued[0].status).toBe('NOT_SENT');
    expect(queued[0].incident_type).toBe('RISING_WATER');
  });

  it('persists queued outbox records across reloads', async () => {
    const item1: QueuedIncidentItem = {
      incident_id: '22222222-2222-4222-8222-222222222222',
      scenario_id: 'scenario-flash-flood',
      reported_at: new Date().toISOString(),
      zone_id: 'ZONE-002',
      incident_type: 'MEDICAL_EMERGENCY',
      urgency: 'CRITICAL',
      status: 'NOT_SENT',
      description: 'Trapped oxygen patient needing extraction.',
    };

    await offlineStorage.queueIncident(item1);

    // Simulate page reload by resetting database instance
    offlineStorage.resetDbInstance();

    const retrieved = await offlineStorage.getQueuedIncidents('scenario-flash-flood');
    expect(retrieved.length).toBe(1);
    expect(retrieved[0].incident_id).toBe('22222222-2222-4222-8222-222222222222');
    expect(retrieved[0].status).toBe('NOT_SENT');
  });

  it('marks synchronized records as ACKNOWLEDGED in local store', async () => {
    const id = '33333333-3333-4333-8333-333333333333';
    await offlineStorage.queueIncident({
      incident_id: id,
      scenario_id: 'scenario-flash-flood',
      reported_at: new Date().toISOString(),
      zone_id: 'ZONE-001',
      incident_type: 'STRANDED_PERSONS',
      urgency: 'HIGH',
      status: 'NOT_SENT',
      description: 'Family stranded on rooftop.',
    });

    await offlineStorage.markIncidentsAcknowledged([id]);
    const items = await offlineStorage.getQueuedIncidents('scenario-flash-flood');

    expect(items[0].status).toBe('ACKNOWLEDGED');
  });

  it('synchronizes outbox through offlineSync and transitions status from NOT_SENT to ACKNOWLEDGED', async () => {
    const incId = '44444444-4444-4444-8444-444444444444';
    await offlineStorage.queueIncident({
      incident_id: incId,
      scenario_id: 'scenario-flash-flood',
      reported_at: new Date().toISOString(),
      zone_id: 'ZONE-001',
      incident_type: 'ROAD_BLOCKED',
      urgency: 'MEDIUM',
      status: 'NOT_SENT',
      description: 'Highway exit obstructed by debris.',
    });

    const mockSyncResponse: IncidentSyncResponse = {
      scenario_id: 'scenario-flash-flood',
      synced_incident_ids: [incId],
      duplicate_incident_ids: [],
      rejected_incident_ids: [],
      total_received: 1,
      total_synced: 1,
      total_duplicates: 0,
      acknowledged_at: new Date().toISOString(),
      status: 'ACKNOWLEDGED',
      disclaimer: 'SIMULATED CITIZEN SOS RECEIPT',
    };

    const syncSpy = vi.spyOn(api, 'syncIncidents').mockResolvedValue(mockSyncResponse);

    const receipt = await offlineSync.syncOutbox('scenario-flash-flood');

    expect(syncSpy).toHaveBeenCalledTimes(1);
    expect(receipt?.total_synced).toBe(1);

    const updated = await offlineStorage.getQueuedIncidents('scenario-flash-flood');
    expect(updated[0].status).toBe('ACKNOWLEDGED');
  });

  it('retains pending NOT_SENT records in outbox when network sync fails', async () => {
    const incId = '55555555-5555-4555-8555-555555555555';
    await offlineStorage.queueIncident({
      incident_id: incId,
      scenario_id: 'scenario-flash-flood',
      reported_at: new Date().toISOString(),
      zone_id: 'ZONE-001',
      incident_type: 'RISING_WATER',
      urgency: 'HIGH',
      status: 'NOT_SENT',
      description: 'Network failure retention test.',
    });

    vi.spyOn(api, 'syncIncidents').mockRejectedValue(new Error('503 Service Unavailable'));

    await expect(offlineSync.syncOutbox('scenario-flash-flood')).rejects.toThrow('503 Service Unavailable');

    const stored = await offlineStorage.getQueuedIncidents('scenario-flash-flood');
    expect(stored.length).toBe(1);
    expect(stored[0].status).toBe('NOT_SENT');
  });

  it('renders Panic Phase UI, queues SOS distress reports, and displays NOT_SENT status in outbox', async () => {
    vi.spyOn(api, 'fetchScenarioAlerts').mockResolvedValue({
      scenario_id: 'scenario-flash-flood',
      scenario_name: 'Flash Flood Emergency',
      generated_at: new Date().toISOString(),
      highest_severity: 'CRITICAL',
      affected_zone_count: 1,
      is_simulated: true,
      is_live_confirmed: false,
      disclaimer: 'Advisory simulated alerts only.',
      alerts: [],
    });
    vi.spyOn(api, 'fetchScenarioSafePoints').mockResolvedValue({
      scenario_id: 'scenario-flash-flood',
      safe_points: [],
      total_shelter_capacity: 0,
      highest_elevation_m: 0,
    });

    render(
      <EmergencyChatbotTab
        backendOnline={true}
        scenarioId="scenario-flash-flood"
        scenarioName="Flash Flood Emergency"
      />,
    );

    // Verify Panic Phase controls are rendered
    expect(screen.getByText(/Enter Panic Phase \(Offline SOS\)/i)).toBeTruthy();
    expect(screen.getByText(/Emergency SOS Distress Dispatch/i)).toBeTruthy();
    expect(screen.getByText(/Client SOS Outbox Queue/i)).toBeTruthy();

    // Toggle panic phase button
    const panicBtn = screen.getByText(/Enter Panic Phase \(Offline SOS\)/i);
    fireEvent.click(panicBtn);

    expect(screen.getByText(/PANIC PHASE ACTIVE/i)).toBeTruthy();
    expect(screen.getByText(/OFFLINE SURVIVAL MODE/i)).toBeTruthy();

    // Fill SOS Distress Form
    const descInput = screen.getByLabelText(/Distress Situation \/ Description/i);
    fireEvent.change(descInput, { target: { value: 'Water rising fast, family trapped on roof.' } });

    const submitBtn = screen.getByText(/Record Emergency SOS \(Queue Outbox\)/i);
    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(screen.getByText(/Water rising fast, family trapped on roof./i)).toBeTruthy();
      expect(screen.getAllByText(/NOT_SENT/i).length).toBeGreaterThanOrEqual(1);
    });
  });

  it('displays explicit storage warning banner when IndexedDB is unavailable', () => {
    (window as any).indexedDB = undefined;
    offlineStorage.resetDbInstance();

    expect(offlineStorage.isIndexedDBAvailable()).toBe(false);

    render(
      <EmergencyChatbotTab
        backendOnline={true}
        scenarioId="scenario-flash-flood"
        scenarioName="Flash Flood Emergency"
      />,
    );

    expect(screen.getByText(/IndexedDB Unavailable:/i)).toBeTruthy();
  });
});

