import { useRuns } from '../hooks/useApi';
import StatusBadge from './StatusBadge';

interface Props {
  onSelect: (id: string) => void;
}

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
        <button
          onClick={refresh}
          className="text-sm text-indigo-600 hover:text-indigo-800"
        >
          Refresh
        </button>
      </div>
      <div className="space-y-2">
        {runs.map((run) => (
          <button
            key={run.id}
            onClick={() => onSelect(run.id)}
            className="w-full text-left bg-white rounded-lg border border-gray-200 p-4 hover:border-indigo-300 hover:shadow-sm transition-all"
          >
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <StatusBadge status={run.status} />
                <span className="font-medium text-gray-900">
                  {run.agent_definition.name}
                </span>
                <span className="text-sm text-gray-400 font-mono">{run.id}</span>
              </div>
              <div className="flex items-center gap-4 text-sm text-gray-500">
                {run.approval && (
                  <span className={
                    run.approval.decision === 'approved' ? 'text-green-600 font-medium' :
                    run.approval.decision === 'rejected' ? 'text-red-600 font-medium' :
                    'text-yellow-600 font-medium'
                  }>
                    {run.approval.decision.replace('_', ' ')}
                  </span>
                )}
                <span>{run.actions.length} actions</span>
                <span>{new Date(run.created_at).toLocaleString()}</span>
              </div>
            </div>
            <p className="text-sm text-gray-500 mt-1 truncate">
              {run.agent_definition.goal}
            </p>
          </button>
        ))}
      </div>
    </div>
  );
}
