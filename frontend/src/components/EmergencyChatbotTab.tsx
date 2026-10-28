import React from 'react';
import {
  MessageSquare,
  AlertCircle,
  Navigation,
  WifiOff,
  Send,
} from 'lucide-react';

export const EmergencyChatbotTab: React.FC = () => {
  return (
    <div className="tab-pane chatbot-pane">
      {/* Scope Status Banner */}
      <div className="milestone-placeholder-banner">
        <div className="placeholder-banner-head">
          <span className="badge-roadmap">SCHEDULED: MILESTONE 5</span>
          <h2 className="banner-title">Emergency Citizen Chatbot Engine</h2>
        </div>
        <p className="banner-text">
          Interactive natural language citizen assistance, safe routing verification, and offline IndexedDB SOS caching will be integrated in Milestone 5. Chatbot backend runtime is in standby for Milestone 1.
        </p>
      </div>

      {/* The 3 Core Operational Modes Specification */}
      <div className="pipeline-preview-card">
        <h3 className="section-title-sm">Autonomous Chatbot Operational Modes (Milestone 5 Design)</h3>
        <div className="pipeline-steps-grid">
          {/* Mode 1 */}
          <div className="pipeline-box">
            <div className="mode-box-head">
              <AlertCircle size={18} className="text-amber" />
              <span className="step-name">1. Pre-Calamity Alert</span>
            </div>
            <p className="step-desc">
              Proactive citizen alerts tailored to specific catchment zones. Delivers elevation awareness, sandbagging guidelines, and shelter locations before water levels peak.
            </p>
          </div>

          {/* Mode 2 */}
          <div className="pipeline-box">
            <div className="mode-box-head">
              <Navigation size={18} className="text-cyan" />
              <span className="step-name">2. Live Safe Navigation</span>
            </div>
            <p className="step-desc">
              Strictly excludes confirmed inundated or blocked roads. Never fabricates safe corridors; marks routes as &quot;CACHED / UNCONFIRMED&quot; if live sensor telemetry is interrupted.
            </p>
          </div>

          {/* Mode 3 */}
          <div className="pipeline-box">
            <div className="mode-box-head">
              <WifiOff size={18} className="text-red" />
              <span className="step-name">3. Panic / Offline SOS</span>
            </div>
            <p className="step-desc">
              Local IndexedDB outbox queue. Distressed citizen SOS reports display <code>NOT SENT</code> until a real server acknowledgement handshake is completed. GPS alone never implies dispatch.
            </p>
          </div>
        </div>
      </div>

      {/* Standby UI Shell Preview */}
      <div className="dashboard-card chatbot-shell-preview">
        <div className="card-header-row">
          <div className="chat-header-title">
            <MessageSquare size={18} className="text-cyan" />
            <span>Citizen Emergency Assistance Console</span>
          </div>
          <span className="status-standby-pill">STANDBY (M5 IMPLEMENTATION)</span>
        </div>

        <div className="mock-chat-window">
          <div className="mock-message bot-msg">
            <div className="msg-bubble">
              <strong>CLIMAFORGE Emergency Dispatch System:</strong>
              <p>
                Welcome to the emergency guidance channel. This module is in verified standby. Full natural language processing and offline IndexedDB synchronization will be enabled in Milestone 5.
              </p>
              <span className="msg-time">System Standby</span>
            </div>
          </div>
        </div>

        <div className="mock-chat-input-row">
          <input
            type="text"
            className="mock-input"
            disabled
            placeholder="Citizen guidance input will be active in Milestone 5..."
          />
          <button type="button" className="btn btn-disabled" disabled>
            <Send size={16} />
          </button>
        </div>
      </div>
    </div>
  );
};
