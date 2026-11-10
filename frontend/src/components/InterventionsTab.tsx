import React from 'react';
import { Activity, AlertTriangle, CheckCircle2, Info, Package, ShieldCheck } from 'lucide-react';
import type {
  ScenarioDetail,
  ScenarioAnalysisResponse,
  FeasibleIntervention,
  InfeasibleIntervention,
  ComparisonRow,
  DecisionCardResult,
  ResourceAllocationResult,
  WhatIfAnalysisResult,
} from '../types/api';

interface InterventionsTabProps {
  scenarioDetail?: ScenarioDetail | null;
  analysisResult: ScenarioAnalysisResponse | null;
  isAnalyzing?: boolean;
  analysisError?: string | null;
  onRunAnalysis?: () => void;
}

function fmt(value: number, decimals = 3): string {
  return value.toFixed(decimals);
}

function pct(value: number): string {
  return `${(value * 100).toFixed(1)}%`;
}

function ResourceTags({ resources }: { resources: Record<string, number> }) {
  const entries = Object.entries(resources);
  if (!entries.length) return <span className="m7-muted-value">None recorded</span>;
  return (
    <div className="m7-resource-tags">
      {entries.map(([resource, quantity]) => (
        <span key={resource}><strong>{resource}</strong>{quantity}</span>
      ))}
    </div>
  );
}

const ResourceAllocationPanel: React.FC<{ data: ResourceAllocationResult }> = ({ data }) => {
  const unmet = data.unmet_demand.filter((item) => item.granted < item.needed);
  const inventoryEntries = Object.entries(data.remaining_inventory);

  return (
    <section className="dashboard-card m7-card">
      <div className="card-header-row m7-card-header">
        <div>
          <span className="m7-card-kicker">Algorithm 8</span>
          <h3>Resource allocation</h3>
          <p>Backend-ranked zone priority and depot inventory allocation.</p>
        </div>
        <span className={`m7-status-pill ${data.status === 'SUCCESS' ? 'm7-success' : 'm7-warning'}`}>
          {data.status}
        </span>
      </div>

      <div className="m7-resource-layout">
        <div className="m7-resource-column">
          <div className="m7-panel-label">Allocation priority</div>
          <div className="m7-allocation-order">
            {data.zone_allocation_order.map((zoneId, index) => (
              <div className="m7-allocation-row" key={zoneId}>
                <span className="m7-rank-number">{index + 1}</span>
                <div><strong>{zoneId}</strong><small>Priority score</small></div>
                <code>{fmt(data.priority_scores[zoneId] ?? 0, 4)}</code>
              </div>
            ))}
            {!data.zone_allocation_order.length && <div className="m7-empty-inline">No allocation priority data.</div>}
          </div>
        </div>

        <div className="m7-resource-column m7-zone-budget">
          <div className="m7-panel-label">Zone grants</div>
          <div className="m7-budget-list">
            {data.zone_allocation_order.map((zoneId) => {
              const budget = data.zone_budgets[zoneId];
              return (
                <div className="m7-budget-row" key={zoneId}>
                  <strong>{zoneId}</strong>
                  {budget ? <ResourceTags resources={budget} /> : <span className="m7-muted-value">No grant recorded</span>}
                </div>
              );
            })}
            {!data.zone_allocation_order.length && <div className="m7-empty-inline">No zone budgets returned.</div>}
          </div>
        </div>

        <div className="m7-resource-column">
          <div className="m7-panel-label">Remaining inventory</div>
          {inventoryEntries.length ? (
            <div className="m7-inventory-grid">
              {inventoryEntries.map(([resource, quantity]) => (
                <div key={resource}><span>{resource}</span><strong>{quantity}</strong></div>
              ))}
            </div>
          ) : <div className="m7-empty-inline">No inventory values returned.</div>}
        </div>
      </div>

      <div className={`m7-demand-summary ${unmet.length ? 'has-unmet' : ''}`}>
        <div><AlertTriangle size={18} /><strong>{unmet.length ? 'Unmet demand' : 'Demand status'}</strong></div>
        {unmet.length ? (
          <div className="m7-demand-list">
            {unmet.map((item, index) => (
              <div key={`${item.zone_id}-${item.resource_type}-${index}`}>
                <strong>{item.zone_id}</strong>
                <span>{item.resource_type}</span>
                <code>needed {item.needed} · granted {item.granted}</code>
                <em>{item.status}</em>
              </div>
            ))}
          </div>
        ) : <span>No unmet demand is recorded in the allocation result.</span>}
      </div>
    </section>
  );
};

const InterventionRankingPanel: React.FC<{
  feasible: FeasibleIntervention[];
  infeasible: InfeasibleIntervention[];
  nugenRecommended: string | null;
}> = ({ feasible, infeasible, nugenRecommended }) => {
  const maxScore = feasible.length ? Math.max(...feasible.map((item) => item.score)) : 1;

  return (
    <section className="dashboard-card m7-card">
      <div className="card-header-row m7-card-header">
        <div>
          <span className="m7-card-kicker">Algorithm 10</span>
          <h3>Intervention ranking</h3>
          <p>Deterministic backend ranking with feasibility verification.</p>
        </div>
        <span className="m7-count-pill">{feasible.length} feasible · {infeasible.length} infeasible</span>
      </div>

      {feasible.length ? (
        <div className="m7-ranking-list">
          {feasible.map((item, index) => {
            const barWidth = maxScore > 0 ? (item.score / maxScore) * 100 : 0;
            const isModelTop = index === 0;
            const isNugenPick = item.intervention_id === nugenRecommended;
            return (
              <article className={`m7-ranking-row ${isModelTop ? 'is-recommended' : ''}`} key={item.intervention_id}>
                <div className="m7-ranking-heading">
                  <span className="m7-rank-number">{index + 1}</span>
                  <div className="m7-ranking-title">
                    <strong>{item.name || item.action}</strong>
                    <div><code>{item.intervention_id}</code><span>Target {item.target_node || 'Not specified'}</span></div>
                  </div>
                  <div className="m7-score-block">
                    <span>Model score</span>
                    <strong>{fmt(item.score, 4)}</strong>
                  </div>
                </div>
                <div className="m7-score-track"><span style={{ width: `${barWidth}%` }} /></div>
                <div className="m7-ranking-badges">
                  {isModelTop && <span className="m7-model-tag"><CheckCircle2 size={12} />Model top-ranked</span>}
                  {isNugenPick && <span className="m7-advisory-tag">Nugen advisory match</span>}
                  <span className="m7-feasible-tag">Feasible</span>
                </div>
                <div className="m7-measure-grid">
                  <div><span>Risk reduction</span><strong>{pct(item.measures.risk_reduction)}</strong></div>
                  <div><span>Cascade reduction</span><strong>{pct(item.measures.cascade_reduction)}</strong></div>
                  <div><span>Population protected</span><strong>{pct(item.measures.population_protection)}</strong></div>
                  <div><span>Emergency protected</span><strong>{pct(item.measures.emergency_protection)}</strong></div>
                  <div><span>Resource cost</span><strong>{pct(item.measures.resource_cost)}</strong></div>
                </div>
                <div className="m7-ranking-meta">
                  {item.cost_usd != null && <span>Cost <strong>${item.cost_usd.toLocaleString()}</strong></span>}
                  {item.lead_time_minutes != null && <span>Lead time <strong>{item.lead_time_minutes} min</strong></span>}
                  <div><span>Required resources</span><ResourceTags resources={item.required_resources} /></div>
                </div>
              </article>
            );
          })}
        </div>
      ) : (
        <div className="m7-empty-inline m7-empty-section">No feasible interventions were returned.</div>
      )}

      {infeasible.length > 0 && (
        <div className="m7-infeasible-list">
          <div className="m7-panel-label">Feasibility blockers</div>
          {infeasible.map((item) => (
            <div className="m7-infeasible-row" key={item.intervention_id}>
              <div><strong>{item.name || item.action}</strong><code>{item.intervention_id}</code></div>
              <ul>{item.blockers.map((blocker, index) => <li key={`${blocker}-${index}`}>{blocker}</li>)}</ul>
              {!!Object.keys(item.required_resources).length && (
                <div><span>Required resources</span><ResourceTags resources={item.required_resources} /></div>
              )}
            </div>
          ))}
        </div>
      )}
    </section>
  );
};

type WhatIfKey = 'impact_index' | 'cascade_length' | 'population_risk' | 'infrastructure_risk' | 'emergency_delay';

const WhatIfPanel: React.FC<{ data: WhatIfAnalysisResult }> = ({ data }) => {
  const rows: { key: WhatIfKey; label: string; isInt?: boolean }[] = [
    { key: 'impact_index', label: 'Impact index' },
    { key: 'cascade_length', label: 'Cascade length', isInt: true },
    { key: 'population_risk', label: 'Population risk' },
    { key: 'infrastructure_risk', label: 'Infrastructure risk' },
    { key: 'emergency_delay', label: 'Emergency delay' },
  ];

  return (
    <section className="dashboard-card m7-card">
      <div className="card-header-row m7-card-header">
        <div><span className="m7-card-kicker">Algorithm 11</span><h3>What-if comparison</h3><p>Baseline and selected intervention simulated separately; baseline data is not mutated.</p></div>
      </div>
      <div className="table-responsive">
        <table className="data-table m7-table">
          <thead><tr><th>Measure</th><th>Baseline</th><th>Selected intervention</th><th>Absolute change</th><th>Relative reduction</th></tr></thead>
          <tbody>
            {rows.map(({ key, label, isInt }) => {
              const before = data.before[key];
              const after = data.after[key];
              const reduction = data.reductions[key];
              return (
                <tr key={key}>
                  <td><strong>{label}</strong></td>
                  <td><code>{isInt ? before : fmt(before)}</code></td>
                  <td><code>{isInt ? after : fmt(after)}</code></td>
                  <td>{reduction ? (isInt ? fmt(reduction.absolute, 0) : fmt(reduction.absolute)) : 'Not returned'}</td>
                  <td>{reduction ? <span className="m7-reduction">{pct(reduction.relative)}</span> : 'Not returned'}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </section>
  );
};

const AlternativeComparisonPanel: React.FC<{ noAction: ComparisonRow; rows: ComparisonRow[] }> = ({ noAction, rows }) => {
  const allRows = [noAction, ...rows];
  return (
    <section className="dashboard-card m7-card">
      <div className="card-header-row m7-card-header">
        <div><span className="m7-card-kicker">Algorithm 12</span><h3>Alternative comparison</h3><p>Top alternatives compared against the no-action baseline.</p></div>
      </div>
      <div className="table-responsive">
        <table className="data-table m7-table">
          <thead><tr><th>Action</th><th>Score</th><th>Impact index</th><th>Cascade length</th><th>Population risk</th><th>Infrastructure risk</th><th>Emergency delay</th><th>Population saved</th><th>Infrastructure protected</th><th>Resource cost</th></tr></thead>
          <tbody>
            {allRows.map((row) => {
              const isBaseline = row.intervention_id === 'NO_ACTION';
              return (
                <tr key={row.intervention_id} className={isBaseline ? 'm7-baseline-row' : ''}>
                  <td><strong>{row.action_name}</strong><small className="m7-table-code">{row.intervention_id}</small>{isBaseline && <span className="m7-baseline-tag">Baseline</span>}</td>
                  <td><code>{isBaseline ? 'Not applicable' : fmt(row.score, 4)}</code></td>
                  <td><code>{fmt(row.impact_index)}</code></td><td>{row.cascade_length}</td>
                  <td>{fmt(row.population_risk)}</td><td>{fmt(row.infrastructure_risk)}</td><td>{fmt(row.emergency_delay)}</td>
                  <td>{isBaseline ? 'Not applicable' : fmt(row.population_saved)}</td>
                  <td>{isBaseline ? 'Not applicable' : fmt(row.infrastructure_protected)}</td>
                  <td>{isBaseline ? 'Not applicable' : pct(row.resource_cost)}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </section>
  );
};

const DecisionCardPanel: React.FC<{ card: DecisionCardResult }> = ({ card }) => {
  const isFeasible = card.status === 'FEASIBLE';
  return (
    <section className={`dashboard-card m7-card m7-decision-card ${isFeasible ? 'm7-decision-feasible' : 'm7-decision-fallback'}`}>
      <div className="card-header-row m7-card-header">
        <div><span className="m7-card-kicker">Algorithm 13</span><h3>Command decision card</h3><p>Deterministic model output for human review and verification.</p></div>
        <span className={`m7-status-pill ${isFeasible ? 'm7-success' : 'm7-danger'}`}>{card.status}</span>
      </div>

      <div className="m7-human-review"><ShieldCheck size={18} /><div><strong>Human review required</strong><span>{card.human_review_warning || 'This recommendation requires operator verification before action.'}</span></div></div>

      {isFeasible ? (
        <div className="m7-decision-grid">
          <div className="m7-decision-primary">
            <span className="m7-panel-label">Recommended intervention</span>
            <h4>{card.action || card.intervention_id || 'Intervention selected'}</h4>
            {card.intervention_id && <code>{card.intervention_id}</code>}
            <dl>
              <div><dt>Zone</dt><dd>{card.zone_id}</dd></div>
              <div><dt>Target node</dt><dd>{card.target_node || 'Not specified'}</dd></div>
              <div><dt>Priority</dt><dd>{card.priority}</dd></div>
              <div><dt>Modelled relative change</dt><dd>{card.modelled_relative_change != null ? pct(card.modelled_relative_change) : 'Not returned'}</dd></div>
            </dl>
            <div className="m7-decision-resources"><span>Required resources</span><ResourceTags resources={card.required_resources} /></div>
          </div>
          <div className="m7-decision-support">
            {card.expected_impact && (
              <div className="m7-support-block">
                <span className="m7-panel-label">Expected impact</span>
                <div><span>Impact index</span><strong><code>{fmt(card.expected_impact.before.impact_index)}</code> → <code>{fmt(card.expected_impact.after.impact_index)}</code></strong></div>
                <div><span>Cascade length</span><strong><code>{card.expected_impact.before.cascade_length}</code> → <code>{card.expected_impact.after.cascade_length}</code></strong></div>
                <div><span>Population risk</span><strong><code>{fmt(card.expected_impact.before.population_risk)}</code> → <code>{fmt(card.expected_impact.after.population_risk)}</code></strong></div>
              </div>
            )}
            <div className="m7-support-block">
              <span className="m7-panel-label">Verification</span>
              {card.quality_flags.length ? <div className="m7-quality-flags">{card.quality_flags.map((flag) => <span key={flag}>{flag}</span>)}</div> : <span className="m7-muted-value">No quality flags returned</span>}
              <div className="m7-run-info"><span>Run ID</span><code>{card.run_id}</code></div>
            </div>
            <div className="m7-nugen-block">
              <div className="m7-nugen-header">
                <span className="m7-panel-label">Nugen advisory</span>
                <span className={`m7-advisory-badge m7-advisory-${card.ai_status.toLowerCase()}`}>
                  {card.ai_status === 'MOCK' ? 'ADVISORY: MOCK' : card.ai_status === 'LIVE' ? 'ADVISORY: LIVE' : card.ai_status === 'FALLBACK' ? 'ADVISORY: FALLBACK' : `ADVISORY: ${card.ai_status}`}
                </span>
              </div>
              <p>{card.nugen_recommendation ? `Nugen recommendation: ${card.nugen_recommendation}` : 'No Nugen recommendation returned.'}</p>
              {card.nugen_agreement !== null && (
                <span className={`m7-agreement-tag ${card.nugen_agreement ? 'agrees' : 'differs'}`}>
                  {card.nugen_agreement ? '✓ Matches deterministic model selection' : '⚠ Differs from deterministic model selection'}
                </span>
              )}
              <small className="m7-advisory-disclaimer">Non-authoritative AI advice. Algorithms 0–13 remain authoritative.</small>
            </div>
            <div className="m7-decision-reason"><span className="m7-panel-label">Decision rationale</span><p>{card.reason}</p></div>
          </div>
        </div>
      ) : (
        <div className="m7-fallback-content">
          <strong>No feasible intervention passed final verification.</strong>
          <p>{card.reason}</p>
          {!!card.blockers.length && <div><span className="m7-panel-label">Blockers</span><ul>{card.blockers.map((blocker, index) => <li key={`${blocker}-${index}`}>{blocker}</li>)}</ul></div>}
          {!!card.rejected_candidates.length && <div><span className="m7-panel-label">Rejected candidates</span>{card.rejected_candidates.map((candidate) => <article key={candidate.intervention_id}><strong>{candidate.intervention_id}</strong><ul>{candidate.blockers.map((blocker, index) => <li key={`${blocker}-${index}`}>{blocker}</li>)}</ul></article>)}</div>}
          <div className="m7-nugen-block">
            <div className="m7-nugen-header">
              <span className="m7-panel-label">Nugen advisory</span>
              <span className={`m7-advisory-badge m7-advisory-${card.ai_status.toLowerCase()}`}>
                {card.ai_status === 'MOCK' ? 'ADVISORY: MOCK' : `ADVISORY: ${card.ai_status}`}
              </span>
            </div>
            <p>{card.nugen_recommendation || 'No Nugen recommendation returned.'}</p>
            <small className="m7-advisory-disclaimer">Non-authoritative AI advice. Algorithms 0–13 remain authoritative.</small>
          </div>
        </div>
      )}
    </section>
  );
};

export const InterventionsTab: React.FC<InterventionsTabProps> = ({
  scenarioDetail,
  analysisResult,
  isAnalyzing = false,
  analysisError = null,
  onRunAnalysis,
}) => {
  const resourceAlloc = analysisResult?.resource_allocation ?? null;
  const ranking = analysisResult?.intervention_ranking ?? null;
  const whatIf = analysisResult?.what_if_analysis ?? null;
  const altComp = analysisResult?.alternative_comparison ?? null;
  const decCard = analysisResult?.decision_card ?? null;
  const hasM7Data = !!(resourceAlloc || ranking || whatIf || altComp || decCard);
  const isMonitoringOnly = !!analysisResult?.is_monitoring_only || analysisResult?.pipeline_status === 'MONITORING_ONLY';
  const isDataInsufficient = analysisResult?.pipeline_status === 'DATA_INSUFFICIENT';

  const rankingNugenId = ranking?.nugen_recommendation && typeof ranking.nugen_recommendation.recommended_action === 'string'
    ? ranking.nugen_recommendation.recommended_action
    : null;

  return (
    <div className="tab-pane redesigned-section m7-section">
      <div className="section-page-header">
        <div>
          <span className="section-eyebrow">Decision support</span>
          <h2 className="section-title">Interventions</h2>
          <p className="section-description">Resource feasibility, intervention comparison, and model-derived next steps.</p>
        </div>
        <div className={`analysis-status-chip ${isAnalyzing ? 'status-running' : analysisError || isDataInsufficient ? 'status-alert' : isMonitoringOnly ? 'status-monitoring' : analysisResult ? 'status-ready' : 'status-awaiting'}`}>
          <span className="status-dot" />
          {isAnalyzing ? 'Analysis running' : analysisError ? 'Analysis error' : isDataInsufficient ? 'Data insufficient' : isMonitoringOnly ? 'Monitoring only' : analysisResult ? 'Analysis complete' : 'Awaiting analysis'}
        </div>
      </div>

      <div className="scenario-context-strip">
        <div><span className="context-label">Active scenario</span><strong>{scenarioDetail?.name || 'No scenario selected'}</strong></div>
        <div><span className="context-label">Data quality</span><strong>{analysisResult?.data_label || scenarioDetail?.data_label || 'Unavailable'}</strong></div>
        <div><span className="context-label">Pipeline status</span><strong>{analysisResult?.pipeline_status || 'NOT_RUN'}</strong></div>
      </div>

      {isAnalyzing && <div className="redesign-state-card loading-state"><Activity size={22} /><div><strong>Running intervention analysis</strong><span>Resource allocation and deterministic decision results are being calculated.</span></div></div>}
      {analysisError && <div className="redesign-state-card error-state"><AlertTriangle size={22} /><div><strong>Analysis could not be completed</strong><span>{analysisError}</span></div></div>}

      {!analysisResult && !isAnalyzing && (
        <div className="redesign-state-card m7-awaiting">
          <Package size={22} />
          <div><strong>Intervention optimization awaiting execution</strong><span>Run flood analysis to evaluate resources, ranked actions, simulations, and the decision card.</span></div>
          {onRunAnalysis && <button type="button" className="btn btn-primary" onClick={onRunAnalysis} disabled={isAnalyzing}>Run flood analysis</button>}
        </div>
      )}

      {isDataInsufficient && (
        <div className="redesign-state-card error-state"><AlertTriangle size={22} /><div><strong>DATA_INSUFFICIENT</strong><span>Required telemetry is missing. Intervention allocations and recommendations are not fabricated.</span></div></div>
      )}

      {analysisResult && isMonitoringOnly && (
        <div className="redesign-state-card monitoring-state"><Info size={22} /><div><strong>Monitoring-only state</strong><span>No qualifying hotspots were found, so tactical intervention algorithms are bypassed.</span></div></div>
      )}

      {analysisResult && !isMonitoringOnly && !isDataInsufficient && !hasM7Data && (
        <div className="redesign-state-card empty-state"><Package size={22} /><div><strong>Decision support data unavailable</strong><span>The analysis completed without resource, ranking, simulation, comparison, or decision-card data.</span></div></div>
      )}

      {analysisResult && !isMonitoringOnly && !isDataInsufficient && hasM7Data && (
        <>
          <div className="m7-data-notice"><Info size={15} /><span>Synthetic or illustrative prototype data may be present. Deterministic results require human review and are not autonomous commands.</span></div>
          {resourceAlloc && <ResourceAllocationPanel data={resourceAlloc} />}
          {ranking && <InterventionRankingPanel feasible={ranking.feasible} infeasible={ranking.infeasible} nugenRecommended={rankingNugenId} />}
          {whatIf && <WhatIfPanel data={whatIf} />}
          {altComp && <AlternativeComparisonPanel noAction={altComp.no_action_baseline} rows={altComp.rows} />}
          {decCard && <DecisionCardPanel card={decCard} />}
        </>
      )}
    </div>
  );
};
