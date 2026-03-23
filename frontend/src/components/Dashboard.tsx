import { useAnalytics, useRuns } from '../hooks/useApi';
import StatusBadge from './StatusBadge';

interface Props {
  onViewRun: (id: string) => void;
  onNewRun: () => void;
}

const RISK_COLORS: Record<string, string> = {
  low: 'bg-green-500',
  medium: 'bg-yellow-500',
  high: 'bg-orange-500',
  critical: 'bg-red-500',
};

export default function Dashboard({ onViewRun, onNewRun }: Props) {
  const { data, loading } = useAnalytics();
  const { runs } = useRuns();

  if (loading || !data) {
    return <div className="text-center py-16 text-gray-400">Loading dashboard...</div>;
  }

  const recentRuns = runs.slice(0, 5);

  return (
    <div className="space-y-6">
      {/* Stats row */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard label="Total Runs" value={data.total_runs} />
        <StatCard
          label="Avg Actions/Run"
          value={data.avg_actions_per_run}
        />
        <StatCard
          label="Approval Rate"
          value={
            data.total_runs > 0
              ? `${Math.round(((data.approval_breakdown.approved ?? 0) / Math.max(1, data.total_runs)) * 100)}%`
              : '—'
          }
        />
        <StatCard
          label="High Risk Runs"
          value={(data.risk_distribution.high ?? 0) + (data.risk_distribution.critical ?? 0)}
          alert={(data.risk_distribution.high ?? 0) + (data.risk_distribution.critical ?? 0) > 0}
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Risk distribution */}
        <div className="bg-white rounded-xl border border-gray-200 p-5">
          <h3 className="text-sm font-semibold text-gray-700 mb-4">Risk Distribution</h3>
          {Object.keys(data.risk_distribution).length === 0 ? (
            <p className="text-sm text-gray-400">No completed runs yet</p>
          ) : (
            <div className="space-y-3">
              {['low', 'medium', 'high', 'critical'].map(level => {
                const count = data.risk_distribution[level] ?? 0;
                if (count === 0 && data.total_runs > 0) return null;
                const pct = data.total_runs > 0 ? (count / data.total_runs) * 100 : 0;
                return (
                  <div key={level}>
                    <div className="flex justify-between text-xs mb-1">
                      <span className="capitalize text-gray-600">{level}</span>
                      <span className="text-gray-400">{count} runs</span>
                    </div>
                    <div className="h-2 bg-gray-100 rounded-full overflow-hidden">
                      <div
                        className={`h-full rounded-full transition-all ${RISK_COLORS[level]}`}
                        style={{ width: `${Math.max(pct, count > 0 ? 4 : 0)}%` }}
                      />
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Tool usage */}
        <div className="bg-white rounded-xl border border-gray-200 p-5">
          <h3 className="text-sm font-semibold text-gray-700 mb-4">Tool Usage</h3>
          {Object.keys(data.tool_usage).length === 0 ? (
            <p className="text-sm text-gray-400">No tool calls recorded</p>
          ) : (
            <div className="space-y-2">
              {Object.entries(data.tool_usage).map(([tool, count]) => {
                const maxCount = Math.max(...Object.values(data.tool_usage));
                return (
                  <div key={tool} className="flex items-center gap-3">
                    <code className="text-xs text-gray-600 w-28 truncate">{tool}</code>
                    <div className="flex-1 h-5 bg-gray-100 rounded-full overflow-hidden">
                      <div
                        className="h-full bg-indigo-400 rounded-full transition-all"
                        style={{ width: `${(count / maxCount) * 100}%` }}
                      />
                    </div>
                    <span className="text-xs text-gray-400 w-8 text-right">{count}</span>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Status breakdown */}
        <div className="bg-white rounded-xl border border-gray-200 p-5">
          <h3 className="text-sm font-semibold text-gray-700 mb-4">Run Status</h3>
          <div className="space-y-3">
            {Object.entries(data.status_breakdown).map(([status, count]) => (
              <div key={status} className="flex items-center justify-between">
                <StatusBadge status={status} />
                <span className="text-sm font-medium text-gray-700">{count}</span>
              </div>
            ))}
            {Object.keys(data.status_breakdown).length === 0 && (
              <p className="text-sm text-gray-400">No runs yet</p>
            )}
          </div>

          {data.top_agents.length > 0 && (
            <>
              <h3 className="text-sm font-semibold text-gray-700 mt-6 mb-3">Top Agents</h3>
              <div className="space-y-2">
                {data.top_agents.slice(0, 5).map(a => (
                  <div key={a.name} className="flex justify-between text-sm">
                    <span className="text-gray-600 truncate">{a.name}</span>
                    <span className="text-gray-400">{a.run_count} runs</span>
                  </div>
                ))}
              </div>
            </>
          )}
        </div>
      </div>

      {/* Recent runs */}
      <div className="bg-white rounded-xl border border-gray-200 p-5">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-sm font-semibold text-gray-700">Recent Runs</h3>
          {recentRuns.length === 0 && (
            <button onClick={onNewRun} className="text-sm text-indigo-600 hover:text-indigo-800">
              Create first run
            </button>
          )}
        </div>
        {recentRuns.length === 0 ? (
          <div className="text-center py-8">
            <p className="text-gray-400 text-sm">No runs yet. Start by creating a new sandbox run.</p>
          </div>
        ) : (
          <div className="space-y-2">
            {recentRuns.map(run => (
              <button
                key={run.id}
                onClick={() => onViewRun(run.id)}
                className="w-full text-left flex items-center justify-between py-2.5 px-3 rounded-lg hover:bg-gray-50 transition-colors"
              >
                <div className="flex items-center gap-3">
                  <StatusBadge status={run.status} />
                  <span className="text-sm font-medium text-gray-800">{run.agent_definition.name}</span>
                  <span className="text-xs text-gray-400 font-mono">{run.id}</span>
                </div>
                <div className="flex items-center gap-3 text-xs text-gray-400">
                  {run.risk_report && (
                    <span className={`px-2 py-0.5 rounded-full font-medium ${
                      run.risk_report.risk_level === 'critical' ? 'bg-red-100 text-red-700' :
                      run.risk_report.risk_level === 'high' ? 'bg-orange-100 text-orange-700' :
                      run.risk_report.risk_level === 'medium' ? 'bg-yellow-100 text-yellow-700' :
                      'bg-green-100 text-green-700'
                    }`}>
                      {run.risk_report.risk_level} risk
                    </span>
                  )}
                  <span>{run.actions.length} actions</span>
                  <span>{new Date(run.created_at).toLocaleString()}</span>
                </div>
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

function StatCard({ label, value, alert }: { label: string; value: number | string; alert?: boolean }) {
  return (
    <div className={`bg-white rounded-xl border p-5 ${alert ? 'border-red-200' : 'border-gray-200'}`}>
      <div className="text-xs font-medium text-gray-500 uppercase tracking-wide">{label}</div>
      <div className={`text-2xl font-bold mt-1 ${alert ? 'text-red-600' : 'text-gray-900'}`}>
        {value}
      </div>
    </div>
  );
}
