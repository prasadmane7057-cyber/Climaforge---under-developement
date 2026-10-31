import React, { useState, useEffect, useCallback } from 'react';
import { Sidebar, type NavigationTab } from './components/Sidebar';
import { Header } from './components/Header';
import { OverviewTab } from './components/OverviewTab';
import { RiskMapTab } from './components/RiskMapTab';
import { ConsequenceGraphTab } from './components/ConsequenceGraphTab';
import { InterventionsTab } from './components/InterventionsTab';
import { EmergencyChatbotTab } from './components/EmergencyChatbotTab';
import { AuditLogTab } from './components/AuditLogTab';
import {
  checkBackendHealth,
  fetchScenarios,
  fetchScenarioDetail,
  fetchAuditLogs,
  recordClientAuditEvent,
  runScenarioAnalysis,
  type HealthCheckResult,
} from './services/api';
import type {
  ScenarioSummaryItem,
  ScenarioDetail,
  AuditEvent,
  ScenarioAnalysisResponse,
} from './types/api';
import './App.css';

export const App: React.FC = () => {
  const [activeTab, setActiveTab] = useState<NavigationTab>('overview');
  const [healthResult, setHealthResult] = useState<HealthCheckResult | null>(null);
  const [isCheckingHealth, setIsCheckingHealth] = useState<boolean>(true);

  // Scenarios state
  const [scenarios, setScenarios] = useState<ScenarioSummaryItem[]>([]);
  const [selectedScenarioId, setSelectedScenarioId] = useState<string>('scenario-monsoon-alert');
  const [scenarioDetail, setScenarioDetail] = useState<ScenarioDetail | null>(null);
  const [isLoadingScenario, setIsLoadingScenario] = useState<boolean>(false);

  // Audit trail state
  const [auditLogs, setAuditLogs] = useState<AuditEvent[]>([]);
  const [isLoadingAudit, setIsLoadingAudit] = useState<boolean>(false);
  const [auditError, setAuditError] = useState<string | null>(null);

  // Milestone 2 Deterministic Risk Analysis State
  const [analysisResult, setAnalysisResult] = useState<ScenarioAnalysisResponse | null>(null);
  const [isAnalyzing, setIsAnalyzing] = useState<boolean>(false);
  const [analysisError, setAnalysisError] = useState<string | null>(null);

  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // 1. Check health
  const refreshHealth = useCallback(async () => {
    setIsCheckingHealth(true);
    const res = await checkBackendHealth();
    setHealthResult(res);
    setIsCheckingHealth(false);
  }, []);

  // 2. Load audit logs
  const loadAuditLogs = useCallback(async () => {
    setIsLoadingAudit(true);
    setAuditError(null);
    try {
      const logs = await fetchAuditLogs();
      setAuditLogs(logs);
    } catch (err) {
      setAuditError(err instanceof Error ? err.message : 'Failed to load the audit trail from backend.');
    } finally {
      setIsLoadingAudit(false);
    }
  }, []);

  // 3. Load scenario detail
  const loadScenario = useCallback(
    async (scenarioId: string) => {
      setIsLoadingScenario(true);
      setErrorMessage(null);
      setAnalysisResult(null);
      setAnalysisError(null);
      try {
        const detail = await fetchScenarioDetail(scenarioId);
        setScenarioDetail(detail);
        setSelectedScenarioId(scenarioId);

        // Record real user interaction event
        await recordClientAuditEvent('SCENARIO_LOADED', `Operator loaded scenario '${detail.name}'`, {
          scenario_id: scenarioId,
          severity: detail.severity,
        });
        loadAuditLogs();
      } catch (err) {
        setErrorMessage(
          err instanceof Error
            ? err.message
            : `Failed to load scenario '${scenarioId}' from backend.`
        );
      } finally {
        setIsLoadingScenario(false);
      }
    },
    [loadAuditLogs]
  );

  // 4. Milestone 2 Run Analysis Action
  const handleRunAnalysis = useCallback(async () => {
    if (isAnalyzing || !selectedScenarioId) return;
    setIsAnalyzing(true);
    setAnalysisError(null);
    try {
      const res = await runScenarioAnalysis(selectedScenarioId);
      setAnalysisResult(res);
      await loadAuditLogs();
    } catch (err) {
      setAnalysisError(
        err instanceof Error ? err.message : 'Analysis failed to execute on backend'
      );
      setAnalysisResult(null);
    } finally {
      setIsAnalyzing(false);
    }
  }, [isAnalyzing, selectedScenarioId, loadAuditLogs]);

  // 4. Initial Bootstrap
  useEffect(() => {
    async function init() {
      await refreshHealth();
      try {
        const scList = await fetchScenarios();
        setScenarios(scList);
        if (scList.length > 0) {
          const defaultId =
            scList.find((s) => s.scenario_id === 'scenario-monsoon-alert')
              ?.scenario_id || scList[0].scenario_id;
          await loadScenario(defaultId);
        }
      } catch {
        // Fallback or offline state handled gracefully
      }
      loadAuditLogs();
    }
    init();
  }, [refreshHealth, loadScenario, loadAuditLogs]);

  // Tab navigation handler
  const handleSelectTab = async (tab: NavigationTab) => {
    setActiveTab(tab);
    await recordClientAuditEvent(
      'USER_NAVIGATION',
      `Operator navigated to ${tab.replace('-', ' ')} panel`,
      { tab, scenario_id: selectedScenarioId }
    );
    if (tab === 'audit-log') {
      loadAuditLogs();
    }
  };

  return (
    <div className="operations-center-layout">
      {/* Sidebar Navigation */}
      <Sidebar
        activeTab={activeTab}
        onSelectTab={handleSelectTab}
        backendOnline={!!healthResult?.success}
      />

      {/* Main Operations Content Area */}
      <div className="operations-main-area">
        <Header
          activeTab={activeTab}
          healthResult={healthResult}
          isCheckingHealth={isCheckingHealth}
          onRefreshHealth={refreshHealth}
          scenarioName={scenarioDetail?.name}
          scenarios={scenarios}
          selectedScenarioId={selectedScenarioId}
          onSelectScenario={loadScenario}
          isLoadingScenario={isLoadingScenario}
        />

        <main className="dashboard-content-scroll">
          {/* Error Banner if connection or loading failed */}
          {errorMessage && (
            <div className="error-alert-bar">
              <span>{errorMessage}</span>
              <button
                type="button"
                className="btn btn-sm btn-retry"
                onClick={() => loadScenario(selectedScenarioId)}
              >
                Retry
              </button>
            </div>
          )}

          {/* Active Navigation Panel */}
          {activeTab === 'overview' && (
            <OverviewTab
              scenarios={scenarios}
              selectedScenarioId={selectedScenarioId}
              scenarioDetail={scenarioDetail}
              isLoadingScenario={isLoadingScenario}
              onSelectScenario={loadScenario}
              healthResult={healthResult}
              recentAuditLogs={auditLogs}
              analysisResult={analysisResult}
              isAnalyzing={isAnalyzing}
              analysisError={analysisError}
              onRunAnalysis={handleRunAnalysis}
              onNavigateTab={handleSelectTab}
            />
          )}

          {activeTab === 'risk-map' && (
            <RiskMapTab
              scenarioDetail={scenarioDetail}
              analysisResult={analysisResult}
              isLoadingScenario={isLoadingScenario}
              isAnalyzing={isAnalyzing}
              analysisError={analysisError}
            />
          )}

          {activeTab === 'consequence-graph' && (
            <ConsequenceGraphTab
              scenarioDetail={scenarioDetail}
              analysisResult={analysisResult}
              isLoadingScenario={isLoadingScenario}
              isAnalyzing={isAnalyzing}
              analysisError={analysisError}
              onRunAnalysis={handleRunAnalysis}
            />
          )}

          {activeTab === 'interventions' && (
            <InterventionsTab
              scenarioDetail={scenarioDetail}
              analysisResult={analysisResult}
              isAnalyzing={isAnalyzing}
              analysisError={analysisError}
              onRunAnalysis={handleRunAnalysis}
            />
          )}

          {activeTab === 'emergency-chatbot' && (
            <EmergencyChatbotTab backendOnline={!!healthResult?.success} />
          )}

          {activeTab === 'audit-log' && (
            <AuditLogTab
              auditLogs={auditLogs}
              isLoading={isLoadingAudit}
              error={auditError}
              onRefresh={loadAuditLogs}
            />
          )}
        </main>

        {/* Global Footer */}
        <footer className="operations-footer">
          <div className="footer-left">
            <span>CLIMAFORGE &bull; Hazard Decision Support</span>
          </div>
          <div className="footer-right">
            <span>Deterministic Algorithms 0&ndash;13 &bull; Nugen Advisory AI (Standby) &bull; React 19 + FastAPI</span>
          </div>
        </footer>
      </div>
    </div>
  );
};

export default App;
