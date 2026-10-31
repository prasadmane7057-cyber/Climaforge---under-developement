import React, { useEffect, useMemo, useState } from 'react';
import { Activity, AlertTriangle, Info, Network } from 'lucide-react';
import type {
  ScenarioDetail,
  ScenarioAnalysisResponse,
  BreakPointItem,
} from '../types/api';

interface ConsequenceGraphTabProps {
  scenarioDetail: ScenarioDetail | null;
  analysisResult?: ScenarioAnalysisResponse | null;
  isLoadingScenario?: boolean;
  isAnalyzing?: boolean;
  analysisError?: string | null;
  onRunAnalysis?: () => void;
}

export const ConsequenceGraphTab: React.FC<ConsequenceGraphTabProps> = ({
  scenarioDetail,
  analysisResult,
  isLoadingScenario = false,
  isAnalyzing = false,
  analysisError = null,
  onRunAnalysis,
}) => {
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);

  const cascade = analysisResult?.cascade_analysis;
  const critical = analysisResult?.critical_nodes;
  const breakPoints = analysisResult?.break_points;
  const graph = analysisResult?.consequence_graph;
  const isMonitoringOnly = !!analysisResult?.is_monitoring_only
    || analysisResult?.cascade_status === 'SKIPPED_MONITORING_ONLY'
    || analysisResult?.pipeline_status === 'MONITORING_ONLY';
  const isDataInsufficient = analysisResult?.pipeline_status === 'DATA_INSUFFICIENT';

  useEffect(() => {
    setSelectedNodeId(null);
  }, [scenarioDetail?.scenario_id, analysisResult?.scenario_id]);

  const nodePositions = useMemo(() => {
    const positions: Record<string, { x: number; y: number }> = {};
    if (!graph?.nodes.length) return positions;

    const adjacency = new Map<string, string[]>();
    graph.edges.forEach((edge) => {
      adjacency.set(edge.source, [...(adjacency.get(edge.source) ?? []), edge.target]);
    });

    const seed = graph.nodes.find((node) => node.seed)?.id ?? graph.nodes[0]?.id;
    const depth = new Map<string, number>();
    if (seed) {
      depth.set(seed, 0);
      const queue = [seed];
      while (queue.length) {
        const current = queue.shift();
        if (!current) break;
        (adjacency.get(current) ?? []).forEach((next) => {
          if (!depth.has(next)) {
            depth.set(next, (depth.get(current) ?? 0) + 1);
            queue.push(next);
          }
        });
      }
    }

    graph.nodes.forEach((node) => {
      if (!depth.has(node.id)) depth.set(node.id, depth.size);
    });

    const levels = new Map<number, string[]>();
    graph.nodes.forEach((node) => {
      const level = depth.get(node.id) ?? 0;
      levels.set(level, [...(levels.get(level) ?? []), node.id]);
    });

    const maxLevel = Math.max(...Array.from(levels.keys()));
    levels.forEach((nodeIds, level) => {
      const widthSlots = maxLevel > 0 ? 960 / maxLevel : 960;
      nodeIds.forEach((nodeId, index) => {
        const y = nodeIds.length === 1
          ? 210
          : 105 + (index * 210 / (nodeIds.length - 1));
        positions[nodeId] = {
          x: 70 + level * widthSlots,
          y,
        };
      });
    });
    return positions;
  }, [graph]);

  const selectedNodeDetails = selectedNodeId && graph
    ? graph.nodes.find((node) => node.id === selectedNodeId)
    : null;
  const selectedNodeState = selectedNodeId && cascade?.node_states
    ? cascade.node_states[selectedNodeId]
    : null;
  const selectedCriticalItem = selectedNodeId && critical?.ranked_nodes
    ? critical.ranked_nodes.find((node) => node.node_id === selectedNodeId)
    : null;
  const incomingEdges = selectedNodeId && graph
    ? graph.edges.filter((edge) => edge.target === selectedNodeId)
    : [];
  const outgoingEdges = selectedNodeId && graph
    ? graph.edges.filter((edge) => edge.source === selectedNodeId)
    : [];

  const nodeCount = graph?.node_count ?? graph?.nodes.length ?? 0;
  const edgeCount = graph?.edge_count ?? graph?.edges.length ?? 0;
  const failingNodeCount = cascade?.failing_nodes.length ?? 0;

  const renderEmptyAnalysis = () => (
    <div className="redesign-state-card empty-state">
      <Network size={22} />
      <div>
        <strong>Consequence graph awaiting analysis</strong>
        <span>Run flood analysis to evaluate dependencies and cascade propagation for {scenarioDetail?.name || 'the active scenario'}.</span>
      </div>
      {onRunAnalysis && (
        <button type="button" className="btn btn-primary" onClick={onRunAnalysis} disabled={isAnalyzing}>
          {isAnalyzing ? 'Running analysis' : 'Run flood analysis'}
        </button>
      )}
    </div>
  );

  return (
    <div className="tab-pane redesigned-section consequence-pane">
      <div className="section-page-header">
        <div>
          <span className="section-eyebrow">Dependency intelligence</span>
          <h2 className="section-title">Consequence graph</h2>
          <p className="section-description">Dependency paths, operational states, and critical infrastructure consequences from the last analysis.</p>
        </div>
        <div className={`analysis-status-chip ${isAnalyzing ? 'status-running' : isMonitoringOnly ? 'status-monitoring' : analysisError || isDataInsufficient ? 'status-alert' : cascade ? 'status-ready' : 'status-awaiting'}`}>
          <span className="status-dot" />
          {isAnalyzing ? 'Analysis running' : isMonitoringOnly ? 'Monitoring only' : isDataInsufficient ? 'Data insufficient' : analysisError ? 'Analysis error' : cascade ? 'Analysis complete' : 'Awaiting analysis'}
        </div>
      </div>

      <div className="scenario-context-strip">
        <div><span className="context-label">Active scenario</span><strong>{scenarioDetail?.name || 'No scenario selected'}</strong></div>
        <div><span className="context-label">Graph source</span><strong>{analysisResult?.data_label || scenarioDetail?.data_label || 'Unavailable'}</strong></div>
        <div><span className="context-label">Cascade status</span><strong>{analysisResult?.cascade_status || 'NOT_RUN'}</strong></div>
      </div>

      {(isLoadingScenario || isAnalyzing) && (
        <div className="redesign-state-card loading-state">
          <Activity size={22} />
          <div><strong>{isLoadingScenario ? 'Loading scenario' : 'Running cascade simulation'}</strong><span>{isLoadingScenario ? 'Scenario details are being refreshed.' : 'Dependency and propagation results are being calculated.'}</span></div>
        </div>
      )}

      {analysisError && (
        <div className="redesign-state-card error-state">
          <AlertTriangle size={22} />
          <div><strong>Analysis could not be completed</strong><span>{analysisError}</span></div>
        </div>
      )}

      {!analysisResult && !isAnalyzing && !isLoadingScenario && !analysisError && renderEmptyAnalysis()}

      {isDataInsufficient && (
        <div className="redesign-state-card error-state">
          <AlertTriangle size={22} />
          <div><strong>DATA_INSUFFICIENT</strong><span>Required telemetry is missing, so dependency propagation was not fabricated or executed.</span></div>
        </div>
      )}

      {isMonitoringOnly && (
        <div className="redesign-state-card monitoring-state">
          <Info size={22} />
          <div><strong>Monitoring-only state</strong><span>No qualifying hotspots were found. Downstream cascade analysis is safely bypassed.</span></div>
        </div>
      )}

      {cascade && !isMonitoringOnly && !isDataInsufficient && (
        <>
          <div className="consequence-summary-grid">
            <div className="risk-summary-card">
              <span>Cascade risk</span>
              <strong className={cascade.cascade_risk >= 0.40 ? 'risk-value-red' : cascade.cascade_risk >= 0.25 ? 'risk-value-amber' : ''}>{cascade.cascade_risk.toFixed(3)}</strong>
              <small>Consequence-weighted average</small>
            </div>
            <div className="risk-summary-card">
              <span>Failing nodes</span>
              <strong>{failingNodeCount}</strong>
              <small>Threshold {cascade.tau_applied.toFixed(2)}</small>
            </div>
            <div className="risk-summary-card">
              <span>Critical hub</span>
              <strong className="summary-text-value">{critical?.critical_node || 'None'}</strong>
              <small>{critical?.critical_node_details ? `Score ${critical.critical_node_details.criticality_score.toFixed(3)}` : 'No critical ranking available'}</small>
            </div>
            <div className="risk-summary-card">
              <span>Best break point</span>
              <strong className="summary-text-value">{breakPoints?.best_break_point?.intervention_id || 'None'}</strong>
              <small>{breakPoints?.best_break_point ? `Reduction ${breakPoints.best_break_point.impact_reduction_pct.toFixed(1)}%` : 'No candidate evaluated'}</small>
            </div>
          </div>

          {cascade.cascade_chain.length > 0 && (
            <div className="dashboard-card redesigned-card">
              <div className="card-header-row redesigned-card-header">
                <div><h3>Propagation chain</h3><p>Primary sequence at threshold {cascade.tau_applied.toFixed(2)}</p></div>
                <span className="data-provenance-tag">{cascade.cascade_chain.length} links</span>
              </div>
              <div className="chain-strip-container redesigned-chain">
                <button type="button" className="chain-node chain-node-seed" onClick={() => setSelectedNodeId(cascade.seed_node)}>
                  <span>Flood initiator</span><strong>{cascade.seed_node}</strong><small>{cascade.seed_risk.toFixed(3)}</small>
                </button>
                {cascade.cascade_chain.map((nodeId) => (
                  <React.Fragment key={nodeId}>
                    <span className="chain-arrow">→</span>
                    <button
                      type="button"
                      className={`chain-node ${critical?.critical_node === nodeId ? 'chain-node-critical' : 'chain-node-failing'} ${selectedNodeId === nodeId ? 'chain-node-selected' : ''}`}
                      onClick={() => setSelectedNodeId(nodeId)}
                    >
                      <span>{critical?.critical_node === nodeId ? 'Critical hub' : 'Affected node'}</span>
                      <strong>{nodeId}</strong>
                      <small>{(cascade.node_risks[nodeId] ?? 0).toFixed(3)}</small>
                    </button>
                  </React.Fragment>
                ))}
              </div>
            </div>
          )}

          <div className="dashboard-card redesigned-card graph-layout-card">
            <div className="card-header-row redesigned-card-header">
              <div><h3>Infrastructure dependency graph</h3><p>Select a node to inspect risk, dependencies, and operational state.</p></div>
              <span className="data-provenance-tag">{nodeCount} nodes · {edgeCount} dependencies</span>
            </div>

            {!graph || graph.nodes.length === 0 ? (
              <div className="redesign-state-card empty-state"><Network size={22} /><div><strong>No graph data is available</strong><span>The analysis returned no consequence nodes or dependencies.</span></div></div>
            ) : (
              <>
                <div className="graph-svg-wrapper redesigned-graph-wrapper">
                  <svg viewBox="0 0 1060 420" className="consequence-graph-svg redesigned-consequence-svg" role="img" aria-label="Consequence dependency graph">
                    <defs>
                      <marker id="edge-arrow" markerWidth="8" markerHeight="6" refX="7" refY="3" orient="auto"><path d="M0,0 L8,3 L0,6 Z" fill="#94a3b8" /></marker>
                      <marker id="edge-arrow-failing" markerWidth="8" markerHeight="6" refX="7" refY="3" orient="auto"><path d="M0,0 L8,3 L0,6 Z" fill="#dc2626" /></marker>
                    </defs>
                    {graph.edges.map((edge) => {
                      const source = nodePositions[edge.source];
                      const target = nodePositions[edge.target];
                      if (!source || !target) return null;
                      const failing = cascade.cascade_chain.includes(edge.source) && cascade.cascade_chain.includes(edge.target);
                      const midX = (source.x + target.x) / 2;
                      const midY = (source.y + target.y) / 2;
                      return (
                        <g key={`${edge.source}-${edge.target}-${edge.dependency_type}`}>
                          <line x1={source.x} y1={source.y} x2={target.x} y2={target.y} className={`graph-edge-line ${failing ? 'edge-failing' : ''}`} markerEnd={`url(#${failing ? 'edge-arrow-failing' : 'edge-arrow'})`} />
                          <rect x={midX - 22} y={midY - 10} width="44" height="20" rx="6" className="edge-label-bg" />
                          <text x={midX} y={midY + 4} className="edge-label-text">s {edge.s.toFixed(2)}</text>
                        </g>
                      );
                    })}
                    {graph.nodes.map((node) => {
                      const position = nodePositions[node.id];
                      if (!position) return null;
                      const risk = cascade.node_risks[node.id] ?? (node.seed ? cascade.seed_risk : 0);
                      const state = cascade.node_states[node.id]?.state;
                      const isCritical = critical?.critical_node === node.id;
                      const isSelected = selectedNodeId === node.id;
                      return (
                        <g key={node.id} className={`graph-node-group ${isSelected ? 'node-selected' : ''}`} onClick={() => setSelectedNodeId(node.id)} role="button" aria-label={`Select ${node.label}`}>
                          <circle cx={position.x} cy={position.y} r={isCritical ? 34 : 28} className={`graph-node-circle node-${node.seed ? 'seed' : state?.toLowerCase() || (isCritical ? 'critical' : risk >= 0.15 ? 'watch' : 'safe')}`} />
                          <text x={position.x} y={position.y - 3} className="node-title-text">{node.id.length > 14 ? `${node.id.slice(0, 12)}…` : node.id}</text>
                          <text x={position.x} y={position.y + 12} className="node-risk-text">{risk.toFixed(2)}</text>
                          {isCritical && <text x={position.x} y={position.y + 48} className="node-badge-text">CRITICAL</text>}
                        </g>
                      );
                    })}
                  </svg>
                </div>

                <div className="graph-legend redesigned-graph-legend">
                  <span><i className="legend-node legend-seed" />Seed</span>
                  <span><i className="legend-node legend-safe" />Safe</span>
                  <span><i className="legend-node legend-watch" />Watch</span>
                  <span><i className="legend-node legend-failing" />Failing</span>
                  <span><i className="legend-node legend-critical" />Critical hub</span>
                  <span><i className="legend-link legend-failing-link" />Failure propagation</span>
                </div>

                {selectedNodeId && selectedNodeDetails ? (
                  <aside className="node-inspector-drawer redesigned-node-inspector">
                    <div className="inspector-head">
                      <div><span className="inspector-kicker">Selected node</span><h4>{selectedNodeDetails.label}</h4></div>
                      <button type="button" className="btn btn-sm btn-outline" onClick={() => setSelectedNodeId(null)}>Clear selection</button>
                    </div>
                    <div className="selected-node-grid">
                      <dl>
                        <div><dt>Node ID</dt><dd>{selectedNodeDetails.id}</dd></div>
                        <div><dt>Category</dt><dd>{selectedNodeDetails.category}</dd></div>
                        <div><dt>Failure probability</dt><dd>{(cascade.node_risks[selectedNodeId] ?? selectedNodeDetails.f).toFixed(4)}</dd></div>
                        <div><dt>Operational state</dt><dd>{selectedNodeState?.state || 'SAFE'}</dd></div>
                        <div><dt>Vulnerability</dt><dd>{selectedNodeDetails.f.toFixed(3)}</dd></div>
                        <div><dt>Consequence weight</dt><dd>{selectedNodeDetails.c.toFixed(3)}</dd></div>
                        {selectedCriticalItem && <><div><dt>Criticality rank</dt><dd>#{selectedCriticalItem.rank} · {selectedCriticalItem.criticality_score.toFixed(3)}</dd></div><div><dt>Dependencies</dt><dd>{selectedCriticalItem.dependency_count}</dd></div></>}
                      </dl>
                      <div className="dependency-list">
                        <div><span>Incoming dependencies</span>{incomingEdges.length ? incomingEdges.map((edge) => <strong key={`in-${edge.source}-${edge.target}`}>{edge.source} · {edge.dependency_type} · s {edge.s.toFixed(2)}</strong>) : <em>None</em>}</div>
                        <div><span>Outgoing dependencies</span>{outgoingEdges.length ? outgoingEdges.map((edge) => <strong key={`out-${edge.source}-${edge.target}`}>{edge.target} · {edge.dependency_type} · s {edge.s.toFixed(2)}</strong>) : <em>None</em>}</div>
                      </div>
                    </div>
                  </aside>
                ) : (
                  <div className="graph-selection-placeholder">Select a graph node to view its operational details and dependency paths.</div>
                )}
              </>
            )}
          </div>

          {critical && critical.ranked_nodes.length > 0 && (
            <div className="dashboard-card redesigned-card">
              <div className="card-header-row redesigned-card-header"><div><h3>Critical node ranking</h3><p>Ranked using the backend criticality calculation.</p></div><span className="data-provenance-tag">{critical.ranked_nodes.length} candidates</span></div>
              <div className="table-responsive">
                <table className="data-table redesigned-table"><thead><tr><th>Rank</th><th>Node</th><th>Criticality</th><th>Direct p</th><th>Population</th><th>Infrastructure</th><th>Emergency</th><th>Downstream</th><th>Dependencies</th></tr></thead><tbody>
                  {critical.ranked_nodes.map((node) => (
                    <tr key={node.node_id} className={node.rank === 1 ? 'row-critical-highlight' : ''}>
                      <td><span className={`rank-badge ${node.rank === 1 ? 'rank-top' : ''}`}>#{node.rank}</span></td>
                      <td><strong>{node.label}</strong><small className="table-cell-code">{node.node_id}</small></td>
                      <td><strong className="score-code">{node.criticality_score.toFixed(3)}</strong></td>
                      <td>{node.scaled_features?.Direct?.toFixed(2) ?? '-'}</td><td>{node.scaled_features?.Pop?.toFixed(2) ?? '-'}</td><td>{node.scaled_features?.Infra?.toFixed(2) ?? '-'}</td><td>{node.scaled_features?.Emerg?.toFixed(2) ?? '-'}</td><td>{node.scaled_features?.Downstream?.toFixed(2) ?? '-'}</td><td>{node.dependency_count}</td>
                    </tr>
                  ))}
                </tbody></table>
              </div>
            </div>
          )}

          {breakPoints && breakPoints.ranked_break_points.length > 0 && (
            <div className="dashboard-card redesigned-card">
              <div className="card-header-row redesigned-card-header"><div><h3>Candidate break points</h3><p>Backend-simulated interventions ranked by cascade risk reduction.</p></div><span className="data-provenance-tag">{breakPoints.ranked_break_points.length} actions</span></div>
              <div className="table-responsive">
                <table className="data-table redesigned-table"><thead><tr><th>Rank</th><th>Intervention</th><th>Target</th><th>Risk before</th><th>Risk after</th><th>Reduction</th><th>Cascade length</th></tr></thead><tbody>
                  {breakPoints.ranked_break_points.map((item: BreakPointItem) => (
                    <tr key={item.intervention_id} className={item.rank === 1 ? 'row-best-breakpoint' : ''}>
                      <td><span className={`rank-badge ${item.rank === 1 ? 'rank-top' : ''}`}>#{item.rank}</span></td>
                      <td><strong>{item.action}</strong><small className="table-cell-code">{item.intervention_id}</small></td>
                      <td>{item.target_node}</td><td>{item.baseline_cascade_risk.toFixed(3)}</td><td>{item.mitigated_cascade_risk.toFixed(3)}</td><td><strong className="reduction-pct-pill">-{item.impact_reduction_pct.toFixed(1)}%</strong></td><td>{item.baseline_cascade_length} → {item.mitigated_cascade_length}</td>
                    </tr>
                  ))}
                </tbody></table>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
};
