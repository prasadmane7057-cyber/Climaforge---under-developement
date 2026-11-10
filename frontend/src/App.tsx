import React, { useState, useEffect, useCallback } from 'react';
import { Sidebar, type NavigationTab } from './components/Sidebar';
import { Header } from './components/Header';
import { OverviewTab } from './components/OverviewTab';
import { RiskMapTab } from './components/RiskMapTab';
import { ConsequenceGraphTab } from './components/ConsequenceGraphTab';
import { InterventionsTab } from './components/InterventionsTab';
import { EmergencyChatbotTab } from './components/EmergencyChatbotTab';
import { EnvironmentalTab } from './components/EnvironmentalTab';
import { AuditLogTab } from './components/AuditLogTab';
import { LoginModal } from './components/LoginModal';
import { UnauthorizedView } from './components/UnauthorizedView';
import { AuthProvider } from './context/AuthContext';
import { useAuth } from './context/useAuth';
import type { PermissionName } from './types/auth';
import {
  checkBackendHealth,
  fetchScenarios,
  fetchScenarioDetail,
  fetchAuditLogs,
  recordClientAuditEvent,
  runScenarioAnalysis,
  predictFloodRisk,
  type HealthCheckResult,
} from './services/api';
import type {
  ScenarioSummaryItem,
  ScenarioDetail,
  AuditEvent,
  ScenarioAnalysisResponse,
  FloodPredictionResponse,
} from './types/api';
import { AlertTriangle, LogIn } from 'lucide-react';
import './App.css';

const TAB_PERMISSIONS: Record<NavigationTab, PermissionName> = {
  overview: 'scenario.read',
  'risk-map': 'scenario.read',
  'consequence-graph': 'scenario.read',
  interventions: 'scenario.read',
  'emergency-chatbot': 'chatbot.ask',
  environmental: 'scenario.read',
  'audit-log': 'audit.read',
};

export const OperationsDashboard: React.FC = () => {
  const {
    user,
    status: authStatus,
    logout,
    hasPermission,
    isLoginModalOpen,
    openLoginModal,
    closeLoginModal,
  } = useAuth();

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
  const [mlPrediction, setMlPrediction] = useState<FloodPredictionResponse | null>(null);
  const [mlPredictionError, setMlPredictionError] = useState<string | null>(null);

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

        // Record real user interaction event if user has audit.create permission or in demonstrator mode
        if (!user || hasPermission('audit.create')) {
          await recordClientAuditEvent('SCENARIO_LOADED', `Operator loaded scenario '${detail.name}'`, {
            scenario_id: scenarioId,
            severity: detail.severity,
          });
        }
        if (!user || hasPermission('audit.read')) {
          loadAuditLogs();
        }
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
    [loadAuditLogs, user, hasPermission]
  );

  // 4. Run Analysis Action with RBAC Guard
  const handleRunAnalysis = useCallback(async () => {
    if (isAnalyzing || !selectedScenarioId) return;

    // RBAC check: Account must possess scenario.run permission
    if (user && !hasPermission('scenario.run')) {
      setAnalysisError('Permission Denied: Account lacks "scenario.run" permission. Execution restricted to Operator, Analyst, or Admin.');
      return;
    }

    setIsAnalyzing(true);
    setAnalysisError(null);
    try {
      const res = await runScenarioAnalysis(selectedScenarioId);
      setAnalysisResult(res);
      if (scenarioDetail?.zones?.length) {
        const rainfall = scenarioDetail.zones.reduce(
          (max, zone) => Math.max(max, zone.rainfall_mm),
          0
        );
        try {
          const ml = await predictFloodRisk({
            prcp_mm: rainfall,
            tmax_c: 20,
            tmin_c: 10,
            snow_mm: 0,
            prcp_lag1_mm: rainfall * 0.8,
            prcp_rolling_3d_mean_mm: rainfall,
            prcp_rolling_7d_mean_mm: rainfall * 0.9,
            prcp_rolling_14d_mean_mm: rainfall * 0.85,
          });
          setMlPrediction(ml);
          setMlPredictionError(null);
        } catch (err) {
          setMlPrediction(null);
          setMlPredictionError(err instanceof Error ? err.message : 'ML prediction failed');
        }
      }
      if (!user || hasPermission('audit.read')) {
        await loadAuditLogs();
      }
    } catch (err) {
      setAnalysisError(
        err instanceof Error ? err.message : 'Analysis failed to execute on backend'
      );
      setAnalysisResult(null);
    } finally {
      setIsAnalyzing(false);
    }
  }, [isAnalyzing, selectedScenarioId, loadAuditLogs, scenarioDetail, user, hasPermission]);

  // 5. Initial Bootstrap
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
    if (!user || hasPermission('audit.create')) {
      await recordClientAuditEvent(
        'USER_NAVIGATION',
        `Operator navigated to ${tab.replace('-', ' ')} panel`,
        { tab, scenario_id: selectedScenarioId }
      );
    }
    if (tab === 'audit-log' && (!user || hasPermission('audit.read'))) {
      loadAuditLogs();
    }
  };

  // Evaluate Tab Access Permission
  const requiredPermission = TAB_PERMISSIONS[activeTab];
  const isTabAuthorized = !user || hasPermission(requiredPermission);

  return (
    <div className="operations-center-layout">
      {/* Sidebar Navigation */}
      <Sidebar
        activeTab={activeTab}
        onSelectTab={handleSelectTab}
        backendOnline={!!healthResult?.success}
        user={user}
        onOpenLogin={openLoginModal}
        onLogout={logout}
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
          user={user}
          onOpenLogin={openLoginModal}
          onLogout={logout}
        />

        {/* Session Expired Banner */}
        {authStatus === 'session-expired' && (
          <div className="session-expired-alert-bar" role="alert">
            <div className="alert-content">
              <AlertTriangle size={16} className="alert-icon" />
              <span>
                Your authenticated session has expired. Please sign in again to restore operator permissions.
              </span>
            </div>
            <button
              type="button"
              className="btn btn-sm btn-primary"
              onClick={openLoginModal}
            >
              <LogIn size={13} />
              <span>Sign In Again</span>
            </button>
          </div>
        )}

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

          {/* RBAC Route Access Guard */}
          {!isTabAuthorized ? (
            <UnauthorizedView
              requiredPermission={requiredPermission}
              userRole={user?.role}
              onNavigateHome={() => setActiveTab('overview')}
              onOpenLogin={openLoginModal}
              isUnauthenticated={!user}
            />
          ) : (
            <>
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
                  mlPrediction={mlPrediction}
                  mlPredictionError={mlPredictionError}
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
                <EmergencyChatbotTab
                  backendOnline={!!healthResult?.success}
                  scenarioId={selectedScenarioId}
                  scenarioName={scenarioDetail?.name}
                />
              )}

              {activeTab === 'environmental' && (
                <EnvironmentalTab />
              )}

              {activeTab === 'audit-log' && (
                <AuditLogTab
                  auditLogs={auditLogs}
                  isLoading={isLoadingAudit}
                  error={auditError}
                  onRefresh={loadAuditLogs}
                />
              )}
            </>
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

      {/* Station Login Modal */}
      <LoginModal isOpen={isLoginModalOpen} onClose={closeLoginModal} />
    </div>
  );
};

export const App: React.FC = () => {
  return (
    <AuthProvider>
      <OperationsDashboard />
    </AuthProvider>
  );
};

export default App;
