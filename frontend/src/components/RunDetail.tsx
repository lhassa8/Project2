import { useEffect } from 'react';
import { useRun, useRunStream } from '../hooks/useApi';
import ActionTimeline from './ActionTimeline';
import DiffView from './DiffView';
import ApprovalPanel from './ApprovalPanel';
import StatusBadge from './StatusBadge';

interface Props {
  runId: string;
  onBack: () => void;
}

export default function RunDetail({ runId, onBack }: Props) {
  const { run, loading, refresh, setRun } = useRun(runId);
  const stream = useRunStream(runId);

  // Merge streamed actions into the run
  const actions = stream.actions.length > 0 ? stream.actions : (run?.actions ?? []);
  const status = stream.status !== 'running' ? stream.status : (run?.status ?? 'running');

  // Refresh when stream completes
  useEffect(() => {
    if (stream.status === 'complete' || stream.status === 'failed') {
      refresh();
    }
  }, [stream.status, refresh]);

  if (loading && !run) {
    return <div className="text-center py-12 text-gray-500">Loading run...</div>;
  }

  if (!run) {
    return <div className="text-center py-12 text-gray-500">Run not found</div>;
  }

  return (
    <div>
      <button
        onClick={onBack}
        className="text-sm text-indigo-600 hover:text-indigo-800 mb-4 inline-block"
      >
        &larr; Back to runs
      </button>

      <div className="bg-white rounded-lg border border-gray-200 p-5 mb-6">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-3">
            <h2 className="text-lg font-semibold text-gray-900">{run.agent_definition.name}</h2>
            <StatusBadge status={status} />
            <span className="text-sm text-gray-400 font-mono">{run.id}</span>
          </div>
          <span className="text-sm text-gray-500">{new Date(run.created_at).toLocaleString()}</span>
        </div>
        <p className="text-sm text-gray-600 mb-2">{run.agent_definition.goal}</p>
        <div className="flex gap-4 text-xs text-gray-400">
          <span>Model: {run.agent_definition.model}</span>
          <span>Persona: {run.run_context.user_persona}</span>
          <span>Tools: {run.agent_definition.tools.filter(t => t.enabled).map(t => t.name).join(', ')}</span>
        </div>
        {run.error && (
          <div className="mt-3 p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">
            {run.error}
          </div>
        )}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2">
          <h3 className="text-sm font-semibold text-gray-700 uppercase tracking-wide mb-3">
            Action Timeline
          </h3>
          <ActionTimeline actions={actions} />
        </div>

        <div className="space-y-6">
          {run.diffs && run.diffs.length > 0 && (
            <div>
              <h3 className="text-sm font-semibold text-gray-700 uppercase tracking-wide mb-3">
                State Changes
              </h3>
              <DiffView diffs={run.diffs} />
            </div>
          )}

          {status === 'complete' && (
            <div>
              <h3 className="text-sm font-semibold text-gray-700 uppercase tracking-wide mb-3">
                Approval
              </h3>
              <ApprovalPanel run={run} onApproved={refresh} />
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
