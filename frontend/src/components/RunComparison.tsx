import { useState } from 'react';
import { compareRuns, useRuns } from '../hooks/useApi';
import type { RunComparison as RunComparisonType } from '../types';

interface Props {
  initialRunA?: string;
  onViewRun: (id: string) => void;
}

const RISK_BADGE: Record<string, string> = {
  low: 'bg-green-100 text-green-700',
  medium: 'bg-yellow-100 text-yellow-700',
  high: 'bg-orange-100 text-orange-700',
  critical: 'bg-red-100 text-red-700',
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
    setLoading(true);
    setError(null);
    try {
      const result = await compareRuns(runIdA, runIdB);
      setComparison(result);
    } catch (err) {
      setError('Failed to compare runs');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      <h2 className="text-lg font-semibold text-gray-800">Compare Runs</h2>

      {/* Run selector */}
      <div className="bg-white rounded-xl border border-gray-200 p-5">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="block text-xs font-medium text-gray-500 mb-1">Run A (Baseline)</label>
            <select
              value={runIdA}
              onChange={e => setRunIdA(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
            >
              <option value="">Select run...</option>
              {runs.filter(r => r.status === 'complete').map(r => (
                <option key={r.id} value={r.id}>
                  {r.agent_definition.name} ({r.id}) - {new Date(r.created_at).toLocaleDateString()}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-500 mb-1">Run B (Comparison)</label>
            <select
              value={runIdB}
              onChange={e => setRunIdB(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
            >
              <option value="">Select run...</option>
              {runs.filter(r => r.status === 'complete' && r.id !== runIdA).map(r => (
                <option key={r.id} value={r.id}>
                  {r.agent_definition.name} ({r.id}) - {new Date(r.created_at).toLocaleDateString()}
                </option>
              ))}
            </select>
          </div>
        </div>
        <div className="mt-4 flex items-center gap-3">
          <button
            onClick={handleCompare}
            disabled={!runIdA || !runIdB || loading}
            className="px-5 py-2 bg-gradient-to-r from-indigo-600 to-violet-600 text-white text-sm font-medium rounded-lg hover:from-indigo-700 hover:to-violet-700 disabled:opacity-50 transition-all shadow-sm"
          >
            {loading ? 'Comparing...' : 'Compare'}
          </button>
          {error && <span className="text-sm text-red-600">{error}</span>}
        </div>
      </div>

      {/* Comparison results */}
      {comparison && (
        <div className="space-y-4">
          {/* Summary */}
          <div className="bg-white rounded-xl border border-gray-200 p-5">
            <h3 className="text-sm font-semibold text-gray-700 mb-3">Summary</h3>
            <ul className="space-y-1.5">
              {comparison.summary.map((point, i) => (
                <li key={i} className="text-sm text-gray-600 flex gap-2">
                  <span className="text-gray-400 flex-shrink-0">-</span>
                  {point}
                </li>
              ))}
            </ul>
          </div>

          {/* Side-by-side metadata */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <MetadataCard
              label="Run A"
              meta={comparison.metadata.run_a}
              risk={comparison.risk.run_a}
              onView={() => onViewRun(comparison.run_a_id)}
            />
            <MetadataCard
              label="Run B"
              meta={comparison.metadata.run_b}
              risk={comparison.risk.run_b}
              onView={() => onViewRun(comparison.run_b_id)}
            />
          </div>

          {/* Risk comparison */}
          <div className="bg-white rounded-xl border border-gray-200 p-5">
            <h3 className="text-sm font-semibold text-gray-700 mb-3">Risk Comparison</h3>
            <div className="flex items-center gap-6">
              <div className="flex-1">
                <div className="flex justify-between text-xs mb-1">
                  <span className="text-gray-500">Run A</span>
                  <span className={`px-2 py-0.5 rounded-full font-medium ${RISK_BADGE[comparison.risk.run_a.risk_level] || 'bg-gray-100 text-gray-600'}`}>
                    {comparison.risk.run_a.risk_level} ({comparison.risk.run_a.overall_score})
                  </span>
                </div>
                <div className="h-3 bg-gray-100 rounded-full overflow-hidden">
                  <div className="h-full bg-indigo-500 rounded-full" style={{ width: `${comparison.risk.run_a.overall_score}%` }} />
                </div>
              </div>
              <div className="flex-1">
                <div className="flex justify-between text-xs mb-1">
                  <span className="text-gray-500">Run B</span>
                  <span className={`px-2 py-0.5 rounded-full font-medium ${RISK_BADGE[comparison.risk.run_b.risk_level] || 'bg-gray-100 text-gray-600'}`}>
                    {comparison.risk.run_b.risk_level} ({comparison.risk.run_b.overall_score})
                  </span>
                </div>
                <div className="h-3 bg-gray-100 rounded-full overflow-hidden">
                  <div className="h-full bg-violet-500 rounded-full" style={{ width: `${comparison.risk.run_b.overall_score}%` }} />
                </div>
              </div>
            </div>
            {comparison.risk.risk_level_changed && (
              <p className="text-xs text-orange-600 mt-2">Risk level changed between runs</p>
            )}
          </div>

          {/* Tool usage comparison */}
          <div className="bg-white rounded-xl border border-gray-200 p-5">
            <h3 className="text-sm font-semibold text-gray-700 mb-3">Tool Usage</h3>
            <div className="space-y-2">
              {comparison.tool_usage.per_tool.map(t => (
                <div key={t.tool} className="grid grid-cols-12 gap-2 items-center text-sm">
                  <code className="col-span-3 text-xs text-gray-600 truncate">{t.tool}</code>
                  <div className="col-span-4 flex items-center gap-2">
                    <div className="flex-1 h-2 bg-gray-100 rounded-full overflow-hidden">
                      <div className="h-full bg-indigo-400 rounded-full" style={{ width: `${(t.run_a_count / Math.max(comparison.tool_usage.run_a_total, 1)) * 100}%` }} />
                    </div>
                    <span className="text-xs text-gray-400 w-6 text-right">{t.run_a_count}</span>
                  </div>
                  <div className="col-span-4 flex items-center gap-2">
                    <div className="flex-1 h-2 bg-gray-100 rounded-full overflow-hidden">
                      <div className="h-full bg-violet-400 rounded-full" style={{ width: `${(t.run_b_count / Math.max(comparison.tool_usage.run_b_total, 1)) * 100}%` }} />
                    </div>
                    <span className="text-xs text-gray-400 w-6 text-right">{t.run_b_count}</span>
                  </div>
                  <span className={`col-span-1 text-xs text-center font-medium ${
                    t.difference > 0 ? 'text-orange-600' : t.difference < 0 ? 'text-green-600' : 'text-gray-400'
                  }`}>
                    {t.difference > 0 ? `+${t.difference}` : t.difference}
                  </span>
                </div>
              ))}
            </div>
          </div>

          {/* Action sequence */}
          <div className="bg-white rounded-xl border border-gray-200 p-5">
            <h3 className="text-sm font-semibold text-gray-700 mb-3">
              Action Sequence (Similarity: {Math.round(comparison.action_sequence.similarity * 100)}%)
            </h3>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <div className="text-xs font-medium text-gray-500 mb-2">Run A</div>
                <div className="flex flex-wrap gap-1">
                  {comparison.action_sequence.run_a_sequence.map((tool, i) => (
                    <span key={i} className="text-xs px-2 py-1 bg-indigo-50 text-indigo-700 rounded">
                      {tool}
                    </span>
                  ))}
                </div>
              </div>
              <div>
                <div className="text-xs font-medium text-gray-500 mb-2">Run B</div>
                <div className="flex flex-wrap gap-1">
                  {comparison.action_sequence.run_b_sequence.map((tool, i) => (
                    <span key={i} className="text-xs px-2 py-1 bg-violet-50 text-violet-700 rounded">
                      {tool}
                    </span>
                  ))}
                </div>
              </div>
            </div>
          </div>

          {/* Environment diff */}
          {comparison.environment.available && (
            <div className="bg-white rounded-xl border border-gray-200 p-5">
              <h3 className="text-sm font-semibold text-gray-700 mb-3">Environment Diff</h3>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {comparison.environment.filesystem && (
                  <div>
                    <div className="text-xs font-medium text-gray-500 mb-2">Filesystem</div>
                    {comparison.environment.filesystem.content_differs.length > 0 && (
                      <div className="mb-2">
                        <span className="text-xs text-orange-600">Changed files:</span>
                        {comparison.environment.filesystem.content_differs.map(f => (
                          <div key={f} className="text-xs text-gray-600 font-mono ml-2">{f}</div>
                        ))}
                      </div>
                    )}
                    {comparison.environment.filesystem.only_in_b.length > 0 && (
                      <div>
                        <span className="text-xs text-green-600">New in Run B:</span>
                        {comparison.environment.filesystem.only_in_b.map(f => (
                          <div key={f} className="text-xs text-gray-600 font-mono ml-2">{f}</div>
                        ))}
                      </div>
                    )}
                    {comparison.environment.filesystem.content_differs.length === 0 &&
                     comparison.environment.filesystem.only_in_b.length === 0 &&
                     comparison.environment.filesystem.only_in_a.length === 0 && (
                      <span className="text-xs text-gray-400">No differences</span>
                    )}
                  </div>
                )}
                {comparison.environment.emails && (
                  <div>
                    <div className="text-xs font-medium text-gray-500 mb-2">Emails Sent</div>
                    <div className="flex gap-4 text-sm">
                      <span className="text-gray-600">Run A: {comparison.environment.emails.run_a_count}</span>
                      <span className="text-gray-600">Run B: {comparison.environment.emails.run_b_count}</span>
                    </div>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function MetadataCard({
  label,
  meta,
  risk,
  onView,
}: {
  label: string;
  meta: { name: string; status: string; action_count: number; diff_count: number; created_at: string };
  risk: { overall_score: number; risk_level: string; signal_count: number };
  onView: () => void;
}) {
  return (
    <div className="bg-white rounded-xl border border-gray-200 p-5">
      <div className="flex items-center justify-between mb-3">
        <h4 className="text-sm font-semibold text-gray-700">{label}</h4>
        <button onClick={onView} className="text-xs text-indigo-600 hover:text-indigo-800">View</button>
      </div>
      <div className="space-y-2 text-sm">
        <div className="flex justify-between">
          <span className="text-gray-500">Agent</span>
          <span className="text-gray-800 font-medium">{meta.name}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-gray-500">Status</span>
          <span className="text-gray-800">{meta.status}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-gray-500">Actions</span>
          <span className="text-gray-800">{meta.action_count}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-gray-500">State Changes</span>
          <span className="text-gray-800">{meta.diff_count}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-gray-500">Risk</span>
          <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${RISK_BADGE[risk.risk_level] || 'bg-gray-100 text-gray-600'}`}>
            {risk.risk_level} ({risk.overall_score})
          </span>
        </div>
      </div>
    </div>
  );
}
