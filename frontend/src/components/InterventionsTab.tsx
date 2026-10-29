import React from 'react';
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

// ── Helpers ──────────────────────────────────────────────────────────────────

function pct(value: number): string {
  return `${(value * 100).toFixed(1)}%`;
}

function fmt(value: number, decimals = 3): string {
  return value.toFixed(decimals);
}

function resourceTags(resources: Record<string, number>): React.ReactNode {
  return Object.entries(resources).map(([sku, qty]) => (
    <span key={sku} className="sku-tag">
      {sku}: <strong>{qty}</strong>
    </span>
  ));
}

// ── Sub-components ────────────────────────────────────────────────────────────

const DataDisclaimer: React.FC = () => (
  <div className="data-disclaimer-bar" style={{ marginBottom: '1rem', padding: '0.5rem 1rem', background: '#1a1a2e', borderLeft: '4px solid #f59e0b', borderRadius: '4px' }}>
    <strong style={{ color: '#f59e0b' }}>⚠ SYNTHETIC / ILLUSTRATIVE DATA ONLY</strong>
    <span style={{ color: '#9ca3af', marginLeft: '0.75rem', fontSize: '0.85rem' }}>
      All values are produced by a prototype model using simulated zone data. Not for operational use.
    </span>
  </div>
);

// ── Resource Allocation Panel ─────────────────────────────────────────────────

const ResourceAllocationPanel: React.FC<{ data: ResourceAllocationResult }> = ({ data }) => {
  const primaryZone = data.zone_allocation_order[0];
  const budget = primaryZone ? data.zone_budgets[primaryZone] : null;
  const score = primaryZone ? data.priority_scores[primaryZone] : null;

  return (
    <div className="dashboard-card" style={{ marginBottom: '1.5rem' }}>
      <div className="card-header-row">
        <div>
          <h3 className="card-heading-sm">Algorithm 8 — Resource Priority & Depot Allocation</h3>
          <p className="card-subheading">
            Zones ranked by PriorityScore; depot resources granted greedily in descending order.
          </p>
        </div>
        <span className={`badge-${data.status === 'SUCCESS' ? 'nominal' : 'warn'}`}>
          {data.status}
        </span>
      </div>

      {/* Allocation order */}
      <div style={{ marginBottom: '1rem' }}>
        <strong style={{ color: '#9ca3af', fontSize: '0.8rem' }}>ALLOCATION ORDER</strong>
        <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap', marginTop: '0.4rem' }}>
          {data.zone_allocation_order.map((zid, i) => (
            <span key={zid} className="zone-id-tag">
              {i + 1}. {zid} — score: {fmt(data.priority_scores[zid] ?? 0, 4)}
            </span>
          ))}
        </div>
      </div>

      {/* Budget table */}
      {primaryZone && budget && (
        <div style={{ marginBottom: '1rem' }}>
          <strong style={{ color: '#9ca3af', fontSize: '0.8rem' }}>
            GRANTED BUDGET — {primaryZone}
            {score !== null && (
              <span style={{ marginLeft: '0.5rem', color: '#6b7280' }}>
                (PriorityScore: {fmt(score, 4)})
              </span>
            )}
          </strong>
          <div className="table-responsive" style={{ marginTop: '0.4rem' }}>
            <table className="data-table">
              <thead>
                <tr>
                  <th>Resource Type</th>
                  <th>Granted</th>
                  <th>Remaining in Depot</th>
                </tr>
              </thead>
              <tbody>
                {Object.entries(budget).map(([resource, granted]) => (
                  <tr key={resource}>
                    <td>{resource}</td>
                    <td>
                      <code className="score-code">{granted}</code>
                    </td>
                    <td>{data.remaining_inventory[resource] ?? 0}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Unmet demand warnings */}
      {data.unmet_demand.filter(u => u.needed > u.granted).length > 0 && (
        <div style={{ background: '#1f1515', border: '1px solid #7f1d1d', borderRadius: '6px', padding: '0.75rem', marginTop: '0.5rem' }}>
          <strong style={{ color: '#f87171', fontSize: '0.85rem' }}>⚠ UNMET DEMAND</strong>
          <ul style={{ margin: '0.4rem 0 0', paddingLeft: '1.2rem', color: '#fca5a5', fontSize: '0.85rem' }}>
            {data.unmet_demand.filter(u => u.needed > u.granted).map((u, i) => (
              <li key={i}>
                {u.zone_id}: {u.resource_type} — need {u.needed}, granted {u.granted} ({u.status})
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
};

// ── Intervention Ranking Panel ────────────────────────────────────────────────

const InterventionRankingPanel: React.FC<{
  feasible: FeasibleIntervention[];
  infeasible: InfeasibleIntervention[];
  nugenRecommended: string | null;
}> = ({ feasible, infeasible, nugenRecommended }) => {
  const maxScore = feasible.length > 0 ? Math.max(...feasible.map(f => f.score)) : 1;

  return (
    <div className="dashboard-card" style={{ marginBottom: '1.5rem' }}>
      <div className="card-header-row">
        <div>
          <h3 className="card-heading-sm">Algorithm 10 — Intervention Priority Ranking</h3>
          <p className="card-subheading">
            Multi-criteria score: 30% RiskRed + 25% CascRed + 20% PopProt + 15% EmergProt − 10% Cost
          </p>
        </div>
        <span className="badge-nominal">{feasible.length} feasible</span>
      </div>

      {/* Feasible interventions */}
      {feasible.length > 0 && (
        <div style={{ marginBottom: '1rem' }}>
          <strong style={{ color: '#9ca3af', fontSize: '0.8rem' }}>FEASIBLE — RANKED</strong>
          {feasible.map((f, i) => {
            const barWidth = maxScore > 0 ? (f.score / maxScore) * 100 : 0;
            const isNugenPick = f.intervention_id === nugenRecommended;
            return (
              <div key={f.intervention_id} style={{
                background: '#111827',
                border: i === 0 ? '1px solid #22c55e' : '1px solid #374151',
                borderRadius: '6px',
                padding: '0.75rem 1rem',
                marginTop: '0.5rem',
              }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.4rem' }}>
                  <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
                    <span className="zone-id-tag" style={{ background: i === 0 ? '#14532d' : '#1f2937' }}>
                      #{i + 1} {f.intervention_id}
                    </span>
                    <span style={{ color: '#e5e7eb', fontSize: '0.9rem', fontWeight: 600 }}>{f.name}</span>
                    {isNugenPick && (
                      <span style={{ background: '#1e3a5f', color: '#60a5fa', padding: '0.1rem 0.5rem', borderRadius: '999px', fontSize: '0.75rem' }}>
                        🤖 AI Pick
                      </span>
                    )}
                    {i === 0 && !isNugenPick && (
                      <span style={{ background: '#14532d', color: '#86efac', padding: '0.1rem 0.5rem', borderRadius: '999px', fontSize: '0.75rem' }}>
                        ✓ Model Top-Ranked
                      </span>
                    )}
                  </div>
                  <code className="score-code">{fmt(f.score, 4)}</code>
                </div>

                {/* Score bar */}
                <div style={{ height: '4px', background: '#374151', borderRadius: '2px', marginBottom: '0.5rem' }}>
                  <div style={{ height: '100%', width: `${barWidth}%`, background: i === 0 ? '#22c55e' : '#3b82f6', borderRadius: '2px', transition: 'width 0.5s ease' }} />
                </div>

                {/* Measures grid */}
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: '0.5rem', fontSize: '0.78rem', color: '#9ca3af' }}>
                  <div><div style={{ color: '#6ee7b7' }}>{pct(f.measures.risk_reduction)}</div>RiskRed</div>
                  <div><div style={{ color: '#93c5fd' }}>{pct(f.measures.cascade_reduction)}</div>CascRed</div>
                  <div><div style={{ color: '#c4b5fd' }}>{pct(f.measures.population_protection)}</div>PopProt</div>
                  <div><div style={{ color: '#fcd34d' }}>{pct(f.measures.emergency_protection)}</div>EmergProt</div>
                  <div><div style={{ color: '#f87171' }}>{pct(f.measures.resource_cost)}</div>Cost</div>
                </div>

                {/* Resources & meta */}
                <div style={{ marginTop: '0.5rem', display: 'flex', gap: '0.75rem', flexWrap: 'wrap', fontSize: '0.78rem', color: '#6b7280' }}>
                  <span>🎯 {f.target_node}</span>
                  {f.cost_usd && <span>💰 ${f.cost_usd.toLocaleString()}</span>}
                  {f.lead_time_minutes && <span>⏱ {f.lead_time_minutes} min</span>}
                  <div className="resource-demand-tags">{resourceTags(f.required_resources)}</div>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Infeasible interventions */}
      {infeasible.length > 0 && (
        <div>
          <strong style={{ color: '#9ca3af', fontSize: '0.8rem' }}>INFEASIBLE (resource shortfall)</strong>
          {infeasible.map(inf => (
            <div key={inf.intervention_id} style={{
              background: '#1a0a0a',
              border: '1px solid #7f1d1d',
              borderRadius: '6px',
              padding: '0.6rem 1rem',
              marginTop: '0.4rem',
            }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span className="zone-id-tag" style={{ background: '#450a0a', color: '#fca5a5' }}>{inf.intervention_id}</span>
                <span style={{ color: '#e5e7eb', fontSize: '0.85rem' }}>{inf.name}</span>
              </div>
              <ul style={{ margin: '0.3rem 0 0', paddingLeft: '1.2rem', color: '#f87171', fontSize: '0.78rem' }}>
                {inf.blockers.map((b, i) => <li key={i}>{b}</li>)}
              </ul>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

// ── What-If Before/After Panel ────────────────────────────────────────────────

type WhatIfKey = 'impact_index' | 'cascade_length' | 'population_risk' | 'infrastructure_risk' | 'emergency_delay';

interface WhatIfRowDef {
  key: WhatIfKey;
  label: string;
  color: string;
  isInt?: boolean;
}

const WhatIfPanel: React.FC<{ data: WhatIfAnalysisResult }> = ({ data }) => {
  const rows: WhatIfRowDef[] = [
    { key: 'impact_index', label: 'Impact Index (CascadeRisk)', color: '#f87171' },
    { key: 'cascade_length', label: 'Cascade Length (failing nodes)', color: '#fb923c', isInt: true },
    { key: 'population_risk', label: 'Population Risk (p_Pop)', color: '#c4b5fd' },
    { key: 'infrastructure_risk', label: 'Infrastructure Risk (weighted avg)', color: '#93c5fd' },
    { key: 'emergency_delay', label: 'Emergency Delay Proxy (p_Emerg)', color: '#fcd34d' },
  ];

  return (
    <div className="dashboard-card" style={{ marginBottom: '1.5rem' }}>
      <h3 className="card-heading-sm" style={{ marginBottom: '0.25rem' }}>
        Algorithm 11 — What-If Simulation (Before / After)
      </h3>
      <p className="card-subheading" style={{ marginBottom: '1rem' }}>
        Paired baseline + top-ranked intervention runs via shared simulate(). Graph is not mutated.
      </p>

      <div className="table-responsive">
        <table className="data-table">
          <thead>
            <tr>
              <th>Measure</th>
              <th>Before (Baseline)</th>
              <th>After (Intervention)</th>
              <th>Abs Δ</th>
              <th>Rel Reduction</th>
            </tr>
          </thead>
          <tbody>
            {rows.map(({ key, label, color, isInt }) => {
              const before = data.before[key as keyof typeof data.before] as number;
              const after = data.after[key as keyof typeof data.after] as number;
              const red = data.reductions[key];
              return (
                <tr key={key}>
                  <td style={{ color, fontWeight: 500 }}>{label}</td>
                  <td><code className="score-code">{isInt ? before : fmt(before)}</code></td>
                  <td><code className="score-code">{isInt ? after : fmt(after)}</code></td>
                  <td style={{ color: '#6ee7b7' }}>
                    {red ? (isInt ? Math.round(red.absolute) : fmt(red.absolute)) : '—'}
                  </td>
                  <td>
                    {red ? (
                      <span style={{
                        color: red.relative > 0 ? '#22c55e' : '#9ca3af',
                        fontWeight: 600,
                      }}>
                        {pct(red.relative)}
                      </span>
                    ) : '—'}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
};

// ── Alternative Comparison Table ──────────────────────────────────────────────

const AlternativeComparisonPanel: React.FC<{
  noAction: ComparisonRow;
  rows: ComparisonRow[];
}> = ({ noAction, rows }) => {
  const allRows = [noAction, ...rows];

  return (
    <div className="dashboard-card" style={{ marginBottom: '1.5rem' }}>
      <h3 className="card-heading-sm" style={{ marginBottom: '0.25rem' }}>
        Algorithm 12 — Alternative Intervention Comparison
      </h3>
      <p className="card-subheading" style={{ marginBottom: '1rem' }}>
        Top-K feasible alternatives vs. no-action baseline, all derived from shared simulate().
      </p>

      <div className="table-responsive">
        <table className="data-table">
          <thead>
            <tr>
              <th>Action</th>
              <th>Score</th>
              <th>Impact Index</th>
              <th>Cascade Len</th>
              <th>Pop Risk</th>
              <th>Infra Risk</th>
              <th>Emerg Delay</th>
              <th>Pop Saved</th>
              <th>Infra Protected</th>
              <th>Resource Cost</th>
            </tr>
          </thead>
          <tbody>
            {allRows.map((row, i) => {
              const isNoAction = row.intervention_id === 'NO_ACTION';
              return (
                <tr key={row.intervention_id} style={i === 1 ? { background: '#0d1f15' } : {}}>
                  <td className="cell-primary">
                    <span className="zone-id-tag" style={isNoAction ? { background: '#374151' } : {}}>
                      {row.intervention_id}
                    </span>
                    <span className="zone-name-text">{row.action_name}</span>
                  </td>
                  <td>
                    <code className="score-code">{isNoAction ? '—' : fmt(row.score, 4)}</code>
                  </td>
                  <td>{fmt(row.impact_index)}</td>
                  <td>{row.cascade_length}</td>
                  <td>{fmt(row.population_risk)}</td>
                  <td>{fmt(row.infrastructure_risk)}</td>
                  <td>{fmt(row.emergency_delay)}</td>
                  <td style={{ color: '#6ee7b7' }}>{isNoAction ? '—' : fmt(row.population_saved)}</td>
                  <td style={{ color: '#93c5fd' }}>{isNoAction ? '—' : fmt(row.infrastructure_protected)}</td>
                  <td>{isNoAction ? '—' : pct(row.resource_cost)}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
};

// ── Command Decision Card ─────────────────────────────────────────────────────

const DecisionCardPanel: React.FC<{ card: DecisionCardResult }> = ({ card }) => {
  const isFeasible = card.status === 'FEASIBLE';

  return (
    <div className="dashboard-card" style={{
      border: isFeasible ? '2px solid #22c55e' : '2px solid #ef4444',
      marginBottom: '1.5rem',
    }}>
      <div className="card-header-row" style={{ marginBottom: '0.75rem' }}>
        <div>
          <h3 className="card-heading-sm">Algorithm 13 — Command Decision Card</h3>
          <p className="card-subheading">Final verified operational recommendation</p>
        </div>
        <span className={isFeasible ? 'badge-nominal' : 'badge-critical'}>
          {card.status}
        </span>
      </div>

      {/* Human review warning */}
      <div style={{
        background: '#1c1a0a',
        border: '1px solid #854d0e',
        borderRadius: '6px',
        padding: '0.6rem 1rem',
        marginBottom: '1rem',
        fontSize: '0.78rem',
        color: '#fde68a',
      }}>
        <strong>⚠ HUMAN REVIEW REQUIRED: </strong>{card.human_review_warning}
      </div>

      {isFeasible ? (
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
          {/* Left column */}
          <div>
            <div className="kv-row" style={{ marginBottom: '0.5rem' }}>
              <span className="kv-label" style={{ color: '#9ca3af', fontSize: '0.78rem' }}>ZONE</span>
              <span className="kv-val">{card.zone_id}</span>
            </div>
            <div className="kv-row" style={{ marginBottom: '0.5rem' }}>
              <span className="kv-label" style={{ color: '#9ca3af', fontSize: '0.78rem' }}>PRIORITY</span>
              <span className="kv-val">{card.priority}</span>
            </div>
            <div className="kv-row" style={{ marginBottom: '0.5rem' }}>
              <span className="kv-label" style={{ color: '#9ca3af', fontSize: '0.78rem' }}>INTERVENTION</span>
              <span className="zone-id-tag">{card.intervention_id}</span>
            </div>
            <div className="kv-row" style={{ marginBottom: '0.5rem' }}>
              <span className="kv-label" style={{ color: '#9ca3af', fontSize: '0.78rem' }}>TARGET NODE</span>
              <code className="score-code">{card.target_node}</code>
            </div>
            <div className="kv-row" style={{ marginBottom: '0.5rem' }}>
              <span className="kv-label" style={{ color: '#9ca3af', fontSize: '0.78rem' }}>ACTION</span>
              <span style={{ color: '#e5e7eb', fontSize: '0.88rem' }}>{card.action}</span>
            </div>
            <div className="kv-row" style={{ marginBottom: '0.5rem' }}>
              <span className="kv-label" style={{ color: '#9ca3af', fontSize: '0.78rem' }}>RESOURCES</span>
              <div className="resource-demand-tags">{resourceTags(card.required_resources)}</div>
            </div>
            <div className="kv-row" style={{ marginBottom: '0.5rem' }}>
              <span className="kv-label" style={{ color: '#9ca3af', fontSize: '0.78rem' }}>MODELLED RISK CHANGE</span>
              <code className="score-code" style={{ color: '#6ee7b7' }}>
                {card.modelled_relative_change !== null
                  ? `${(card.modelled_relative_change * 100).toFixed(2)}%`
                  : '—'}
              </code>
            </div>
          </div>

          {/* Right column */}
          <div>
            {card.expected_impact && (
              <div style={{ marginBottom: '0.75rem' }}>
                <strong style={{ color: '#9ca3af', fontSize: '0.78rem' }}>EXPECTED IMPACT (MODEL INDICES)</strong>
                <div style={{ marginTop: '0.4rem', fontSize: '0.82rem', color: '#d1d5db' }}>
                  <div>Impact Index: {fmt(card.expected_impact.before.impact_index)} → <strong style={{ color: '#22c55e' }}>{fmt(card.expected_impact.after.impact_index)}</strong></div>
                  <div>Cascade Length: {card.expected_impact.before.cascade_length} → <strong style={{ color: '#22c55e' }}>{card.expected_impact.after.cascade_length}</strong></div>
                  <div>Pop Risk: {fmt(card.expected_impact.before.population_risk)} → <strong style={{ color: '#22c55e' }}>{fmt(card.expected_impact.after.population_risk)}</strong></div>
                </div>
              </div>
            )}

            <div style={{ marginBottom: '0.75rem' }}>
              <strong style={{ color: '#9ca3af', fontSize: '0.78rem' }}>AI STATUS</strong>
              <div style={{ marginTop: '0.3rem' }}>
                <span style={{
                  background: '#1e3a5f',
                  color: '#93c5fd',
                  padding: '0.2rem 0.6rem',
                  borderRadius: '999px',
                  fontSize: '0.78rem',
                }}>
                  🤖 {card.ai_status}
                  {card.nugen_recommendation && ` — Nugen: ${card.nugen_recommendation}`}
                  {card.nugen_agreement === false && ' (AI differs from model)'}
                  {card.nugen_agreement === true && ' (AI agrees)'}
                </span>
              </div>
            </div>

            <div style={{ marginBottom: '0.75rem' }}>
              <strong style={{ color: '#9ca3af', fontSize: '0.78rem' }}>QUALITY FLAGS</strong>
              <div style={{ marginTop: '0.3rem', display: 'flex', flexWrap: 'wrap', gap: '0.3rem' }}>
                {card.quality_flags.map(flag => (
                  <span key={flag} style={{
                    background: '#374151',
                    color: '#d1d5db',
                    padding: '0.1rem 0.4rem',
                    borderRadius: '4px',
                    fontSize: '0.72rem',
                  }}>
                    {flag}
                  </span>
                ))}
              </div>
            </div>

            <div>
              <strong style={{ color: '#9ca3af', fontSize: '0.78rem' }}>REASON</strong>
              <p style={{ marginTop: '0.3rem', color: '#d1d5db', fontSize: '0.82rem', lineHeight: 1.5 }}>
                {card.reason}
              </p>
            </div>
          </div>
        </div>
      ) : (
        /* No feasible intervention */
        <div>
          <div style={{ color: '#f87171', fontSize: '0.95rem', marginBottom: '1rem' }}>
            <strong>⚠ No feasible intervention passed final verification.</strong>
          </div>
          <p style={{ color: '#d1d5db', fontSize: '0.85rem', marginBottom: '0.75rem' }}>
            {card.reason}
          </p>
          {card.blockers.length > 0 && (
            <div>
              <strong style={{ color: '#9ca3af', fontSize: '0.78rem' }}>BLOCKERS</strong>
              <ul style={{ marginTop: '0.3rem', paddingLeft: '1.2rem', color: '#fca5a5', fontSize: '0.85rem' }}>
                {card.blockers.map((b, i) => <li key={i}>{b}</li>)}
              </ul>
            </div>
          )}
          {card.rejected_candidates.length > 0 && (
            <div style={{ marginTop: '0.75rem' }}>
              <strong style={{ color: '#9ca3af', fontSize: '0.78rem' }}>REJECTED CANDIDATES</strong>
              {card.rejected_candidates.map(rc => (
                <div key={rc.intervention_id} style={{ marginTop: '0.4rem', fontSize: '0.82rem' }}>
                  <span className="zone-id-tag" style={{ background: '#450a0a', color: '#fca5a5' }}>
                    {rc.intervention_id}
                  </span>
                  <ul style={{ margin: '0.2rem 0 0', paddingLeft: '1.2rem', color: '#f87171' }}>
                    {rc.blockers.map((b, i) => <li key={i}>{b}</li>)}
                  </ul>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      <div style={{ marginTop: '0.75rem', fontSize: '0.72rem', color: '#6b7280' }}>
        Run ID: <code>{card.run_id}</code>
      </div>
    </div>
  );
};

// ── Main Tab Component ────────────────────────────────────────────────────────

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

  const hasM4Data = resourceAlloc || ranking || decCard;

  return (
    <div className="tab-pane interventions-pane">
      {/* Scope Status Banner */}
      <div className="milestone-placeholder-banner banner-live">
        <div className="placeholder-banner-head">
          <span className="badge-live">MILESTONE 4: ACTIVE</span>
          <span className="badge-spec">ALGORITHMS 8 &amp; 10–13 DECISION CORE</span>
          <h2 className="banner-title">Intervention Optimization &amp; Decision Support Engine</h2>
        </div>
        <p className="banner-text">
          Depot resource allocation, multi-criteria Pareto ranking, what-if counterfactual simulation,
          side-by-side alternative comparison, and Command Decision Card generation.
        </p>
      </div>

      {/* Analysis Error Alert */}
      {analysisError && (
        <div className="dashboard-card" style={{ background: '#2d1215', border: '1px solid #7f1d1d', marginBottom: '1.5rem', padding: '1rem' }}>
          <strong style={{ color: '#f87171' }}>Analysis Execution Failed: </strong>
          <span style={{ color: '#fca5a5' }}>{analysisError}</span>
        </div>
      )}

      {/* Awaiting Analysis Prompt */}
      {!analysisResult && (
        <div className="dashboard-card action-prompt-card" style={{ marginBottom: '1.5rem' }}>
          <div className="action-prompt-content" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '1rem' }}>
            <div>
              <h3 className="card-heading-sm">Intervention Optimization Awaiting Execution</h3>
              <p className="card-subheading">
                Execute flood risk analysis on <strong>{scenarioDetail?.name || 'the active scenario'}</strong> to evaluate depot resource feasibility, rank countermeasures, and generate operational decision cards.
              </p>
            </div>
            {onRunAnalysis && (
              <button
                type="button"
                className="btn btn-primary"
                onClick={onRunAnalysis}
                disabled={isAnalyzing}
              >
                {isAnalyzing ? 'Optimizing Interventions...' : 'Run Flood Analysis'}
              </button>
            )}
          </div>
        </div>
      )}

      {/* Monitoring Only Guard */}
      {analysisResult && (analysisResult.is_monitoring_only || analysisResult.cascade_status !== 'SUCCESS') && (
        <div className="dashboard-card monitoring-alert-card" style={{ marginBottom: '1.5rem', background: '#0f2027', border: '1px solid #1e3a5f' }}>
          <div className="monitoring-alert-head" style={{ marginBottom: '0.5rem' }}>
            <span className="badge-nominal">STATUS: MONITORING_ONLY</span>
            <h3 className="card-heading-sm" style={{ marginTop: '0.5rem' }}>No Flood Hotspots Qualified for Tactical Interventions</h3>
          </div>
          <p className="card-subheading">
            Downstream intervention algorithms (8, 10–13) require at least one zone exceeding the flood hotspot threshold (&ge;50.0). Catchment is currently within nominal thresholds.
          </p>
        </div>
      )}

      {/* Analysis Ran But No M4 Data Payload */}
      {analysisResult && !analysisResult.is_monitoring_only && analysisResult.cascade_status === 'SUCCESS' && !hasM4Data && (
        <div className="dashboard-card" style={{ marginBottom: '1.5rem', padding: '1rem' }}>
          <p className="banner-text">
            Analysis completed but Milestone 4 decision support data is missing from backend response.
          </p>
        </div>
      )}

      {/* Full M4 Dashboard Results */}
      {analysisResult && hasM4Data && (
        <>
          <DataDisclaimer />

          {/* Resource Allocation */}
          {resourceAlloc && <ResourceAllocationPanel data={resourceAlloc} />}

          {/* Intervention Ranking */}
          {ranking && (
            <InterventionRankingPanel
              feasible={ranking.feasible}
              infeasible={ranking.infeasible}
              nugenRecommended={
                ranking.nugen_recommendation
                  ? (ranking.nugen_recommendation as Record<string, string>)['recommended_action'] ?? null
                  : null
              }
            />
          )}

          {/* What-If Simulation */}
          {whatIf && <WhatIfPanel data={whatIf} />}

          {/* Alternative Comparison */}
          {altComp && (
            <AlternativeComparisonPanel
              noAction={altComp.no_action_baseline}
              rows={altComp.rows}
            />
          )}

          {/* Command Decision Card */}
          {decCard && <DecisionCardPanel card={decCard} />}
        </>
      )}
    </div>
  );
};
