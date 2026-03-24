import { useState } from 'react';
import { useRuns } from '../hooks/useApi';
import StatusBadge from './StatusBadge';

interface Props {
  onSelect: (id: string) => void;
}

export default function RunHistory({ onSelect }: Props) {
  const [statusFilter, setStatusFilter] = useState<string>('');
  const [search, setSearch] = useState('');
  const { runs, total, loading, refresh } = useRuns({
    status: statusFilter || undefined,
    agent_name: search || undefined,
    limit: 50,
  });

  if (loading) {
    return <div className="text-center py-12 text-text-tertiary">Loading runs...</div>;
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-5">
        <h2 className="text-lg font-semibold text-text-primary">
          Run History
          {total > 0 && <span className="text-sm font-normal text-text-tertiary ml-2">({total})</span>}
        </h2>
        <button onClick={refresh} className="text-[13px] text-text-tertiary hover:text-text-secondary">
          Refresh
        </button>
      </div>

      <div className="flex gap-3 mb-5">
        <input
          type="text"
          value={search}
          onChange={e => setSearch(e.target.value)}
          placeholder="Search by agent name..."
          className="flex-1 px-3 py-2 border border-border rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-accent/30 focus:border-accent bg-white"
        />
        <select
          value={statusFilter}
          onChange={e => setStatusFilter(e.target.value)}
          className="px-3 py-2 border border-border rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-accent/30 focus:border-accent bg-white"
        >
          <option value="">All statuses</option>
          <option value="running">Running</option>
          <option value="complete">Complete</option>
          <option value="failed">Failed</option>
        </select>
      </div>

      {runs.length === 0 ? (
        <div className="text-center py-16">
          <p className="text-text-tertiary text-sm">
            {statusFilter || search ? 'No runs match your filters.' : 'No sandbox runs yet.'}
          </p>
        </div>
      ) : (
        <>
          <div className="hidden md:grid grid-cols-12 gap-3 px-4 py-2 text-[11px] font-medium text-text-tertiary uppercase tracking-wider">
            <div className="col-span-1">Status</div>
            <div className="col-span-3">Agent</div>
            <div className="col-span-1">ID</div>
            <div className="col-span-2">Risk</div>
            <div className="col-span-1">Actions</div>
            <div className="col-span-2">Decision</div>
            <div className="col-span-2 text-right">Created</div>
          </div>

          <div className="space-y-1">
            {runs.map((run) => (
              <button
                key={run.id}
                onClick={() => onSelect(run.id)}
                className="w-full text-left bg-white rounded-lg border border-border px-4 py-3 hover:bg-surface-secondary transition-colors"
              >
                <div className="md:grid md:grid-cols-12 md:gap-3 md:items-center">
                  <div className="col-span-1">
                    <StatusBadge status={run.status} />
                  </div>
                  <div className="col-span-3">
                    <span className="text-[13px] font-medium text-text-primary">{run.agent_definition.name}</span>
                    <p className="text-xs text-text-tertiary truncate mt-0.5">{run.agent_definition.goal}</p>
                  </div>
                  <div className="col-span-1">
                    <span className="text-xs text-text-tertiary font-mono">{run.id}</span>
                  </div>
                  <div className="col-span-2">
                    {run.risk_report ? (
                      <div className="flex items-center gap-2">
                        <span className={`text-[11px] px-1.5 py-0.5 rounded font-medium ${
                          run.risk_report.risk_level === 'critical' ? 'bg-red-50 text-red-600' :
                          run.risk_report.risk_level === 'high' ? 'bg-orange-50 text-orange-600' :
                          run.risk_report.risk_level === 'medium' ? 'bg-amber-50 text-amber-600' :
                          'bg-emerald-50 text-emerald-600'
                        }`}>
                          {run.risk_report.risk_level}
                        </span>
                        <span className="text-xs text-text-tertiary">{run.risk_report.overall_score}</span>
                      </div>
                    ) : (
                      <span className="text-xs text-text-tertiary">-</span>
                    )}
                  </div>
                  <div className="col-span-1">
                    <span className="text-xs text-text-secondary">{run.actions.length}</span>
                  </div>
                  <div className="col-span-2">
                    {run.approval ? (
                      <span className={`text-xs font-medium ${
                        run.approval.decision === 'approved' ? 'text-emerald-600' :
                        run.approval.decision === 'rejected' ? 'text-red-600' :
                        'text-amber-600'
                      }`}>
                        {run.approval.decision.replace('_', ' ')}
                      </span>
                    ) : run.status === 'complete' ? (
                      <span className="text-xs text-text-tertiary">pending review</span>
                    ) : (
                      <span className="text-xs text-text-tertiary">-</span>
                    )}
                  </div>
                  <div className="col-span-2 text-right">
                    <span className="text-xs text-text-tertiary">{new Date(run.created_at).toLocaleString()}</span>
                  </div>
                </div>
              </button>
            ))}
          </div>
        </>
      )}
    </div>
  );
}
