import React from 'react';
import type { ScenarioDetail } from '../types/api';

interface ConsequenceGraphTabProps {
  scenarioDetail: ScenarioDetail | null;
}

export const ConsequenceGraphTab: React.FC<ConsequenceGraphTabProps> = ({
  scenarioDetail,
}) => {
  return (
    <div className="tab-pane consequence-pane">
      {/* Scope Status Banner */}
      <div className="milestone-placeholder-banner">
        <div className="placeholder-banner-head">
          <span className="badge-roadmap">SCHEDULED: MILESTONE 3</span>
          <h2 className="banner-title">Consequence Graph & Cascade Propagation Engine</h2>
        </div>
        <p className="banner-text">
          Interactive NetworkX dependency graph visualization and percolation cascade simulation (Algorithms 6–9) will be implemented in Milestone 3. In Milestone 1, the infrastructure asset contracts below are registered and ready for dependency linking.
        </p>
      </div>

      {/* Planned Cascade Pipeline Steps */}
      <div className="pipeline-preview-card">
        <h3 className="section-title-sm">Upcoming Algorithmic Pipeline (Algorithms 6–9)</h3>
        <div className="pipeline-steps-grid">
          <div className="pipeline-box">
            <span className="step-num">Alg 6</span>
            <span className="step-name">Graph Construction</span>
            <p className="step-desc">
              Directed NetworkX multigraph modeling power, water, transport, and medical interdependencies.
            </p>
          </div>
          <div className="pipeline-box">
            <span className="step-num">Alg 7</span>
            <span className="step-name">Cascade Simulation</span>
            <p className="step-desc">
              Deterministic breadth-first percolation failure propagation based on asset flood thresholds.
            </p>
          </div>
          <div className="pipeline-box">
            <span className="step-num">Alg 8</span>
            <span className="step-name">Critical Node Analysis</span>
            <p className="step-desc">
              Betweenness centrality and cascade amplification factor to isolate single-point failure hubs.
            </p>
          </div>
          <div className="pipeline-box">
            <span className="step-num">Alg 9</span>
            <span className="step-name">Intervention Break-Points</span>
            <p className="step-desc">
              Locating optimal edge cuts to prevent failure propagation to emergency shelters and hospitals.
            </p>
          </div>
        </div>
      </div>

      {/* Registered Critical Infrastructure Assets from Active Scenario */}
      <div className="dashboard-card">
        <div className="card-header-row">
          <div>
            <h3 className="card-heading-sm">Registered Critical Infrastructure Assets</h3>
            <p className="card-subheading">
              Node entities loaded from active scenario schema awaiting graph edge mapping
            </p>
          </div>
          <span className="badge-nominal">
            {scenarioDetail?.nodes.length ?? 0} Assets Registered
          </span>
        </div>

        <div className="table-responsive">
          <table className="data-table">
            <thead>
              <tr>
                <th>Node ID & Asset Name</th>
                <th>Classification</th>
                <th>Zone ID</th>
                <th>Nominal Capacity</th>
                <th>Operating Ratio</th>
                <th>Flood Threshold Depth</th>
                <th>Criticality Weight</th>
                <th>Recovery Latency</th>
              </tr>
            </thead>
            <tbody>
              {scenarioDetail?.nodes.map((node) => (
                <tr key={node.node_id}>
                  <td className="cell-primary">
                    <span className="zone-id-tag">{node.node_id}</span>
                    <span className="zone-name-text">{node.name}</span>
                  </td>
                  <td>
                    <span className="node-type-pill">{node.node_type}</span>
                  </td>
                  <td>{node.zone_id}</td>
                  <td>{node.baseline_capacity.toLocaleString()} units</td>
                  <td>
                    <span
                      className={`ratio-pill ${
                        node.current_operational_ratio < 0.6
                          ? 'ratio-danger'
                          : node.current_operational_ratio < 0.9
                          ? 'ratio-warn'
                          : 'ratio-good'
                      }`}
                    >
                      {(node.current_operational_ratio * 100).toFixed(0)}%
                    </span>
                  </td>
                  <td>
                    <code className="score-code">{node.flood_threshold_m.toFixed(1)} m</code>
                  </td>
                  <td>{node.criticality_weight.toFixed(2)}</td>
                  <td>
                    {node.recovery_latency_hours ? `${node.recovery_latency_hours} hrs` : 'TBD'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
