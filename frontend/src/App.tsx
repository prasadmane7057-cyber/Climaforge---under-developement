import React, { useState, useEffect, useCallback } from 'react';
import {
  ShieldAlert,
  Server,
  RefreshCw,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  Layers,
  Database,
  ArrowRight,
  Clock,
  Terminal,
} from 'lucide-react';
import { checkBackendHealth, getApiBaseUrl, type HealthCheckResult } from './services/api';
import './App.css';

export const App: React.FC = () => {
  const [result, setResult] = useState<HealthCheckResult | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [lastChecked, setLastChecked] = useState<Date | null>(null);

  const handleCheckConnection = useCallback(async () => {
    setIsLoading(true);
    const res = await checkBackendHealth();
    setResult(res);
    setIsLoading(false);
    setLastChecked(new Date());
  }, []);

  useEffect(() => {
    handleCheckConnection();
  }, [handleCheckConnection]);

  const apiUrl = getApiBaseUrl();

  return (
    <div className="app-container">
      {/* Top Disclaimer Banner */}
      <div className="top-banner">
        <span className="banner-badge">PROTOTYPE NOTICE</span>
        <span className="banner-text">
          SYNTHETIC / ILLUSTRATIVE DATA ONLY — Milestone 0 Foundation Build
        </span>
      </div>

      {/* Header */}
      <header className="header">
        <div className="header-brand">
          <div className="brand-icon-wrapper">
            <ShieldAlert className="brand-icon" size={28} />
          </div>
          <div>
            <div className="brand-title-row">
              <h1 className="brand-title">CLIMAFORGE</h1>
              <span className="version-pill">M0 — Foundation</span>
            </div>
            <p className="brand-subtitle">
              Climate-Flood Decision Support Core & Autonomous Operations Platform
            </p>
          </div>
        </div>

        <div className="header-meta">
          <div className="meta-pill">
            <span className="meta-label">ENVIRONMENT</span>
            <span className="meta-value">Development</span>
          </div>
          <div
            className={`meta-pill status-pill ${
              isLoading ? 'status-checking' : result?.success ? 'status-online' : 'status-offline'
            }`}
          >
            <span className="status-dot"></span>
            <span className="meta-value">
              {isLoading ? 'Checking' : result?.success ? 'Backend Online' : 'Backend Disconnected'}
            </span>
          </div>
        </div>
      </header>

      {/* Main Content Grid */}
      <main className="main-content">
        {/* Connection Diagnostics Card */}
        <section className="card card-connection">
          <div className="card-header">
            <div className="card-title-group">
              <Server className="section-icon text-cyan" size={22} />
              <div>
                <h2 className="card-title">Backend Connection & Diagnostics</h2>
                <p className="card-description">
                  Verifying REST communication with FastAPI core on port 8000
                </p>
              </div>
            </div>

            <button
              onClick={handleCheckConnection}
              disabled={isLoading}
              className={`btn btn-refresh ${isLoading ? 'btn-loading' : ''}`}
              title="Query GET /health endpoint"
            >
              <RefreshCw size={16} className={isLoading ? 'spin-animation' : ''} />
              <span>{isLoading ? 'Checking...' : 'Check Connection'}</span>
            </button>
          </div>

          <div className="connection-target-row">
            <div className="target-item">
              <span className="target-label">Target API URL:</span>
              <code className="target-code">{apiUrl}/health</code>
            </div>
            {lastChecked && (
              <div className="target-item">
                <Clock size={14} className="text-muted" />
                <span className="target-label">Last Ping:</span>
                <span className="target-val">{lastChecked.toLocaleTimeString()}</span>
              </div>
            )}
            {result?.latencyMs !== undefined && (
              <div className="target-item">
                <span className="target-label">Latency:</span>
                <span className={`target-val ${result.success ? 'text-green' : 'text-amber'}`}>
                  {result.latencyMs} ms
                </span>
              </div>
            )}
          </div>

          {/* Loading State */}
          {isLoading && !result && (
            <div className="state-panel panel-loading">
              <div className="spinner"></div>
              <p className="state-title">Pinging backend diagnostic endpoint...</p>
              <p className="state-subtitle">Establishing HTTP link with {apiUrl}</p>
            </div>
          )}

          {/* Success State */}
          {!isLoading && result?.success && result.data && (
            <div className="state-panel panel-success">
              <div className="state-header">
                <div className="state-badge badge-success">
                  <CheckCircle2 size={18} />
                  <span>HEALTHY (HTTP 200)</span>
                </div>
                <span className="server-timestamp">
                  Server UTC: {new Date(result.data.timestamp).toISOString()}
                </span>
              </div>

              <div className="subsystems-grid">
                {Object.entries(result.data.subsystems).map(([subsystem, status]) => (
                  <div key={subsystem} className="subsystem-card">
                    <div className="subsystem-header">
                      <span className="subsystem-key">{subsystem.replace(/_/g, ' ')}</span>
                      <span className="subsystem-status-badge">{status}</span>
                    </div>
                  </div>
                ))}
              </div>

              <div className="diagnostic-details-box">
                <div className="diag-row">
                  <span className="diag-k">Service Name:</span>
                  <span className="diag-v">{result.data.app_name}</span>
                </div>
                <div className="diag-row">
                  <span className="diag-k">API Version:</span>
                  <span className="diag-v">{result.data.version}</span>
                </div>
                <div className="diag-row">
                  <span className="diag-k">Advisory Layer:</span>
                  <span className="diag-v text-cyan">
                    Nugen Mock Provider (Advisory only — strictly non-authoritative)
                  </span>
                </div>
              </div>
            </div>
          )}

          {/* Error State */}
          {!isLoading && result && !result.success && (
            <div className="state-panel panel-error">
              <div className="state-header">
                <div className="state-badge badge-error">
                  <XCircle size={18} />
                  <span>CONNECTION FAILED</span>
                </div>
                <span className="error-title-text">{result.errorMessage}</span>
              </div>

              <div className="error-explanation">
                <AlertTriangle size={18} className="text-amber flex-shrink-0" />
                <p>{result.errorDetails}</p>
              </div>

              <div className="troubleshooting-guide">
                <span className="guide-title">
                  <Terminal size={14} /> Quick Resolution for Windows PowerShell:
                </span>
                <p className="guide-instruction">
                  Ensure the backend virtual environment is active and run uvicorn with --app-dir:
                </p>
                <div className="code-block-wrapper">
                  <code>
                    cd &quot;C:\Users\Aditya\Desktop\Climaforge Workspace&quot;
                    <br />
                    .\backend\.venv\Scripts\python -m uvicorn --app-dir backend app.main:app --host 0.0.0.0 --port 8000 --reload
                  </code>
                </div>
              </div>
            </div>
          )}
        </section>

        {/* Milestone 0 Architecture & Contracts Overview */}
        <section className="architecture-grid">
          {/* Contracts Card */}
          <div className="card">
            <div className="card-title-group">
              <Database className="section-icon text-indigo" size={20} />
              <h3 className="card-title">Provisional Domain Contracts</h3>
            </div>
            <p className="card-description">
              Typed Pydantic contracts validated in Milestone 0 backend:
            </p>

            <ul className="contract-list">
              <li className="contract-item">
                <div className="contract-item-head">
                  <span className="contract-name">ZoneInput</span>
                  <span className="contract-tag">Alg 0-1</span>
                </div>
                <p className="contract-desc">
                  Zone telemetry, area, elevation, rainfall (mm), drainage capacity, and soil
                  saturation ratio.
                </p>
              </li>

              <li className="contract-item">
                <div className="contract-item-head">
                  <span className="contract-name">GraphNode</span>
                  <span className="contract-tag">Alg 6-9</span>
                </div>
                <p className="contract-desc">
                  Critical infrastructure elements: substations, hospitals, water treatment,
                  operational ratio, flood failure thresholds.
                </p>
              </li>

              <li className="contract-item">
                <div className="contract-item-head">
                  <span className="contract-name">Intervention</span>
                  <span className="contract-tag">Alg 10-12</span>
                </div>
                <p className="contract-desc">
                  Candidate mitigation actions: barriers, pumps, diversions, required resources, lead
                  times, and risk attenuation.
                </p>
              </li>

              <li className="contract-item">
                <div className="contract-item-head">
                  <span className="contract-name">DecisionCard</span>
                  <span className="contract-tag">Alg 13</span>
                </div>
                <p className="contract-desc">
                  Authoritative incident commander directive: prioritized action IDs, costs,
                  projected impact, and advisory status.
                </p>
              </li>

              <li className="contract-item">
                <div className="contract-item-head">
                  <span className="contract-name">IncidentRecord</span>
                  <span className="contract-tag">Field & SOS</span>
                </div>
                <p className="contract-desc">
                  Field incident reports with urgency levels and offline cache status (NOT_SENT until
                  server acknowledgement).
                </p>
              </li>
            </ul>
          </div>

          {/* System Rules & Roadmap Card */}
          <div className="card">
            <div className="card-title-group">
              <Layers className="section-icon text-emerald" size={20} />
              <h3 className="card-title">Engineering Rules & Next Milestones</h3>
            </div>
            <p className="card-description">
              Foundational architecture boundaries established for the prototype:
            </p>

            <div className="rules-container">
              <div className="rule-item">
                <div className="rule-badge">BOUNDARY</div>
                <p className="rule-text">
                  <strong>Authoritative Calculation Core:</strong> Algorithms 0–13 are deterministic
                  Python calculations. Nugen is advisory only and cannot override risk or resource
                  constraints.
                </p>
              </div>

              <div className="rule-item">
                <div className="rule-badge">INTEGRITY</div>
                <p className="rule-text">
                  <strong>Data Completeness:</strong> Missing required telemetry yields{' '}
                  <code>DATA_INSUFFICIENT</code>. No score or safe route is ever fabricated.
                </p>
              </div>

              <div className="rule-item">
                <div className="rule-badge">OFFLINE</div>
                <p className="rule-text">
                  <strong>SOS Dispatch:</strong> Citizen reports remain <code>NOT_SENT</code> in
                  IndexedDB outbox until the backend provides signed receipt.
                </p>
              </div>
            </div>

            <div className="milestone-roadmap">
              <h4 className="roadmap-title">Roadmap Pipeline</h4>
              <div className="roadmap-steps">
                <div className="step-item step-completed">
                  <CheckCircle2 size={16} />
                  <span>Milestone 0: Full-Stack Foundation</span>
                </div>
                <div className="step-item step-pending">
                  <ArrowRight size={16} />
                  <span>Milestone 1: Operations Dashboard Shell</span>
                </div>
                <div className="step-item step-pending">
                  <ArrowRight size={16} />
                  <span>Milestone 2: Deterministic Risk Engine (Alg 0-5)</span>
                </div>
                <div className="step-item step-pending">
                  <ArrowRight size={16} />
                  <span>Milestone 3: Consequence Graph & Cascades (Alg 6-9)</span>
                </div>
                <div className="step-item step-pending">
                  <ArrowRight size={16} />
                  <span>Milestone 4: Intervention Optimizer & Decision Cards (Alg 10-13)</span>
                </div>
                <div className="step-item step-pending">
                  <ArrowRight size={16} />
                  <span>Milestone 5: Multi-Phase Emergency Chatbot</span>
                </div>
              </div>
            </div>
          </div>
        </section>
      </main>

      {/* Footer */}
      <footer className="footer">
        <div className="footer-content">
          <span>CLIMAFORGE © 2026 — Climate-Flood Decision Support Prototype</span>
          <span className="footer-divider">•</span>
          <span>FastAPI + React 19 + TypeScript + Vite</span>
          <span className="footer-divider">•</span>
          <span className="text-cyan">Milestone 0: Verified & Ready</span>
        </div>
      </footer>
    </div>
  );
};

export default App;
