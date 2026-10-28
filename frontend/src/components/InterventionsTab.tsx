import React from 'react';
import type { ScenarioDetail } from '../types/api';

interface InterventionsTabProps {
  scenarioDetail: ScenarioDetail | null;
}

export const InterventionsTab: React.FC<InterventionsTabProps> = ({
  scenarioDetail,
}) => {
  return (
    <div className="tab-pane interventions-pane">
      {/* Scope Status Banner */}
      <div className="milestone-placeholder-banner">
        <div className="placeholder-banner-head">
          <span className="badge-roadmap">SCHEDULED: MILESTONE 4</span>
          <h2 className="banner-title">Intervention Optimization & Decision Support Engine</h2>
        </div>
        <p className="banner-text">
          Automated resource feasibility checking, Pareto optimization, and signed Command Decision Cards (Algorithms 10–13) will be activated in Milestone 4. No ranking or mitigation recommendations are fabricated here in Milestone 1.
        </p>
      </div>

      {/* Candidate Interventions Catalog */}
      <div className="dashboard-card">
        <div className="card-header-row">
          <div>
            <h3 className="card-heading-sm">Candidate Intervention Action Catalog</h3>
            <p className="card-subheading">
              Available tactical countermeasures evaluated during simulated flood emergencies
            </p>
          </div>
          <span className="badge-nominal">
            {scenarioDetail?.interventions.length ?? 0} Actions Loaded
          </span>
        </div>

        <div className="table-responsive">
          <table className="data-table">
            <thead>
              <tr>
                <th>Action ID & Name</th>
                <th>Category</th>
                <th>Target Zone</th>
                <th>Target Infrastructure</th>
                <th>Resource Demand</th>
                <th>Est. Cost</th>
                <th>Deployment Lead Time</th>
                <th>Attenuation Factor</th>
                <th>Decision Status</th>
              </tr>
            </thead>
            <tbody>
              {scenarioDetail?.interventions.map((intv) => (
                <tr key={intv.intervention_id}>
                  <td className="cell-primary">
                    <span className="zone-id-tag">{intv.intervention_id}</span>
                    <span className="zone-name-text">{intv.name}</span>
                  </td>
                  <td>
                    <span className="action-type-pill">{intv.intervention_type}</span>
                  </td>
                  <td>{intv.target_zone_id}</td>
                  <td>{intv.target_node_id ?? 'Catchment-wide'}</td>
                  <td>
                    <div className="resource-demand-tags">
                      {Object.entries(intv.required_resources).map(([sku, qty]) => (
                        <span key={sku} className="sku-tag">
                          {sku}: <strong>{qty}</strong>
                        </span>
                      ))}
                    </div>
                  </td>
                  <td>${intv.cost_estimate_usd.toLocaleString()}</td>
                  <td>{intv.lead_time_minutes} mins</td>
                  <td>
                    <code className="score-code">
                      -{(intv.risk_reduction_factor * 100).toFixed(0)}%
                    </code>
                  </td>
                  <td>
                    <span className="status-pending-tag">Pending M4 Optimization</span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Milestone 4 Architecture Preview */}
      <div className="pipeline-preview-card">
        <h3 className="section-title-sm">Upcoming Optimization Specifications (Algorithms 10–13)</h3>
        <div className="pipeline-steps-grid">
          <div className="pipeline-box">
            <span className="step-num">Alg 10</span>
            <span className="step-name">Resource Feasibility</span>
            <p className="step-desc">
              Deterministic verification against available depot inventories; infeasible actions are excluded.
            </p>
          </div>
          <div className="pipeline-box">
            <span className="step-num">Alg 11</span>
            <span className="step-name">Multi-Criteria Ranking</span>
            <p className="step-desc">
              Weighted Pareto scoring balancing population protected, cost, and implementation lead time.
            </p>
          </div>
          <div className="pipeline-box">
            <span className="step-num">Alg 12</span>
            <span className="step-name">What-If Simulation</span>
            <p className="step-desc">
              Comparative cascade graph rerun demonstrating unmitigated vs mitigated infrastructure survival.
            </p>
          </div>
          <div className="pipeline-box">
            <span className="step-num">Alg 13</span>
            <span className="step-name">Decision Card Synthesis</span>
            <p className="step-desc">
              Generating authoritative operational directive for Incident Command review and sign-off.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};
