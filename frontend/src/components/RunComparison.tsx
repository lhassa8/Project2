import { useState } from 'react';
import { compareRuns, useRuns } from '../hooks/useApi';
import type { RunComparison as RunComparisonType } from '../types';

interface Props {
  initialRunA?: string;
  onViewRun: (id: string) => void;
}

const RISK_STYLE: Record<string, string> = {
  low: 'bg-emerald-50 text-emerald-600',
  medium: 'bg-amber-50 text-amber-600',
  high: 'bg-orange-50 text-orange-600',
  critical: 'bg-red-50 text-red-600',
};

export default function RunComparisonView({ initialRunA, onViewRun }: Props) {
  const { runs } = useRuns();
  const [runIdA, setRunIdA] = useState(initialRunA || '');
  const [runIdB, setRunIdB] = useState('');
  const [comparison, setComparison] = useState<RunComparisonType | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleCompare = async () => {
    if (!runIdA || !runIdB) return;
    setLoading(true); setError(null);
    try { setComparison(await compareRuns(runIdA, runIdB)); }
    catch { setError('Failed to compare runs'); }
    finally { setLoading(false); }
  };

  return (
    <div className="space-y-6">
      <h2 className="text-lg font-semibold text-text-primary">Compare Runs</h2>

      <div className="bg-white rounded-lg border border-border p-5">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="block text-xs text-text-tertiary mb-1">Run A (Baseline)</label>
            <select value={runIdA} onChange={e => setRunIdA(e.target.value)} className="w-full px-3 py-2 border border-border rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-accent/30 focus:border-accent bg-white">
              <option value="">Select run...</option>
              {runs.filter(r => r.status === 'complete').map(r => (
                <option key={r.id} value={r.id}>{r.agent_definition.name} ({r.id})</option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-xs text-text-tertiary mb-1">Run B (Comparison)</label>
            <select value={runIdB} onChange={e => setRunIdB(e.target.value)} className="w-full px-3 py-2 border border-border rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-accent/30 focus:border-accent bg-white">
              <option value="">Select run...</option>
              {runs.filter(r => r.status === 'complete' && r.id !== runIdA).map(r => (
                <option key={r.id} value={r.id}>{r.agent_definition.name} ({r.id})</option>
              ))}
            </select>
          </div>
        </div>
        <div className="mt-4 flex items-center gap-3">
          <button onClick={handleCompare} disabled={!runIdA || !runIdB || loading} className="px-5 py-2 bg-text-primary text-white text-[13px] font-medium rounded-md hover:bg-black/80 disabled:opacity-40 transition-colors">
            {loading ? 'Comparing...' : 'Compare'}
          </button>
          {error && <span className="text-[13px] text-red-600">{error}</span>}
        </div>
      </div>

      {comparison && (
        <div className="space-y-4">
          <div className="bg-white rounded-lg border border-border p-5">
            <h3 className="text-[13px] font-medium text-text-primary mb-3">Summary</h3>
            <ul className="space-y-1.5">
              {comparison.summary.map((point, i) => (
                <li key={i} className="text-[13px] text-text-secondary flex gap-2">
                  <span className="text-text-tertiary flex-shrink-0">-</span>{point}
                </li>
              ))}
            </ul>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {['run_a', 'run_b'].map(key => {
              const meta = comparison.metadata[key as 'run_a' | 'run_b'];
              const risk = comparison.risk[key as 'run_a' | 'run_b'];
              const id = key === 'run_a' ? comparison.run_a_id : comparison.run_b_id;
              return (
                <div key={key} className="bg-white rounded-lg border border-border p-5">
                  <div className="flex items-center justify-between mb-3">
                    <h4 className="text-[13px] font-medium text-text-primary">{key === 'run_a' ? 'Run A' : 'Run B'}</h4>
                    <button onClick={() => onViewRun(id)} className="text-xs text-accent hover:text-accent-dark">View</button>
                  </div>
                  <div className="space-y-2 text-[13px]">
                    <div className="flex justify-between"><span className="text-text-tertiary">Agent</span><span className="text-text-primary font-medium">{meta.name}</span></div>
                    <div className="flex justify-between"><span className="text-text-tertiary">Actions</span><span className="text-text-primary">{meta.action_count}</span></div>
                    <div className="flex justify-between"><span className="text-text-tertiary">Risk</span><span className={`text-[11px] px-1.5 py-0.5 rounded font-medium ${RISK_STYLE[risk.risk_level] || 'bg-gray-50 text-text-secondary'}`}>{risk.risk_level} ({risk.overall_score})</span></div>
                  </div>
                </div>
              );
            })}
          </div>

          <div className="bg-white rounded-lg border border-border p-5">
            <h3 className="text-[13px] font-medium text-text-primary mb-3">Risk Comparison</h3>
            <div className="flex items-center gap-6">
              {['run_a', 'run_b'].map(key => {
                const risk = comparison.risk[key as 'run_a' | 'run_b'];
                return (
                  <div key={key} className="flex-1">
                    <div className="flex justify-between text-xs mb-1">
                      <span className="text-text-tertiary">{key === 'run_a' ? 'Run A' : 'Run B'}</span>
                      <span className="text-text-secondary">{risk.overall_score}/100</span>
                    </div>
                    <div className="h-1.5 bg-surface-secondary rounded-full overflow-hidden">
                      <div className="h-full bg-accent/60 rounded-full" style={{ width: `${risk.overall_score}%` }} />
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          <div className="bg-white rounded-lg border border-border p-5">
            <h3 className="text-[13px] font-medium text-text-primary mb-3">
              Action Sequence ({Math.round(comparison.action_sequence.similarity * 100)}% similar)
            </h3>
            <div className="grid grid-cols-2 gap-4">
              {['run_a', 'run_b'].map(key => {
                const seq = comparison.action_sequence[`${key}_sequence` as 'run_a_sequence' | 'run_b_sequence'];
                return (
                  <div key={key}>
                    <div className="text-xs text-text-tertiary mb-2">{key === 'run_a' ? 'Run A' : 'Run B'}</div>
                    <div className="flex flex-wrap gap-1">
                      {seq.map((tool, i) => (
                        <span key={i} className="text-xs px-2 py-1 bg-surface-secondary text-text-secondary rounded">{tool}</span>
                      ))}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
