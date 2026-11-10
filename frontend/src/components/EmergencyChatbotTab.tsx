import React, { useEffect, useState } from 'react';
import type { FormEvent } from 'react';
import {
  AlertOctagon,
  AlertTriangle,
  CheckCircle2,
  Clock,
  Compass,
  Flame,
  HardDrive,
  Info,
  Navigation,
  Radio,
  RefreshCw,
  Send,
  ShieldAlert,
  ShieldCheck,
  Trash2,
  Wifi,
  WifiOff,
} from 'lucide-react';
import {
  askGroundedChatbot,
  fetchScenarioAlerts,
  fetchScenarioSafePoints,
  requestEvacuationRoute,
  streamChatbotMessage,
} from '../services/api';
import {
  cacheRoute,
  cacheScenarioData,
  clearAcknowledgedIncidents,
  getCachedRoute,
  getCachedScenarioData,
  getQueuedIncidents,
  isIndexedDBAvailable,
  queueIncident,
  type QueuedIncidentItem,
} from '../services/offlineStorage';
import {
  getIsOnline,
  initOfflineSync,
  subscribeSyncStatus,
  syncOutbox,
} from '../services/offlineSync';
import type {
  ChatHistoryItem,
  CitizenAlertItem,
  EvacuationRouteResponse,
  SafePointDetail,
} from '../types/api';

interface EmergencyChatbotTabProps {
  backendOnline: boolean;
  scenarioId: string;
  scenarioName?: string;
}

interface ChatMessage {
  id: string;
  role: 'assistant' | 'user';
  text: string;
  source: 'DETERMINISTIC_FALLBACK' | 'LLM' | 'SYSTEM' | 'MOCK' | 'NUGEN_AI';
}

const suggestedPrompts = [
  'What is the safest evacuation route from Riverside (ZONE-001)?',
  'Which evacuation shelters are operational and safe?',
  'Which locations have active critical flood warnings?',
  'Explain the current risk assessment in simple language',
  'What are the main consequences identified by the engine?',
  'Why is this intervention recommended?',
];

export const EmergencyChatbotTab: React.FC<EmergencyChatbotTabProps> = ({
  backendOnline,
  scenarioId,
  scenarioName,
}) => {
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: 'welcome',
      role: 'assistant',
      text: 'Hello, I am CLIMAFORGE AI, your climate-risk and disaster-management assistant powered by Nugen AI (Qwen/Qwen2.5-0.5B-Instruct). I provide guidance on flood risks, safe evacuation corridors, and emergency preparedness. How can I assist you today?',
      source: 'SYSTEM',
    },
  ]);
  const [draft, setDraft] = useState('');
  const [isSending, setIsSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lastFailedQuestion, setLastFailedQuestion] = useState<string | null>(null);
  const [_currentMode, setCurrentMode] = useState<'grounded_llm' | 'deterministic_fallback' | 'mock_advisory' | null>(null);

  // Milestone 6 Pre-Calamity Alerts State
  const [alerts, setAlerts] = useState<CitizenAlertItem[]>([]);
  const [isLoadingAlerts, setIsLoadingAlerts] = useState(false);
  const [alertsError, setAlertsError] = useState<string | null>(null);

  // Milestone 6 Safe Evacuation Routing State
  const [safePoints, setSafePoints] = useState<SafePointDetail[]>([]);
  const [selectedOrigin, setSelectedOrigin] = useState<string>('ZONE-001');
  const [selectedDestination, setSelectedDestination] = useState<string>('');
  const [activeRoute, setActiveRoute] = useState<EvacuationRouteResponse | null>(null);
  const [isPlanningRoute, setIsPlanningRoute] = useState(false);
  const [routingError, setRoutingError] = useState<string | null>(null);

  // Milestone 7 Panic Phase, Offline Cache & Client SOS Outbox State
  const [isPanicMode, setIsPanicMode] = useState<boolean>(false);
  const [isBrowserOnline, setIsBrowserOnline] = useState<boolean>(getIsOnline());
  const [isUsingCachedData, setIsUsingCachedData] = useState<boolean>(false);
  const [cachedAtTimestamp, setCachedAtTimestamp] = useState<string | null>(null);
  const [storageSupported] = useState<boolean>(isIndexedDBAvailable());
  const [outboxItems, setOutboxItems] = useState<QueuedIncidentItem[]>([]);
  const [isSyncingOutbox, setIsSyncingOutbox] = useState<boolean>(false);
  const [syncFeedback, setSyncFeedback] = useState<string | null>(null);

  // SOS Distress Form State
  const [sosType, setSosType] = useState<string>('RISING_WATER');
  const [sosUrgency, setSosUrgency] = useState<'CRITICAL' | 'HIGH' | 'MEDIUM'>('HIGH');
  const [sosZone, setSosZone] = useState<string>('ZONE-001');
  const [sosDescription, setSosDescription] = useState<string>('');
  const [sosIncludeGps, setSosIncludeGps] = useState<boolean>(false);
  const [sosLat, setSosLat] = useState<string>('');
  const [sosLon, setSosLon] = useState<string>('');
  const [formFeedback, setFormFeedback] = useState<string | null>(null);

  const effectiveOnline = backendOnline && isBrowserOnline;

  // Refresh outbox items from IndexedDB
  const refreshOutbox = async () => {
    if (!storageSupported) return;
    try {
      const items = await getQueuedIncidents(scenarioId);
      setOutboxItems(items);
    } catch {
      // Ignore
    }
  };

  // Subscribe to offline sync listeners
  useEffect(() => {
    const unsubscribeStatus = subscribeSyncStatus((state) => {
      setIsBrowserOnline(state.isOnline);
      setIsSyncingOutbox(state.isSyncing);
      if (state.lastSyncError) {
        setSyncFeedback(`Sync error: ${state.lastSyncError}`);
      }
    });

    const cleanupAutoSync = initOfflineSync(
      () => scenarioId,
      (receipt) => {
        setSyncFeedback(
          `Auto-sync complete: ${receipt.total_synced} incident(s) acknowledged (${receipt.total_duplicates} duplicates).`,
        );
        refreshOutbox();
      },
    );

    refreshOutbox();

    return () => {
      unsubscribeStatus();
      cleanupAutoSync();
    };
  }, [scenarioId, storageSupported]);

  // Load alerts and safe points (online fetch with background cache, or offline cache fallback)
  useEffect(() => {
    let isCancelled = false;

    const loadEmergencyData = async () => {
      if (!scenarioId) {
        setAlerts([]);
        setSafePoints([]);
        setActiveRoute(null);
        return;
      }

      // If online: fetch fresh data from backend and update local IndexedDB cache
      if (effectiveOnline) {
        setIsLoadingAlerts(true);
        setAlertsError(null);
        try {
          const [alertsResponse, safePointsResponse] = await Promise.all([
            fetchScenarioAlerts(scenarioId),
            fetchScenarioSafePoints(scenarioId),
          ]);
          if (!isCancelled) {
            const fetchedAlerts = alertsResponse.alerts || [];
            const fetchedSafePoints = safePointsResponse.safe_points || [];
            setAlerts(fetchedAlerts);
            setSafePoints(fetchedSafePoints);
            setIsUsingCachedData(false);
            setCachedAtTimestamp(null);

            // Persist to client-side IndexedDB for offline survival mode
            if (storageSupported) {
              cacheScenarioData({
                scenario_id: scenarioId,
                scenario_name: scenarioName || scenarioId,
                cached_at: new Date().toISOString(),
                alerts: fetchedAlerts,
                safe_points: fetchedSafePoints,
              }).catch(() => {});
            }
          }
        } catch (err) {
          if (!isCancelled) {
            // Fall back to offline cached data if live fetch fails
            if (storageSupported) {
              const cached = await getCachedScenarioData(scenarioId).catch(() => null);
              if (cached) {
                setAlerts(cached.alerts || []);
                setSafePoints(cached.safe_points || []);
                setIsUsingCachedData(true);
                setCachedAtTimestamp(cached.cached_at);
                setAlertsError(null);
              } else {
                const message = err instanceof Error ? err.message : 'Failed to retrieve emergency alerts.';
                setAlertsError(message);
              }
            } else {
              const message = err instanceof Error ? err.message : 'Failed to retrieve emergency alerts.';
              setAlertsError(message);
            }
          }
        } finally {
          if (!isCancelled) {
            setIsLoadingAlerts(false);
          }
        }
      } else {
        // When offline: read directly from local IndexedDB cache
        if (storageSupported) {
          setIsLoadingAlerts(true);
          try {
            const cached = await getCachedScenarioData(scenarioId);
            if (!isCancelled) {
              if (cached) {
                setAlerts(cached.alerts || []);
                setSafePoints(cached.safe_points || []);
                setIsUsingCachedData(true);
                setCachedAtTimestamp(cached.cached_at);
              } else {
                setAlerts([]);
                setSafePoints([]);
              }
              const cachedR = await getCachedRoute(scenarioId);
              if (cachedR && !activeRoute) {
                setActiveRoute(cachedR);
              }
            }
          } catch {
            // Ignore storage read error
          } finally {
            if (!isCancelled) {
              setIsLoadingAlerts(false);
            }
          }
        }
      }
    };

    loadEmergencyData();
    refreshOutbox();

    return () => {
      isCancelled = true;
    };
  }, [effectiveOnline, scenarioId, storageSupported]);

  // Plan safe evacuation route (online calculation with offline cache write)
  const handlePlanRoute = async () => {
    if (!scenarioId || isPlanningRoute) return;

    if (!effectiveOnline) {
      // Offline: attempt to retrieve previously cached route plan
      if (storageSupported) {
        const cached = await getCachedRoute(scenarioId).catch(() => null);
        if (cached) {
          setActiveRoute(cached);
          setRoutingError(null);
          return;
        }
      }
      setRoutingError('Cannot calculate new evacuation route while offline. Displaying cached corridors if available.');
      return;
    }

    setIsPlanningRoute(true);
    setRoutingError(null);

    try {
      const routeResponse = await requestEvacuationRoute(
        scenarioId,
        selectedOrigin,
        selectedDestination ? selectedDestination : undefined,
      );
      setActiveRoute(routeResponse);

      // Cache route plan in IndexedDB for offline survival mode
      if (storageSupported) {
        cacheRoute(routeResponse).catch(() => {});
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Evacuation route planning failed.';
      setRoutingError(message);
    } finally {
      setIsPlanningRoute(false);
    }
  };

  // Submit emergency SOS report to client outbox
  const handleSosSubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (!sosDescription.trim()) return;

    if (!storageSupported) {
      setFormFeedback('Error: Client storage is unavailable. Cannot queue SOS report.');
      return;
    }

    const clientUuid =
      typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function'
        ? crypto.randomUUID()
        : '00000000-0000-4000-8000-' + Math.random().toString(16).substring(2, 14);

    const newItem: QueuedIncidentItem = {
      incident_id: clientUuid,
      scenario_id: scenarioId,
      reported_at: new Date().toISOString(),
      zone_id: sosZone || selectedOrigin || 'ZONE-001',
      incident_type: sosType,
      urgency: sosUrgency,
      status: 'NOT_SENT',
      description: sosDescription.trim(),
      latitude: sosIncludeGps && sosLat ? parseFloat(sosLat) : null,
      longitude: sosIncludeGps && sosLon ? parseFloat(sosLon) : null,
    };

    try {
      await queueIncident(newItem);
      setSosDescription('');
      setFormFeedback(`SOS incident queued into offline outbox (Status: NOT_SENT).`);
      await refreshOutbox();

      // If online, immediately attempt background sync
      if (effectiveOnline) {
        setIsSyncingOutbox(true);
        try {
          const receipt = await syncOutbox(scenarioId);
          if (receipt) {
            setSyncFeedback(`Synchronized with emergency operations: ${receipt.status}.`);
          }
        } catch (syncErr) {
          setSyncFeedback(`Sync pending: ${syncErr instanceof Error ? syncErr.message : 'Network error'}. Retained in outbox.`);
        } finally {
          setIsSyncingOutbox(false);
          await refreshOutbox();
        }
      }
    } catch (queueErr) {
      setFormFeedback(`Failed to store SOS report: ${queueErr instanceof Error ? queueErr.message : 'Storage error'}`);
    }
  };

  // Manual Trigger: Drain Outbox
  const handleManualSync = async () => {
    if (!effectiveOnline) {
      setSyncFeedback('Cannot synchronize: Network connection is offline.');
      return;
    }
    setIsSyncingOutbox(true);
    setSyncFeedback(null);
    try {
      const receipt = await syncOutbox(scenarioId);
      if (receipt) {
        setSyncFeedback(
          `Sync successful: ${receipt.total_synced} newly synced, ${receipt.total_duplicates} previously acknowledged.`,
        );
      } else {
        setSyncFeedback('Outbox is up to date. No pending reports.');
      }
    } catch (err) {
      setSyncFeedback(`Sync failed: ${err instanceof Error ? err.message : 'Server error'}. Pending reports retained.`);
    } finally {
      setIsSyncingOutbox(false);
      await refreshOutbox();
    }
  };

  // Manual Trigger: Clear Acknowledged Items
  const handleClearAcknowledged = async () => {
    if (!storageSupported) return;
    try {
      await clearAcknowledgedIncidents(scenarioId);
      await refreshOutbox();
    } catch {
      // Ignore
    }
  };

  const handleClearChat = () => {
    setMessages([
      {
        id: 'welcome',
        role: 'assistant',
        text: 'Hello, I am CLIMAFORGE AI, your climate-risk and disaster-management assistant powered by Nugen AI (Qwen/Qwen2.5-0.5B-Instruct). I provide guidance on flood risks, safe evacuation corridors, and emergency preparedness. How can I assist you today?',
        source: 'SYSTEM',
      },
    ]);
    setError(null);
    setLastFailedQuestion(null);
  };

  const sendMessage = async (questionText: string) => {
    const trimmed = questionText.trim();
    if (!trimmed || isSending) return;

    if (!effectiveOnline) {
      setError('Chatbot assistant is currently unavailable offline. Please use the cached route planner or SOS outbox.');
      return;
    }

    const msgId = typeof crypto !== 'undefined' && crypto.randomUUID ? crypto.randomUUID() : String(Date.now());
    const userMessage: ChatMessage = {
      id: `u-${msgId}`,
      role: 'user',
      text: trimmed,
      source: 'MOCK',
    };
    const assistantMessageId = `a-${msgId}`;
    const initialAssistantMessage: ChatMessage = {
      id: assistantMessageId,
      role: 'assistant',
      text: '',
      source: 'NUGEN_AI',
    };

    setMessages((prev) => [...prev, userMessage, initialAssistantMessage]);
    setDraft('');
    setError(null);
    setLastFailedQuestion(null);
    setIsSending(true);

    const history: ChatHistoryItem[] = messages
      .filter((m) => m.role === 'assistant' || m.role === 'user')
      .map((m) => ({
        role: m.role,
        content: m.text,
      }));

    try {
      await streamChatbotMessage(
        scenarioId,
        trimmed,
        history,
        {
          onToken: (token) => {
            setMessages((prev) =>
              prev.map((m) =>
                m.id === assistantMessageId ? { ...m, text: m.text + token } : m
              )
            );
          },
          onDone: (meta) => {
            setMessages((prev) =>
              prev.map((m) =>
                m.id === assistantMessageId
                  ? {
                      ...m,
                      text: meta.fullText || m.text,
                      source: (meta.source as any) || 'NUGEN_AI',
                    }
                  : m
              )
            );
            setCurrentMode('grounded_llm');
          },
          onError: async (streamErr) => {
            console.warn('Streaming interrupted or failed, attempting non-streaming fallback:', streamErr);
            try {
              const fallbackResponse = await askGroundedChatbot(scenarioId, trimmed, history);
              setMessages((prev) =>
                prev.map((m) =>
                  m.id === assistantMessageId
                    ? { ...m, text: fallbackResponse.answer, source: fallbackResponse.source }
                    : m
                )
              );
              setCurrentMode(fallbackResponse.mode);
            } catch (fbErr) {
              const message = fbErr instanceof Error ? fbErr.message : 'Assistant request failed.';
              setError(message);
              setLastFailedQuestion(trimmed);
              setMessages((prev) => prev.filter((m) => m.id !== assistantMessageId));
            }
          },
        }
      );
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Assistant request failed.';
      setError(message);
      setLastFailedQuestion(trimmed);
      setMessages((prev) => prev.filter((m) => m.id !== assistantMessageId));
    } finally {
      setIsSending(false);
    }
  };

  const handleSubmit = (event: FormEvent) => {
    event.preventDefault();
    sendMessage(draft);
  };

  return (
    <div className="tab-pane m8-chat-pane">
      <div className="m8-page-heading">
        <div>
          <span className="m8-kicker">Milestone 7 Panic Phase, Offline Cache & Client SOS Outbox</span>
          <h2>Emergency Assistant, Alerts & Evacuation Routing</h2>
          <p>Citizen-accessible hazard warnings, deterministic shelter routing, and resilient offline SOS dispatch.</p>
        </div>
        <div className={`m8-service-status ${effectiveOnline ? 'online' : 'offline'}`}>
          {effectiveOnline ? <Wifi size={15} /> : <WifiOff size={15} />}
          <div>
            <strong>{effectiveOnline ? 'Online (Connected)' : 'Offline (Local Cache)'}</strong>
            <span>Scenario: {scenarioName || scenarioId}</span>
          </div>
        </div>
      </div>

      {/* Safety & Non-Authoritative Guidance Banner */}
      <div className="m8-safety-banner">
        <ShieldCheck size={18} />
        <div>
          <strong>Non-authoritative simulated emergency guidance</strong>
          <span>
            Simulated alerts and corridors are advisory models generated from Algorithm 1 & 5 outputs. Real-world
            evacuation commands require official civil defense verification.
          </span>
        </div>
      </div>

      {/* Milestone 7: Panic Phase Controls & Storage Status Header */}
      <div className="m7-panic-header">
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <button
            type="button"
            className={`m7-panic-toggle-btn ${isPanicMode ? 'active' : ''}`}
            onClick={() => setIsPanicMode(!isPanicMode)}
            aria-label="Toggle Panic Phase"
          >
            <AlertOctagon size={14} />
            {isPanicMode ? 'PANIC PHASE ACTIVE' : 'Enter Panic Phase (Offline SOS)'}
          </button>
          <span className="m6-simulation-pill">
            <Radio size={11} /> {effectiveOnline ? 'NETWORK ONLINE' : 'CELLULAR TOWERS DOWN (OFFLINE)'}
          </span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '0.72rem', color: 'var(--text-secondary)' }}>
          <HardDrive size={13} />
          <span>Offline Store: {storageSupported ? 'IndexedDB Active' : 'Storage Unavailable'}</span>
        </div>
      </div>

      {/* Offline Storage Warning Banner if IndexedDB Unavailable */}
      {!storageSupported && (
        <div className="m7-offline-warning-banner m7-storage-warning">
          <AlertTriangle size={16} style={{ flexShrink: 0 }} />
          <div>
            <strong>IndexedDB Unavailable: </strong>
            Client-side offline caching and persistent outbox queuing are disabled by browser privacy restrictions.
            Emergency SOS reports will not persist across reloads.
          </div>
        </div>
      )}

      {/* Prominent Offline Survival Mode Warning Banner */}
      {(!effectiveOnline || isPanicMode || isUsingCachedData) && (
        <div className="m7-offline-warning-banner">
          <AlertOctagon size={18} style={{ color: '#d97706', flexShrink: 0 }} />
          <div>
            <strong>OFFLINE SURVIVAL MODE: </strong>
            Live communications are interrupted. Emergency guidance and evacuation safe points are served from local device cache.
            {cachedAtTimestamp && <span> (Cached: {new Date(cachedAtTimestamp).toLocaleTimeString()}). </span>}
            Information may be outdated. Use the offline SOS outbox below to queue distress signals for automatic dispatch upon reconnection.
          </div>
        </div>
      )}

      {/* Milestone 7: Panic Phase & Client SOS Outbox Suite */}
      <div className="m7-panic-suite">
        <div className="m7-panic-grid">
          {/* Emergency SOS Distress Form */}
          <section className="m7-sos-card" aria-label="Emergency SOS report form">
            <h3>
              <Flame size={16} />
              Emergency SOS Distress Dispatch
            </h3>
            <p style={{ fontSize: '0.72rem', color: 'var(--text-secondary)', margin: 0 }}>
              Queue life-safety distress reports without network connectivity. Automatically transmitted upon reconnect.
            </p>

            <form onSubmit={handleSosSubmit} className="m7-sos-form">
              <div className="m7-form-row">
                <div className="m7-form-group">
                  <label htmlFor="sos-type">Incident Type</label>
                  <select
                    id="sos-type"
                    className="m7-form-select"
                    value={sosType}
                    onChange={(e) => setSosType(e.target.value)}
                  >
                    <option value="RISING_WATER">RISING_WATER (Water Intrusion)</option>
                    <option value="MEDICAL_EMERGENCY">MEDICAL_EMERGENCY (Trauma / Critical Care)</option>
                    <option value="STRANDED_PERSONS">STRANDED_PERSONS (Trapped Citizens)</option>
                    <option value="ROAD_BLOCKED">IMPASSABLE_CORRIDOR (Obstructed Transit)</option>
                  </select>
                </div>
                <div className="m7-form-group">
                  <label htmlFor="sos-urgency">Urgency Priority</label>
                  <select
                    id="sos-urgency"
                    className="m7-form-select"
                    value={sosUrgency}
                    onChange={(e) => setSosUrgency(e.target.value as 'CRITICAL' | 'HIGH' | 'MEDIUM')}
                  >
                    <option value="CRITICAL">CRITICAL (Immediate Life Threat)</option>
                    <option value="HIGH">HIGH (Severe Danger)</option>
                    <option value="MEDIUM">MEDIUM (Caution / Assistance)</option>
                  </select>
                </div>
              </div>

              <div className="m7-form-row">
                <div className="m7-form-group">
                  <label htmlFor="sos-zone">Location Zone</label>
                  <select
                    id="sos-zone"
                    className="m7-form-select"
                    value={sosZone}
                    onChange={(e) => setSosZone(e.target.value)}
                  >
                    <option value="ZONE-001">ZONE-001: Riverside Industrial District</option>
                    <option value="ZONE-002">ZONE-002: Central Ward & Commercial Core</option>
                    <option value="ZONE-003">ZONE-003: Valley Residential Heights</option>
                    <option value="ZONE-004">ZONE-004: Harbor & Estuary Basin</option>
                  </select>
                </div>
                <div className="m7-form-group" style={{ justifyContent: 'center' }}>
                  <label style={{ display: 'flex', alignItems: 'center', gap: '6px', cursor: 'pointer', marginTop: '16px' }}>
                    <input
                      type="checkbox"
                      checked={sosIncludeGps}
                      onChange={(e) => setSosIncludeGps(e.target.checked)}
                    />
                    <span>Attach GPS (Optional)</span>
                  </label>
                </div>
              </div>

              {sosIncludeGps && (
                <div className="m7-form-row">
                  <div className="m7-form-group">
                    <label htmlFor="sos-lat">Latitude</label>
                    <input
                      id="sos-lat"
                      type="number"
                      step="any"
                      placeholder="e.g. 40.7128"
                      className="m7-form-input"
                      value={sosLat}
                      onChange={(e) => setSosLat(e.target.value)}
                    />
                  </div>
                  <div className="m7-form-group">
                    <label htmlFor="sos-lon">Longitude</label>
                    <input
                      id="sos-lon"
                      type="number"
                      step="any"
                      placeholder="e.g. -74.0060"
                      className="m7-form-input"
                      value={sosLon}
                      onChange={(e) => setSosLon(e.target.value)}
                    />
                  </div>
                </div>
              )}

              <div className="m7-form-group">
                <label htmlFor="sos-desc">Distress Situation / Description</label>
                <textarea
                  id="sos-desc"
                  className="m7-form-textarea"
                  placeholder="Describe trapped persons, water depth, structure status, or urgent medical needs..."
                  value={sosDescription}
                  onChange={(e) => setSosDescription(e.target.value)}
                  required
                />
              </div>

              <button type="submit" className="m7-sos-submit-btn">
                <Send size={13} />
                Record Emergency SOS (Queue Outbox)
              </button>

              {formFeedback && (
                <div style={{ fontSize: '0.72rem', color: '#16a34a', fontWeight: 600 }}>
                  {formFeedback}
                </div>
              )}
            </form>
          </section>

          {/* Client SOS Outbox Section */}
          <section className="m7-outbox-card" aria-label="Client SOS outbox queue">
            <div className="m7-outbox-header">
              <h3>
                <HardDrive size={16} />
                Client SOS Outbox Queue ({outboxItems.length})
              </h3>
              <div className="m7-outbox-actions">
                <button
                  type="button"
                  className="m7-sync-btn"
                  onClick={handleManualSync}
                  disabled={!effectiveOnline || isSyncingOutbox || outboxItems.length === 0}
                >
                  <RefreshCw size={11} className={isSyncingOutbox ? 'spin' : ''} />
                  {isSyncingOutbox ? 'Syncing...' : 'Sync Outbox'}
                </button>
                <button
                  type="button"
                  className="m7-clear-btn"
                  onClick={handleClearAcknowledged}
                  title="Clear acknowledged records"
                >
                  <Trash2 size={11} />
                  Clear Acknowledged
                </button>
              </div>
            </div>

            {syncFeedback && (
              <div className={`m7-sync-msg ${syncFeedback.includes('failed') || syncFeedback.includes('error') ? 'error' : ''}`}>
                {syncFeedback}
              </div>
            )}

            {outboxItems.length === 0 ? (
              <div style={{ padding: '16px', textAlign: 'center', fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
                Outbox is empty. No queued emergency reports.
              </div>
            ) : (
              <div className="m7-outbox-list">
                {outboxItems.map((item) => (
                  <div key={item.incident_id} className="m7-outbox-item">
                    <div className="m7-outbox-item-top">
                      <span style={{ fontWeight: 700, color: 'var(--text-primary)' }}>
                        {item.incident_type} ({item.urgency})
                      </span>
                      <span className={`m7-status-pill ${item.status === 'NOT_SENT' ? 'not-sent' : 'acknowledged'}`}>
                        {item.status === 'NOT_SENT' ? <Clock size={10} /> : <CheckCircle2 size={10} />}
                        {item.status}
                      </span>
                    </div>
                    <div style={{ color: 'var(--text-secondary)' }}>
                      <strong>Zone:</strong> {item.zone_id} | <strong>Logged:</strong> {new Date(item.reported_at).toLocaleTimeString()}
                      {item.latitude && item.longitude && (
                        <span> | <strong>GPS:</strong> {item.latitude.toFixed(4)}, {item.longitude.toFixed(4)}</span>
                      )}
                    </div>
                    <div style={{ color: 'var(--text-primary)', marginTop: '2px' }}>
                      {item.description}
                    </div>
                    <div style={{ fontSize: '0.62rem', color: 'var(--text-secondary)', fontFamily: 'var(--font-mono)' }}>
                      UUID: {item.incident_id}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </section>
        </div>
      </div>

      {/* Milestone 6: Pre-Calamity Citizen Alerts */}
      <div className="m6-emergency-suite">
        <section className="m6-alerts-section" aria-label="Pre-calamity citizen alerts">
          <div className="m6-section-title-row">
            <h3>
              <ShieldAlert size={17} style={{ color: '#dc2626' }} />
              Pre-Calamity Citizen Alerts {isUsingCachedData && '(Offline Cached)'}
            </h3>
            <span className="m6-simulation-pill">
              <Info size={11} /> SIMULATED ALERTS ONLY
            </span>
          </div>

          {isLoadingAlerts ? (
            <div className="m8-loading" style={{ padding: '8px' }}><span /><span /><span /></div>
          ) : alertsError ? (
            <div className="m8-advisory-note">
              <AlertTriangle size={15} />
              <span>{alertsError}</span>
            </div>
          ) : alerts.length === 0 ? (
            <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
              No active flood alerts for this scenario. Catchment conditions are within baseline thresholds.
            </div>
          ) : (
            <div className="m6-alerts-grid">
              {alerts.map((alert) => {
                const sevClass = alert.severity.toLowerCase();
                return (
                  <div key={alert.alert_id} className={`m6-alert-card ${sevClass}`}>
                    <div className="m6-alert-card-header">
                      <span className={`m6-severity-badge ${sevClass}`}>
                        {alert.severity === 'CRITICAL' && <Flame size={11} />}
                        {alert.severity}
                      </span>
                      <span className="m6-alert-score">{alert.risk_score.toFixed(1)}/100</span>
                    </div>
                    <div className="m6-alert-headline">{alert.headline}</div>
                    <div className="m6-alert-cause">
                      <strong>Dominant driver:</strong> {alert.dominant_cause}
                    </div>
                    <div className="m6-alert-action">{alert.action_recommendation}</div>
                    <div className="m6-alert-disclaimer">{alert.disclaimer}</div>
                  </div>
                );
              })}
            </div>
          )}
        </section>

        {/* Milestone 6: Safe Evacuation Route Planner */}
        <section className="m6-routing-panel" aria-label="Safe evacuation route planner">
          <div className="m6-section-title-row">
            <h3>
              <Navigation size={17} style={{ color: '#16a34a' }} />
              Safe Evacuation Route Planner {isUsingCachedData && '(Offline Cached)'}
            </h3>
            <span className="m6-simulation-pill">
              <CheckCircle2 size={11} /> DIJKSTRA HAZARD-AVOIDANCE
            </span>
          </div>

          <div className="m6-routing-controls">
            <div className="m6-field-group">
              <label htmlFor="evac-origin">Origin Hazard Zone</label>
              <select
                id="evac-origin"
                className="m6-field-select"
                value={selectedOrigin}
                onChange={(e) => setSelectedOrigin(e.target.value)}
                disabled={isPlanningRoute}
              >
                <option value="ZONE-001">ZONE-001: Riverside Industrial District (Elev: 4.5m)</option>
                <option value="ZONE-002">ZONE-002: Central Ward & Commercial Core (Elev: 9.2m)</option>
                <option value="ZONE-003">ZONE-003: Valley Residential Heights (Elev: 18.0m)</option>
                <option value="ZONE-004">ZONE-004: Harbor & Estuary Basin (Elev: 2.1m)</option>
              </select>
            </div>

            <div className="m6-field-group">
              <label htmlFor="evac-destination">Designated Safe Refuge</label>
              <select
                id="evac-destination"
                className="m6-field-select"
                value={selectedDestination}
                onChange={(e) => setSelectedDestination(e.target.value)}
                disabled={isPlanningRoute}
              >
                {[
                  <option key="auto" value="">Auto-Select Nearest Safe Shelter</option>,
                  ...safePoints.map((sp) => (
                    <option key={sp.safe_point_id} value={sp.safe_point_id}>
                      {sp.name} (Cap: {sp.capacity_persons}, Elev: {sp.elevation_m}m)
                    </option>
                  )),
                ]}
              </select>
            </div>

            <button
              type="button"
              className="m6-route-btn"
              onClick={handlePlanRoute}
              disabled={isPlanningRoute}
            >
              <Compass size={14} />
              {isPlanningRoute ? 'Computing Safe Path...' : 'Find Safe Route'}
            </button>
          </div>

          {routingError && (
            <div className="m8-advisory-note" style={{ marginTop: '8px' }}>
              <AlertTriangle size={15} />
              <span>{routingError}</span>
            </div>
          )}

          {/* Route Planning Result Display */}
          {activeRoute && (
            <div className={`m6-route-card ${activeRoute.status === 'CONFIRMED_SAFE' ? 'safe' : 'blocked'}`}>
              <div className="m6-route-header">
                <span className={`m6-route-status-pill ${activeRoute.status === 'CONFIRMED_SAFE' ? 'safe' : 'blocked'}`}>
                  {activeRoute.status === 'CONFIRMED_SAFE' ? (
                    <>
                      <CheckCircle2 size={13} />
                      CONFIRMED SAFE (SIMULATED)
                    </>
                  ) : (
                    <>
                      <AlertTriangle size={13} />
                      BLOCKED / IMPASSABLE (NO ROUTE)
                    </>
                  )}
                </span>
                {activeRoute.status === 'CONFIRMED_SAFE' ? (
                  <div className="m6-route-metrics">
                    <span>Destination: <strong>{activeRoute.destination_safe_point_name}</strong></span>
                    <span>Distance: <strong>{activeRoute.distance_km != null ? `${activeRoute.distance_km} km` : 'Unavailable'}</strong></span>
                    <span>Transit: <strong>{activeRoute.estimated_transit_minutes != null ? `~${activeRoute.estimated_transit_minutes} mins` : 'Unavailable'}</strong></span>
                  </div>
                ) : (
                  <div className="m6-route-metrics m6-route-metrics-blocked">
                    <span>Distance: <strong>Unavailable (Route Blocked)</strong></span>
                    <span>Transit: <strong>Unavailable (Shelter in Place)</strong></span>
                  </div>
                )}
                <span className="m6-simulation-pill">
                  is_live_confirmed: false
                </span>
              </div>

              {/* Hazard Avoidance Notification Banner */}
              {activeRoute.avoided_hazard_nodes && activeRoute.avoided_hazard_nodes.length > 0 && (
                <div className="m6-avoidance-banner">
                  <ShieldAlert size={16} style={{ flexShrink: 0 }} />
                  <div>
                    <strong>Hazard Bypass Active: </strong>
                    Avoided {activeRoute.avoided_hazard_nodes.length} flooded/failing infrastructure asset
                    {activeRoute.avoided_hazard_nodes.length > 1 ? 's' : ''}:{' '}
                    <em>{activeRoute.avoided_hazard_nodes.join(', ')}</em>. Route diverted to safe elevated bypass corridors.
                  </div>
                </div>
              )}

              {/* Blocked Route Instructions */}
              {activeRoute.status === 'BLOCKED' && (
                <div className="m6-blocked-instructions">
                  <strong>{activeRoute.error_message || 'All candidate transit corridors are blocked by active flood waters.'}</strong>
                  <div className="m6-step-list" style={{ marginTop: '6px' }}>
                    {activeRoute.step_by_step_instructions.map((step, idx) => (
                      <div key={idx} className="m6-step-item">
                        <span className="m6-step-num" style={{ background: '#fee2e2', color: '#991b1b' }}>!</span>
                        <span>{step}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Safe Waypoints and Instructions */}
              {activeRoute.status === 'CONFIRMED_SAFE' && (
                <div>
                  <strong style={{ fontSize: '0.75rem', color: 'var(--text-primary)' }}>
                    Turn-by-Turn Safe Evacuation Corridor:
                  </strong>
                  <div className="m6-step-list">
                    {activeRoute.step_by_step_instructions.map((step, idx) => (
                      <div key={idx} className="m6-step-item">
                        <span className="m6-step-num">{idx + 1}</span>
                        <span>{step}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              <div className="m6-alert-disclaimer" style={{ marginTop: '8px' }}>
                {activeRoute.disclaimer}
              </div>
            </div>
          )}
        </section>
      </div>

      <div className="m8-chat-layout">
        <aside className="dashboard-card m8-chat-context">
          <div className="m8-card-header">
            <span className="m8-panel-label">Conversation context</span>
            <h3>Supported workflow</h3>
          </div>
          <div className="m8-context-list">
            <div><span>01</span><strong>Review scenario evidence</strong></div>
            <div><span>02</span><strong>Inspect hazard alerts & bypass corridors</strong></div>
            <div><span>03</span><strong>Access offline panic guidance & outbox</strong></div>
            <div><span>04</span><strong>Ask grounded explanations & rationale</strong></div>
          </div>
          <div className="m8-prompt-chips">
            {suggestedPrompts.map((prompt) => (
              <button
                key={prompt}
                type="button"
                className="m8-chip"
                onClick={() => sendMessage(prompt)}
                disabled={isSending || !effectiveOnline}
              >
                {prompt}
              </button>
            ))}
          </div>
        </aside>

        <section className="dashboard-card m8-chat-panel">
          <div className="m8-chat-panel-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '10px 14px', borderBottom: '1px solid var(--border-subtle, #334155)', background: 'var(--surface-subtle, rgba(30, 41, 59, 0.5))' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <strong style={{ fontSize: '0.85rem', color: 'var(--text-primary)' }}>CLIMAFORGE AI Assistant</strong>
              <span className="m8-source-pill" style={{ background: '#0284c7', color: '#ffffff', fontSize: '0.65rem' }}>
                NUGEN AI • Qwen/Qwen2.5-0.5B-Instruct
              </span>
            </div>
            <button
              type="button"
              className="m7-clear-btn"
              onClick={handleClearChat}
              disabled={isSending}
              title="Reset conversation"
              style={{ fontSize: '0.7rem', padding: '3px 8px' }}
            >
              <Trash2 size={11} />
              Clear Conversation
            </button>
          </div>

          <div className="m8-chat-messages">
            {messages.map((m) => (
              <article key={m.id} className={`m8-message ${m.role}`}>
                <div className="m8-message-meta">
                  <span>{m.role === 'assistant' ? 'CLIMAFORGE AI' : 'Operator'}</span>
                  {m.role === 'assistant' && (
                    <span className="m8-source-pill">
                      {m.source === 'NUGEN_AI'
                        ? 'Nugen AI (Qwen)'
                        : m.source === 'LLM'
                        ? 'Grounded LLM'
                        : m.source === 'DETERMINISTIC_FALLBACK'
                        ? 'Deterministic Engine'
                        : m.source === 'SYSTEM'
                        ? 'System Notice'
                        : 'Mock Advisory'}
                    </span>
                  )}
                </div>
                <div className="m8-message-body">
                  {m.text || (isSending && m.role === 'assistant' ? 'Generating answer...' : '')}
                </div>
              </article>
            ))}
            {isSending && (
              <div className="m8-loading">
                <span /><span /><span />
              </div>
            )}
          </div>

          {error && (
            <div className="m8-advisory-note" style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '8px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                <AlertTriangle size={15} />
                <span>{error}</span>
              </div>
              {lastFailedQuestion && (
                <button
                  type="button"
                  className="btn btn-primary"
                  onClick={() => {
                    setError(null);
                    sendMessage(lastFailedQuestion);
                  }}
                  style={{ padding: '3px 10px', fontSize: '0.72rem' }}
                >
                  <RefreshCw size={11} /> Retry Question
                </button>
              )}
            </div>
          )}

          <form className="m8-chat-input" onSubmit={handleSubmit}>
            <input
              type="text"
              placeholder={effectiveOnline ? "Ask a grounded scenario question..." : "Assistant is offline. Review cached routes or submit offline SOS above."}
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              disabled={isSending || !effectiveOnline}
            />
            <button
              type="submit"
              className="btn btn-primary"
              disabled={isSending || !draft.trim() || !effectiveOnline}
              title={effectiveOnline ? "Send grounded question" : "Offline mode active"}
            >
              <Send size={15} />
            </button>
          </form>
        </section>
      </div>
    </div>
  );
};
