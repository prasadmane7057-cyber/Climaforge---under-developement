import React, { useState } from 'react';
import {
  RefreshCw,
  Filter,
  Server,
  User,
} from 'lucide-react';
import type { AuditEvent } from '../types/api';

interface AuditLogTabProps {
  auditLogs: AuditEvent[];
  isLoading: boolean;
  onRefresh: () => void;
}

export const AuditLogTab: React.FC<AuditLogTabProps> = ({
  auditLogs,
  isLoading,
  onRefresh,
}) => {
  const [filterSource, setFilterSource] = useState<'ALL' | 'BACKEND' | 'FRONTEND'>('ALL');

  const filteredLogs = auditLogs.filter((log) => {
    if (filterSource === 'ALL') return true;
    return log.source === filterSource;
  });

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
      {/* Header Controls */}
      <div className="control-bar-card">
        <div className="audit-filter-group">
          <Filter size={16} className="text-cyan" />
          <span className="control-label">Source Filter:</span>
          <div className="btn-group-toggle">
            <button
              type="button"
              className={`toggle-btn ${filterSource === 'ALL' ? 'active' : ''}`}
              onClick={() => setFilterSource('ALL')}
            >
              All Events ({auditLogs.length})
            </button>
            <button
              type="button"
              className={`toggle-btn ${filterSource === 'BACKEND' ? 'active' : ''}`}
              onClick={() => setFilterSource('BACKEND')}
            >
              Backend ({auditLogs.filter((l) => l.source === 'BACKEND').length})
            </button>
            <button
              type="button"
              className={`toggle-btn ${filterSource === 'FRONTEND' ? 'active' : ''}`}
              onClick={() => setFilterSource('FRONTEND')}
            >
              Frontend UI ({auditLogs.filter((l) => l.source === 'FRONTEND').length})
            </button>
          </div>
        </div>

        <button
          type="button"
          className="btn btn-refresh"
          onClick={onRefresh}
          disabled={isLoading}
        >
          <RefreshCw size={15} className={isLoading ? 'spin-animation' : ''} />
          <span>{isLoading ? 'Refreshing...' : 'Refresh Audit Trail'}</span>
        </button>
      </div>

      {/* Audit Log Table */}
      <div className="dashboard-card">
        <div className="card-header-row">
          <div>
            <h3 className="card-heading-sm">System Operational & UI Session Audit Trail</h3>
            <p className="card-subheading">
              Authentic immutable record of backend lifecycle events and client operator actions
            </p>
          </div>
          <span className="badge-provenance">VERIFIED SESSION LOGS ONLY</span>
        </div>

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
              {filteredLogs.length === 0 && (
                <tr>
                  <td colSpan={6} className="text-center text-muted py-8">
                    No matching audit records found.
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
