import React from 'react';
import {
  RefreshCw,
  Server,
  AlertTriangle,
} from 'lucide-react';
import type { HealthCheckResult } from '../services/api';
import type { NavigationTab } from './Sidebar';

interface HeaderProps {
  activeTab: NavigationTab;
  healthResult: HealthCheckResult | null;
  isCheckingHealth: boolean;
  onRefreshHealth: () => void;
  scenarioName?: string;
}

const TAB_TITLES: Record<NavigationTab, { title: string; subtitle: string }> = {
  overview: {
    title: 'Operations Overview & Scenario Monitor',
    subtitle: 'Zonal risk aggregation, critical asset distribution, and telemetry overview',
  },
  'risk-map': {
    title: 'Tactical Risk Map & Zonal Inundation Schematic',
    subtitle: 'Spatial distribution of hydraulic risk, watercourse proximity, and asset locations',
  },
  'consequence-graph': {
    title: 'Consequence Graph & Critical Cascade Infrastructure',
    subtitle: 'Directed failure propagation dependencies across critical facilities (Milestone 3 Preview)',
  },
  interventions: {
    title: 'Candidate Interventions & Logistics Catalog',
    subtitle: 'Mitigation actions, barrier deployments, and resource demands (Milestone 4 Preview)',
  },
  'emergency-chatbot': {
    title: 'Autonomous Citizen Emergency Guidance',
    subtitle: 'Pre-calamity warning, verified live navigation, and offline SOS outbox (Milestone 5 Preview)',
  },
  'audit-log': {
    title: 'System Operational & UI Session Audit Log',
    subtitle: 'Authentic chronological record of backend lifecycle events and operator actions',
  },
};

export const Header: React.FC<HeaderProps> = ({
  activeTab,
  healthResult,
  isCheckingHealth,
  onRefreshHealth,
  scenarioName,
}) => {
  const currentTabInfo = TAB_TITLES[activeTab];

  return (
    <header className="dashboard-header">
      {/* Top Banner */}
      <div className="prototype-banner">
        <div className="banner-content">
          <AlertTriangle size={14} className="banner-icon" />
          <span className="banner-tag">SYNTHETIC / ILLUSTRATIVE DATA ONLY</span>
          <span className="banner-desc">
            For CLIMAFORGE prototype demonstration only. Not for real-world evacuation or emergency dispatch.
          </span>
        </div>
      </div>

      {/* Main Header Bar */}
      <div className="header-bar">
        <div className="header-title-block">
          <div className="breadcrumb">
            <span>CLIMAFORGE</span>
            <span className="breadcrumb-separator">/</span>
            <span className="breadcrumb-current">{activeTab.replace('-', ' ').toUpperCase()}</span>
            {scenarioName && (
              <>
                <span className="breadcrumb-separator">/</span>
                <span className="breadcrumb-scenario">{scenarioName}</span>
              </>
            )}
          </div>
          <h1 className="header-title">{currentTabInfo.title}</h1>
          <p className="header-subtitle">{currentTabInfo.subtitle}</p>
        </div>

        <div className="header-actions">
          {/* Connection Status Pill */}
          <div
            className={`connection-pill ${
              isCheckingHealth
                ? 'pill-checking'
                : healthResult?.success
                ? 'pill-online'
                : 'pill-offline'
            }`}
          >
            <Server size={14} />
            <span className="connection-text">
              {isCheckingHealth
                ? 'Checking...'
                : healthResult?.success
                ? 'Core Online'
                : 'Core Disconnected'}
            </span>
            {healthResult?.latencyMs !== undefined && (
              <span className="latency-badge">{healthResult.latencyMs}ms</span>
            )}
          </div>

          {/* Quick Check Health Button */}
          <button
            type="button"
            className="btn btn-icon-secondary"
            onClick={onRefreshHealth}
            disabled={isCheckingHealth}
            title="Ping backend health endpoint"
          >
            <RefreshCw size={15} className={isCheckingHealth ? 'spin-animation' : ''} />
          </button>
        </div>
      </div>
    </header>
  );
};
