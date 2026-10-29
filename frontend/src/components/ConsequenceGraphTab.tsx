import React, { useState } from 'react';
import type { ScenarioDetail, ScenarioAnalysisResponse, BreakPointItem } from '../types/api';

interface ConsequenceGraphTabProps {
  scenarioDetail: ScenarioDetail | null;
  analysisResult?: ScenarioAnalysisResponse | null;
  isAnalyzing?: boolean;
  onRunAnalysis?: () => void;
}

export const ConsequenceGraphTab: React.FC<ConsequenceGraphTabProps> = ({
  scenarioDetail,
  analysisResult,
  isAnalyzing = false,
  onRunAnalysis,
}) => {
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);

  const cascade = analysisResult?.cascade_analysis;
  const critical = analysisResult?.critical_nodes;
  const breakPoints = analysisResult?.break_points;
  const graph = analysisResult?.consequence_graph;
  const isMonitoringOnly = analysisResult?.is_monitoring_only || analysisResult?.cascade_status === 'SKIPPED_MONITORING_ONLY';

  // Coords for SVG diagram rendering
  const nodePositions: Record<string, { x: number; y: number }> = {
    Flood: { x: 80, y: 160 },
    Drainage: { x: 260, y: 90 },
    Road: { x: 440, y: 90 },
    'Main Junction A': { x: 620, y: 90 },
    'Emergency Access': { x: 800, y: 90 },
    Hospital: { x: 960, y: 90 },
    Population: { x: 530, y: 260 },
  };

  const selectedNodeDetails = selectedNodeId && graph
    ? graph.nodes.find((n) => n.id === selectedNodeId)
    : null;

  const selectedNodeState = selectedNodeId && cascade?.node_states
    ? cascade.node_states[selectedNodeId]
    : null;

  const selectedCriticalItem = selectedNodeId && critical?.ranked_nodes
    ? critical.ranked_nodes.find((n) => n.node_id === selectedNodeId)
    : null;

  return (
    <div className="tab-pane consequence-pane">
      {/* Scope / Status Banner */}
      <div className="milestone-placeholder-banner banner-live">
        <div className="placeholder-banner-head">
          <span className="badge-live">MILESTONE 3: ACTIVE</span>
          <span className="badge-spec">ALGORITHMS 4–7 DETERMINISTIC CORE</span>
          <h2 className="banner-title">Consequence Graph & Cascade Propagation Engine</h2>
        </div>
        <p className="banner-text">
          Network dependency topology, Noisy-OR probability propagation, critical node identification, and catalogue-backed cascade break point simulation.
        </p>
      </div>

      {/* Analysis trigger bar if not yet executed */}
      {!analysisResult && (
        <div className="dashboard-card action-prompt-card">
          <div className="action-prompt-content">
            <div>
              <h3 className="card-heading-sm">Cascade Simulation Awaiting Execution</h3>
              <p className="card-subheading">
                Run flood analysis on <strong>{scenarioDetail?.name || 'the active scenario'}</strong> to evaluate failure propagation, identify critical hubs, and simulate break points.
              </p>
            </div>
            {onRunAnalysis && (
              <button
                type="button"
                className="btn btn-primary"
                onClick={onRunAnalysis}
                disabled={isAnalyzing}
              >
                {isAnalyzing ? 'Running Simulation...' : 'Run Flood Analysis'}
              </button>
            )}
          </div>
        </div>
      )}

      {/* Monitoring only guard state */}
      {isMonitoringOnly && (
        <div className="dashboard-card monitoring-alert-card">
          <div className="monitoring-alert-head">
            <span className="monitoring-tag">STATUS: MONITORING_ONLY</span>
            <h3 className="card-heading-sm">Downstream Cascade Bypassed</h3>
          </div>
          <p className="card-subheading">
            All evaluated zones scored below the hotspot threshold (&lt; 50.0). Per canonical specification Section 4 &amp; 6.3, downstream cascade propagation and break point detection are safely bypassed.
          </p>
        </div>
      )}

      {/* Active Milestone 3 Cascade Overview Cards */}
      {cascade && !isMonitoringOnly && (
        <>
          <div className="summary-cards-grid">
            <div className="summary-metric-card">
              <span className="metric-label">Cascade Risk (0-1)</span>
              <span className={`metric-value ${cascade.cascade_risk >= 0.40 ? 'val-danger' : cascade.cascade_risk >= 0.25 ? 'val-warning' : 'val-good'}`}>
                {cascade.cascade_risk.toFixed(3)}
              </span>
              <span className="metric-sub">Consequence-Weighted Average</span>
            </div>

            <div className="summary-metric-card">
              <span className="metric-label">Failing Nodes (Length)</span>
              <span className={`metric-value ${cascade.cascade_length >= 4 ? 'val-danger' : cascade.cascade_length >= 2 ? 'val-warning' : 'val-good'}`}>
                {cascade.cascade_length}
              </span>
              <span className="metric-sub">Failure Threshold &tau; &ge; {cascade.tau_applied.toFixed(2)}</span>
            </div>

            <div className="summary-metric-card">
              <span className="metric-label">Critical Node Hub</span>
              <span className="metric-value val-danger">
                {critical?.critical_node || 'N/A'}
              </span>
              <span className="metric-sub">
                Score: {critical?.critical_node_details?.criticality_score.toFixed(3) || '0.000'} (Rank 1)
              </span>
            </div>

            <div className="summary-metric-card">
              <span className="metric-label">Top Break Point</span>
              <span className="metric-value val-good">
                {breakPoints?.best_break_point?.intervention_id || 'N/A'}
              </span>
              <span className="metric-sub">
                -{breakPoints?.best_break_point?.impact_reduction_pct.toFixed(1)}% Simulated Cascade Risk
              </span>
            </div>
          </div>

          {/* Cascade Chain Transmission Strip */}
          <div className="dashboard-card">
            <div className="card-header-row">
              <div>
                <h3 className="card-heading-sm">Cascade Failure Transmission Chain</h3>
                <p className="card-subheading">
                  Primary topological propagation spine along strongest incoming failure edges (&tau; &ge; {cascade.tau_applied.toFixed(2)})
                </p>
              </div>
              <span className="badge-nominal">
                {cascade.cascade_chain.length} Spine Links
              </span>
            </div>

            <div className="chain-strip-container">
              <div className="chain-node chain-node-seed">
                <span className="chain-label">Flood Initiator</span>
                <span className="chain-risk">Risk: {cascade.seed_risk.toFixed(2)}</span>
              </div>
              {cascade.cascade_chain.map((nodeId) => {
                const nodeRisk = cascade.node_risks[nodeId] ?? 0.0;
                const isCrit = critical?.critical_node === nodeId;
                return (
                  <React.Fragment key={nodeId}>
                    <div className="chain-arrow">&rarr;</div>
                    <div
                      className={`chain-node ${isCrit ? 'chain-node-critical' : 'chain-node-failing'}`}
                      onClick={() => setSelectedNodeId(nodeId)}
                      title={`Click to inspect ${nodeId}`}
                    >
                      <span className="chain-label">{nodeId}</span>
                      <span className="chain-risk">Risk: {nodeRisk.toFixed(3)}</span>
                      {isCrit && <span className="chain-tag-crit">CRITICAL HUB</span>}
                    </div>
                  </React.Fragment>
                );
              })}
            </div>
          </div>

          {/* Interactive Network Graph Schematic */}
          <div className="dashboard-card">
            <div className="card-header-row">
              <div>
                <h3 className="card-heading-sm">Urban Infrastructure Consequence Graph Topology</h3>
                <p className="card-subheading">
                  Interactive dependency graph with failure propagation states. Click any node to inspect exposure terms.
                </p>
              </div>
              <span className="data-provenance-tag">SYNTHETIC TOPOLOGY</span>
            </div>

            <div className="graph-svg-wrapper">
              <svg viewBox="0 0 1060 360" className="consequence-graph-svg">
                <defs>
                  <marker
                    id="arrowhead"
                    markerWidth="8"
                    markerHeight="6"
                    refX="22"
                    refY="3"
                    orient="auto"
                  >
                    <polygon points="0 0, 8 3, 0 6" fill="#64748b" />
                  </marker>
                  <marker
                    id="arrowhead-crit"
                    markerWidth="8"
                    markerHeight="6"
                    refX="22"
                    refY="3"
                    orient="auto"
                  >
                    <polygon points="0 0, 8 3, 0 6" fill="#ef4444" />
                  </marker>
                </defs>

                {/* Render Edges */}
                {graph?.edges.map((edge) => {
                  const sourcePos = nodePositions[edge.source] || { x: 100, y: 100 };
                  const targetPos = nodePositions[edge.target] || { x: 200, y: 200 };
                  const midX = (sourcePos.x + targetPos.x) / 2;
                  const midY = (sourcePos.y + targetPos.y) / 2;
                  const isFailingPath =
                    cascade.cascade_chain.includes(edge.source) &&
                    cascade.cascade_chain.includes(edge.target);

                  return (
                    <g key={`${edge.source}->${edge.target}`} className="graph-edge-group">
                      <line
                        x1={sourcePos.x}
                        y1={sourcePos.y}
                        x2={targetPos.x}
                        y2={targetPos.y}
                        className={`graph-edge-line ${isFailingPath ? 'edge-failing' : ''}`}
                        markerEnd={isFailingPath ? 'url(#arrowhead-crit)' : 'url(#arrowhead)'}
                      />
                      <rect
                        x={midX - 18}
                        y={midY - 9}
                        width="36"
                        height="18"
                        rx="4"
                        className="edge-label-bg"
                      />
                      <text x={midX} y={midY + 4} className="edge-label-text">
                        s={edge.s.toFixed(2)}
                      </text>
                    </g>
                  );
                })}

                {/* Render Nodes */}
                {graph?.nodes.map((node) => {
                  const pos = nodePositions[node.id] || { x: 100, y: 100 };
                  const pRisk = cascade.node_risks[node.id] ?? (node.seed ? cascade.seed_risk : 0.0);
                  const isFailing = pRisk >= cascade.tau_applied;
                  const isCriticalNode = critical?.critical_node === node.id;
                  const isSelected = selectedNodeId === node.id;

                  let nodeFillClass = 'node-safe';
                  if (node.seed) nodeFillClass = 'node-seed';
                  else if (isCriticalNode) nodeFillClass = 'node-critical';
                  else if (isFailing) nodeFillClass = 'node-failing';
                  else if (pRisk >= 0.15) nodeFillClass = 'node-watch';

                  return (
                    <g
                      key={node.id}
                      className={`graph-node-group ${isSelected ? 'node-selected' : ''}`}
                      onClick={() => setSelectedNodeId(node.id)}
                      style={{ cursor: 'pointer' }}
                    >
                      <circle
                        cx={pos.x}
                        cy={pos.y}
                        r={isCriticalNode ? 32 : 26}
                        className={`graph-node-circle ${nodeFillClass}`}
                      />
                      <text x={pos.x} y={pos.y - 4} className="node-title-text">
                        {node.id.length > 12 ? node.id.substring(0, 10) + '..' : node.id}
                      </text>
                      <text x={pos.x} y={pos.y + 11} className="node-risk-text">
                        p={pRisk.toFixed(2)}
                      </text>
                      {isCriticalNode && (
                        <text x={pos.x} y={pos.y + 45} className="node-badge-text">
                          CRITICAL
                        </text>
                      )}
                    </g>
                  );
                })}
              </svg>
            </div>

            {/* Selected Node Inspector Drawer */}
            {selectedNodeId && (
              <div className="node-inspector-drawer">
                <div className="inspector-head">
                  <h4 className="inspector-title">
                    Node Inspector: <strong>{selectedNodeId}</strong> ({selectedNodeDetails?.label})
                  </h4>
                  <button
                    type="button"
                    className="btn btn-sm btn-outline"
                    onClick={() => setSelectedNodeId(null)}
                  >
                    Close
                  </button>
                </div>
                <div className="inspector-grid">
                  <div className="inspector-item">
                    <span className="item-label">Failure Probability (p)</span>
                    <span className="item-value">{(cascade.node_risks[selectedNodeId] ?? 0.0).toFixed(4)}</span>
                  </div>
                  <div className="inspector-item">
                    <span className="item-label">Vulnerability (f)</span>
                    <span className="item-value">{(selectedNodeDetails?.f ?? 0.0).toFixed(3)}</span>
                  </div>
                  <div className="inspector-item">
                    <span className="item-label">Consequence Weight (c)</span>
                    <span className="item-value">{(selectedNodeDetails?.c ?? 0.0).toFixed(3)}</span>
                  </div>
                  <div className="inspector-item">
                    <span className="item-label">Operational State</span>
                    <span className={`status-pill pill-${(selectedNodeState?.state || 'SAFE').toLowerCase()}`}>
                      {selectedNodeState?.state || 'SAFE'}
                    </span>
                  </div>
                  {selectedCriticalItem && (
                    <>
                      <div className="inspector-item">
                        <span className="item-label">Criticality Rank</span>
                        <span className="item-value">Rank {selectedCriticalItem.rank} (Score: {selectedCriticalItem.criticality_score.toFixed(3)})</span>
                      </div>
                      <div className="inspector-item">
                        <span className="item-label">Downstream Impact</span>
                        <span className="item-value">{selectedCriticalItem.downstream_impact.toFixed(3)}</span>
                      </div>
                    </>
                  )}
                </div>
              </div>
            )}
          </div>

          {/* Critical Node Ranking Table (Algorithm 6) */}
          <div className="dashboard-card">
            <div className="card-header-row">
              <div>
                <h3 className="card-heading-sm">Algorithm 6: Critical Node Feature Breakdown</h3>
                <p className="card-subheading">
                  All 6 max-scaled terms combined with configurable weights v = (0.15, 0.20, 0.15, 0.20, 0.20, 0.10)
                </p>
              </div>
              <span className="badge-nominal">
                {critical?.ranked_nodes.length || 0} Candidates Evaluated
              </span>
            </div>

            <div className="table-responsive">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Rank</th>
                    <th>Node ID & Asset Name</th>
                    <th>Criticality Score</th>
                    <th>Direct (p)</th>
                    <th>Pop Impact</th>
                    <th>Infra Impact</th>
                    <th>Emerg Impact</th>
                    <th>Downstream</th>
                    <th>Dep Count</th>
                  </tr>
                </thead>
                <tbody>
                  {critical?.ranked_nodes.map((node) => {
                    const isTop = node.rank === 1;
                    return (
                      <tr key={node.node_id} className={isTop ? 'row-critical-highlight' : ''}>
                        <td>
                          <span className={`rank-badge ${isTop ? 'rank-top' : ''}`}>#{node.rank}</span>
                        </td>
                        <td className="cell-primary">
                          <span className="zone-id-tag">{node.node_id}</span>
                          <span className="zone-name-text">{node.label}</span>
                          {isTop && <span className="top-crit-pill">CRITICAL NODE</span>}
                        </td>
                        <td>
                          <strong className="score-code">{node.criticality_score.toFixed(3)}</strong>
                        </td>
                        <td>{node.scaled_features?.Direct?.toFixed(2) ?? '-'}</td>
                        <td>{node.scaled_features?.Pop?.toFixed(2) ?? '-'}</td>
                        <td>{node.scaled_features?.Infra?.toFixed(2) ?? '-'}</td>
                        <td>{node.scaled_features?.Emerg?.toFixed(2) ?? '-'}</td>
                        <td>{node.scaled_features?.Downstream?.toFixed(2) ?? '-'}</td>
                        <td>{node.dependency_count}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>

          {/* Cascade-Break Point Simulation Table (Algorithm 7) */}
          <div className="dashboard-card">
            <div className="card-header-row">
              <div>
                <h3 className="card-heading-sm">Algorithm 7: Candidate Intervention Break-Point Simulation</h3>
                <p className="card-subheading">
                  Catalogue-backed actions evaluated through shared simulate() core. Ranked descending by CascadeRisk reduction.
                </p>
              </div>
              <span className="badge-nominal">
                {breakPoints?.ranked_break_points.length || 0} Actions Simulated
              </span>
            </div>

            <div className="table-responsive">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Rank</th>
                    <th>Action ID & Intervention</th>
                    <th>Target Node</th>
                    <th>Mitigation (m)</th>
                    <th>Baseline &rarr; Mitigated Risk</th>
                    <th>Abs Reduction</th>
                    <th>Rel Reduction (%)</th>
                    <th>Cascade Length</th>
                    <th>Surviving Nodes</th>
                  </tr>
                </thead>
                <tbody>
                  {breakPoints?.ranked_break_points.map((bp: BreakPointItem) => {
                    const isBest = bp.rank === 1;
                    return (
                      <tr key={bp.intervention_id} className={isBest ? 'row-best-breakpoint' : ''}>
                        <td>
                          <span className={`rank-badge ${isBest ? 'rank-top' : ''}`}>#{bp.rank}</span>
                        </td>
                        <td className="cell-primary">
                          <span className="zone-id-tag">{bp.intervention_id}</span>
                          <span className="zone-name-text">{bp.action}</span>
                          {isBest && <span className="best-breakpoint-pill">BEST BREAK POINT</span>}
                        </td>
                        <td>
                          <code className="score-code">{bp.target_node}</code>
                        </td>
                        <td>{(bp.mitigation_m * 100).toFixed(0)}%</td>
                        <td>
                          <span className="risk-transition">
                            {bp.baseline_cascade_risk.toFixed(3)} &rarr; {bp.mitigated_cascade_risk.toFixed(3)}
                          </span>
                        </td>
                        <td>
                          <strong className="reduction-abs">-{bp.impact_reduction_abs.toFixed(3)}</strong>
                        </td>
                        <td>
                          <span className="reduction-pct-pill">-{bp.impact_reduction_pct.toFixed(1)}%</span>
                        </td>
                        <td>
                          {bp.baseline_cascade_length} &rarr; <strong>{bp.mitigated_cascade_length}</strong> (-{bp.cascade_length_delta})
                        </td>
                        <td>
                          <span className="surviving-count">{bp.surviving_nodes.length} nodes protected</span>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>

          {/* Cycle Resolution Audit Log (if applicable) */}
          {cascade.cycle_logs && cascade.cycle_logs.length > 0 && (
            <div className="dashboard-card">
              <div className="card-header-row">
                <div>
                  <h3 className="card-heading-sm">Algorithm 5: Cycle Resolution Audit Log</h3>
                  <p className="card-subheading">
                    Weakest edges deterministically dropped to guarantee acyclic topological execution
                  </p>
                </div>
                <span className="badge-warning">{cascade.cycle_logs.length} Cycles Resolved</span>
              </div>
              <ul className="cycle-log-list">
                {cascade.cycle_logs.map((log, idx) => (
                  <li key={idx} className="cycle-log-item">
                    <span className="cycle-nodes">Cycle: {log.cycle.join(' &rarr; ')}</span>
                    <span className="removed-edge">Dropped Edge: {log.removed_edge[0]} &rarr; {log.removed_edge[1]} (s={log.strength.toFixed(2)})</span>
                    <span className="cycle-reason">{log.reason}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </>
      )}
    </div>
  );
};
