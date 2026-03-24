import { useAnalytics, useRuns } from '../hooks/useApi';
import StatusBadge from './StatusBadge';
import WelcomeGuide from './WelcomeGuide';

interface Props {
  onViewRun: (id: string) => void;
  onNewRun: () => void;
  onViewTemplates?: () => void;
}

const RISK_COLORS: Record<string, string> = {
  low: 'bg-emerald-500',
  medium: 'bg-amber-500',
  high: 'bg-orange-500',
  critical: 'bg-red-500',
};

export default function Dashboard({ onViewRun, onNewRun, onViewTemplates }: Props) {
  const { data, loading, refresh: refreshAnalytics } = useAnalytics();
  const { runs, refresh: refreshRuns } = useRuns();

  if (loading || !data) {
    return <div className="text-center py-16 text-text-tertiary">Loading dashboard...</div>;
  }

  // Show welcome guide for new users with no runs
  if (data.total_runs === 0 && runs.length === 0) {
    return (
      <WelcomeGuide
        onViewRun={onViewRun}
        onNewRun={onNewRun}
        onViewTemplates={onViewTemplates || (() => {})}
        onRefresh={() => { refreshAnalytics(); refreshRuns(); }}
      />
    );
  }

  const recentRuns = runs.slice(0, 5);

  return (
    <div className="space-y-8">
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard label="Total Runs" value={data.total_runs} />
        <StatCard label="Avg Actions" value={data.avg_actions_per_run} />
        <StatCard
          label="Approval Rate"
          value={
            data.total_runs > 0
              ? `${Math.round(((data.approval_breakdown.approved ?? 0) / Math.max(1, data.total_runs)) * 100)}%`
              : '-'
          }
        />
        <StatCard
          label="High Risk"
          value={(data.risk_distribution.high ?? 0) + (data.risk_distribution.critical ?? 0)}
          alert={(data.risk_distribution.high ?? 0) + (data.risk_distribution.critical ?? 0) > 0}
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="bg-white rounded-lg border border-border p-5">
          <h3 className="text-[13px] font-medium text-text-primary mb-4">Risk Distribution</h3>
          {Object.keys(data.risk_distribution).length === 0 ? (
            <p className="text-xs text-text-tertiary">No completed runs yet</p>
          ) : (
            <div className="space-y-3">
              {['low', 'medium', 'high', 'critical'].map(level => {
                const count = data.risk_distribution[level] ?? 0;
                if (count === 0 && data.total_runs > 0) return null;
                const pct = data.total_runs > 0 ? (count / data.total_runs) * 100 : 0;
                return (
                  <div key={level}>
                    <div className="flex justify-between text-xs mb-1">
                      <span className="capitalize text-text-secondary">{level}</span>
                      <span className="text-text-tertiary">{count}</span>
                    </div>
                    <div className="h-1.5 bg-surface-secondary rounded-full overflow-hidden">
                      <div
                        className={`h-full rounded-full ${RISK_COLORS[level]}`}
                        style={{ width: `${Math.max(pct, count > 0 ? 4 : 0)}%` }}
                      />
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        <div className="bg-white rounded-lg border border-border p-5">
          <h3 className="text-[13px] font-medium text-text-primary mb-4">Tool Usage</h3>
          {Object.keys(data.tool_usage).length === 0 ? (
            <p className="text-xs text-text-tertiary">No tool calls recorded</p>
          ) : (
            <div className="space-y-2.5">
              {Object.entries(data.tool_usage).map(([tool, count]) => {
                const maxCount = Math.max(...Object.values(data.tool_usage));
                return (
                  <div key={tool} className="flex items-center gap-3">
                    <code className="text-xs text-text-secondary w-28 truncate">{tool}</code>
                    <div className="flex-1 h-1.5 bg-surface-secondary rounded-full overflow-hidden">
                      <div
                        className="h-full bg-accent/60 rounded-full"
                        style={{ width: `${(count / maxCount) * 100}%` }}
                      />
                    </div>
                    <span className="text-xs text-text-tertiary w-8 text-right">{count}</span>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        <div className="bg-white rounded-lg border border-border p-5">
          <h3 className="text-[13px] font-medium text-text-primary mb-4">Run Status</h3>
          <div className="space-y-2.5">
            {Object.entries(data.status_breakdown).map(([status, count]) => (
              <div key={status} className="flex items-center justify-between">
                <StatusBadge status={status} />
                <span className="text-sm font-medium text-text-primary">{count}</span>
              </div>
            ))}
            {Object.keys(data.status_breakdown).length === 0 && (
              <p className="text-xs text-text-tertiary">No runs yet</p>
            )}
          </div>

          {data.top_agents.length > 0 && (
            <>
              <div className="border-t border-border my-4" />
              <h3 className="text-[13px] font-medium text-text-primary mb-3">Top Agents</h3>
              <div className="space-y-2">
                {data.top_agents.slice(0, 5).map(a => (
                  <div key={a.name} className="flex justify-between text-xs">
                    <span className="text-text-secondary truncate">{a.name}</span>
                    <span className="text-text-tertiary">{a.run_count}</span>
                  </div>
                ))}
              </div>
            </>
          )}
        </div>
      </div>

      <div className="bg-white rounded-lg border border-border p-5">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-[13px] font-medium text-text-primary">Recent Runs</h3>
          {recentRuns.length === 0 && (
            <button onClick={onNewRun} className="text-[13px] text-accent hover:text-accent-dark">
              Create first run
            </button>
          )}
        </div>
        {recentRuns.length === 0 ? (
          <div className="text-center py-8">
            <p className="text-text-tertiary text-sm">No runs yet. Create a new sandbox run to get started.</p>
          </div>
        ) : (
          <div className="space-y-1">
            {recentRuns.map(run => (
              <button
                key={run.id}
                onClick={() => onViewRun(run.id)}
                className="w-full text-left flex items-center justify-between py-2.5 px-3 rounded-md hover:bg-surface-secondary transition-colors"
              >
                <div className="flex items-center gap-3">
                  <StatusBadge status={run.status} />
                  <span className="text-[13px] font-medium text-text-primary">{run.agent_definition.name}</span>
                  <span className="text-xs text-text-tertiary font-mono">{run.id}</span>
                </div>
                <div className="flex items-center gap-3 text-xs text-text-tertiary">
                  {run.risk_report && (
                    <span className={`px-1.5 py-0.5 rounded text-[11px] font-medium ${
                      run.risk_report.risk_level === 'critical' ? 'bg-red-50 text-red-600' :
                      run.risk_report.risk_level === 'high' ? 'bg-orange-50 text-orange-600' :
                      run.risk_report.risk_level === 'medium' ? 'bg-amber-50 text-amber-600' :
                      'bg-emerald-50 text-emerald-600'
                    }`}>
                      {run.risk_report.risk_level}
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
    <div className={`bg-white rounded-lg border p-5 ${alert ? 'border-red-200' : 'border-border'}`}>
      <div className="text-xs text-text-tertiary">{label}</div>
      <div className={`text-2xl font-semibold mt-1 ${alert ? 'text-red-600' : 'text-text-primary'}`}>
        {value}
      </div>
    </div>
  );
}
