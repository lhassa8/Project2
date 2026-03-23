import { useRuns } from '../hooks/useApi';
import StatusBadge from './StatusBadge';

interface Props {
  onSelect: (id: string) => void;
}

const RISK_BADGE: Record<string, string> = {
  low: 'bg-green-100 text-green-700',
  medium: 'bg-yellow-100 text-yellow-700',
  high: 'bg-orange-100 text-orange-700',
  critical: 'bg-red-100 text-red-700',
};

export default function RunHistory({ onSelect }: Props) {
  const { runs, loading, refresh } = useRuns();

  if (loading) {
    return <div className="text-center py-12 text-gray-500">Loading runs...</div>;
  }

  if (runs.length === 0) {
    return (
      <div className="text-center py-16">
        <p className="text-gray-400 text-lg mb-2">No sandbox runs yet</p>
        <p className="text-gray-400 text-sm">Create a new run to get started.</p>
      </div>
    );
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-semibold text-gray-800">Run History</h2>
        <button onClick={refresh} className="text-sm text-indigo-600 hover:text-indigo-800">
          Refresh
        </button>
      </div>

      {/* Table header */}
      <div className="hidden md:grid grid-cols-12 gap-3 px-4 py-2 text-xs font-medium text-gray-400 uppercase tracking-wide">
        <div className="col-span-1">Status</div>
        <div className="col-span-3">Agent</div>
        <div className="col-span-1">ID</div>
        <div className="col-span-2">Risk</div>
        <div className="col-span-1">Actions</div>
        <div className="col-span-2">Decision</div>
        <div className="col-span-2 text-right">Created</div>
      </div>

      <div className="space-y-1.5">
        {runs.map((run) => (
          <button
            key={run.id}
            onClick={() => onSelect(run.id)}
            className="w-full text-left bg-white rounded-xl border border-gray-200 px-4 py-3 hover:border-indigo-300 hover:shadow-sm transition-all"
          >
            <div className="md:grid md:grid-cols-12 md:gap-3 md:items-center">
              <div className="col-span-1">
                <StatusBadge status={run.status} />
              </div>
              <div className="col-span-3">
                <span className="text-sm font-medium text-gray-900">{run.agent_definition.name}</span>
                <p className="text-xs text-gray-400 truncate mt-0.5">{run.agent_definition.goal}</p>
              </div>
              <div className="col-span-1">
                <span className="text-xs text-gray-400 font-mono">{run.id}</span>
              </div>
              <div className="col-span-2">
                {run.risk_report ? (
                  <div className="flex items-center gap-2">
                    <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${RISK_BADGE[run.risk_report.risk_level]}`}>
                      {run.risk_report.risk_level}
                    </span>
                    <span className="text-xs text-gray-400">{run.risk_report.overall_score}/100</span>
                  </div>
                ) : (
                  <span className="text-xs text-gray-300">-</span>
                )}
              </div>
              <div className="col-span-1">
                <span className="text-xs text-gray-500">{run.actions.length}</span>
              </div>
              <div className="col-span-2">
                {run.approval ? (
                  <span className={`text-xs font-medium ${
                    run.approval.decision === 'approved' ? 'text-green-600' :
                    run.approval.decision === 'rejected' ? 'text-red-600' :
                    'text-yellow-600'
                  }`}>
                    {run.approval.decision.replace('_', ' ')}
                  </span>
                ) : run.status === 'complete' ? (
                  <span className="text-xs text-gray-400">pending review</span>
                ) : (
                  <span className="text-xs text-gray-300">-</span>
                )}
              </div>
              <div className="col-span-2 text-right">
                <span className="text-xs text-gray-400">{new Date(run.created_at).toLocaleString()}</span>
              </div>
            </div>
          </button>
        ))}
      </div>
    </div>
  );
}
