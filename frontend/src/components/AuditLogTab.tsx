import React, { useState } from 'react';
import {
  RefreshCw,
  Filter,
  Server,
  User,
  Activity,
  AlertCircle,
  Clock3,
} from 'lucide-react';
import type { AuditEvent } from '../types/api';

interface AuditLogTabProps {
  auditLogs: AuditEvent[];
  isLoading: boolean;
  error: string | null;
  onRefresh: () => void;
}

export const AuditLogTab: React.FC<AuditLogTabProps> = ({
  auditLogs,
  isLoading,
  error,
  onRefresh,
}) => {
  const [filterSource, setFilterSource] = useState<'ALL' | 'BACKEND' | 'FRONTEND'>('ALL');

  const filteredLogs = auditLogs.filter((log) => {
    if (filterSource === 'ALL') return true;
    return log.source === filterSource;
  });

  const backendCount = auditLogs.filter((log) => log.source === 'BACKEND').length;
  const frontendCount = auditLogs.filter((log) => log.source === 'FRONTEND').length;
  const eventTypes = new Set(auditLogs.map((log) => log.event_type)).size;
  const timestampLabel = auditLogs.length > 0
    ? new Date(auditLogs[0].timestamp).toLocaleString()
    : 'No events recorded';

  const getEventTypeBadgeClass = (type: string) => {
    switch (type) {
      case 'SYSTEM_BOOT':
        return 'badge-boot';
      case 'HEALTH_CHECK':
        return 'badge-health';
      case 'SCENARIO_LOADED':
        return 'badge-scenario';
      case 'USER_NAVIGATION':
        return 'badge-nav';
      default:
        return 'badge-generic';
    }
  };

  return (
    <div className="tab-pane audit-pane">
      <div className="m8-page-heading">
        <div>
          <span className="m8-kicker">Recorded session activity</span>
          <h2>Audit Log</h2>
          <p>Actual backend lifecycle and operator events recorded during this application session.</p>
        </div>
        <button
          type="button"
          className="m8-refresh-button"
          onClick={onRefresh}
          disabled={isLoading}
        >
          <RefreshCw size={15} className={isLoading ? 'spin-animation' : ''} />
          <span>{isLoading ? 'Refreshing' : 'Refresh log'}</span>
        </button>
      </div>

      {error && (
        <div className="m8-error-banner">
          <AlertCircle size={17} />
          <div><strong>Audit trail unavailable</strong><span>{error}. Previously loaded records remain visible.</span></div>
        </div>
      )}

      <div className="m8-audit-metrics">
        <article className="dashboard-card"><Activity size={16} /><div><span>Total events</span><strong>{auditLogs.length}</strong></div></article>
        <article className="dashboard-card"><Server size={16} /><div><span>Backend</span><strong>{backendCount}</strong></div></article>
        <article className="dashboard-card"><User size={16} /><div><span>Frontend</span><strong>{frontendCount}</strong></div></article>
        <article className="dashboard-card"><Clock3 size={16} /><div><span>Event types</span><strong>{eventTypes}</strong></div></article>
      </div>

      <div className="control-bar-card m8-audit-controls">
        <div className="m8-audit-filter">
          <Filter size={16} />
          <span>Source</span>
          <div className="btn-group-toggle">
            {(['ALL', 'BACKEND', 'FRONTEND'] as const).map((source) => (
              <button
                key={source}
                type="button"
                className={`toggle-btn ${filterSource === source ? 'active' : ''}`}
                onClick={() => setFilterSource(source)}
              >
                {source === 'ALL' ? `All (${auditLogs.length})` : source === 'BACKEND' ? `Backend (${backendCount})` : `Frontend (${frontendCount})`}
              </button>
            ))}
          </div>
        </div>
        <span className="m8-last-event">Latest: <strong>{timestampLabel}</strong></span>
      </div>

      <div className="dashboard-card m8-audit-card">
        <div className="table-responsive">
          <table className="data-table">
            <thead>
              <tr>
                <th>Event ID</th>
                <th>Timestamp (UTC)</th>
                <th>Source</th>
                <th>Category</th>
                <th>Event Description</th>
                <th>Context Metadata</th>
              </tr>
            </thead>
            <tbody>
              {isLoading && auditLogs.length === 0 && (
                <tr>
                  <td colSpan={6} className="m8-audit-state">
                    <span className="m8-loading-dots"><span /><span /><span /></span>
                    Loading recorded audit events...
                  </td>
                </tr>
              )}
              {filteredLogs.map((log) => (
                <tr key={log.event_id}>
                  <td>
                    <code className="event-id-code">{log.event_id}</code>
                  </td>
                  <td className="text-muted text-mono">
                    {new Date(log.timestamp).toISOString().replace('T', ' ').slice(0, 19)}
                  </td>
                  <td>
                    <span
                      className={`source-badge ${
                        log.source === 'BACKEND' ? 'source-backend' : 'source-frontend'
                      }`}
                    >
                      {log.source === 'BACKEND' ? <Server size={12} /> : <User size={12} />}
                      {log.source}
                    </span>
                  </td>
                  <td>
                    <span className={`event-type-pill ${getEventTypeBadgeClass(log.event_type)}`}>
                      {log.event_type}
                    </span>
                  </td>
                  <td className="cell-primary font-medium">{log.description}</td>
                  <td>
                    {log.details && Object.keys(log.details).length > 0 ? (
                      <div className="metadata-tag-list">
                        {Object.entries(log.details).map(([k, v]) => (
                          <span key={k} className="meta-tag">
                            {k}: <strong>{v}</strong>
                          </span>
                        ))}
                      </div>
                    ) : (
                      <span className="text-dim">—</span>
                    )}
                  </td>
                </tr>
              ))}
              {!isLoading && filteredLogs.length === 0 && (
                <tr>
                  <td colSpan={6} className="text-center text-muted py-8">
                    {auditLogs.length === 0 ? 'No audit events have been recorded.' : 'No matching audit records found for this source.'}
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
