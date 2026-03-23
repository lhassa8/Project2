import { useEffect, useState } from 'react';
import { useRun, useRunStream, exportRun } from '../hooks/useApi';
import ActionTimeline from './ActionTimeline';
import DiffView from './DiffView';
import ApprovalPanel from './ApprovalPanel';
import RiskPanel from './RiskPanel';
import StatusBadge from './StatusBadge';

interface Props {
  runId: string;
  onBack: () => void;
  onViewRun?: (id: string) => void;
  onCompare?: (runId: string) => void;
}

export default function RunDetail({ runId, onBack, onViewRun, onCompare }: Props) {
  const { run, loading, refresh } = useRun(runId);
  const stream = useRunStream(runId);
  const [exporting, setExporting] = useState(false);
  const [showSnapshot, setShowSnapshot] = useState<'initial' | 'final' | null>(null);

  const actions = stream.actions.length > 0 ? stream.actions : (run?.actions ?? []);
  const status = stream.status !== 'running' ? stream.status : (run?.status ?? 'running');
  const riskReport = stream.riskReport ?? run?.risk_report ?? null;
  const policyViolations = stream.policyViolations.length > 0
    ? stream.policyViolations
    : (run?.policy_violations ?? []);

  useEffect(() => {
    if (stream.status === 'complete' || stream.status === 'failed') {
      refresh();
    }
  }, [stream.status, refresh]);

  const handleExport = async () => {
    setExporting(true);
    try {
      const artifact = await exportRun(runId);
      const blob = new Blob([JSON.stringify(artifact, null, 2)], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `sandbox-run-${runId}-audit.json`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      console.error('Export failed:', err);
    } finally {
      setExporting(false);
    }
  };

  if (loading && !run) {
    return <div className="text-center py-12 text-gray-500">Loading run...</div>;
  }
  if (!run) {
    return <div className="text-center py-12 text-gray-500">Run not found</div>;
  }

  const snapshot = showSnapshot === 'initial' ? run.initial_snapshot : showSnapshot === 'final' ? run.final_snapshot : null;

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <button onClick={onBack} className="text-sm text-indigo-600 hover:text-indigo-800">
          &larr; Back to runs
        </button>
        <div className="flex gap-2">
          {onCompare && status === 'complete' && (
            <button
              onClick={() => onCompare(runId)}
              className="px-3 py-1.5 border border-indigo-300 text-sm text-indigo-600 rounded-lg hover:bg-indigo-50 transition-colors"
            >
              Compare
            </button>
          )}
          <button
            onClick={handleExport}
            disabled={exporting}
            className="px-3 py-1.5 border border-gray-300 text-sm text-gray-600 rounded-lg hover:bg-gray-50 disabled:opacity-50 transition-colors"
          >
            {exporting ? 'Exporting...' : 'Export Audit'}
          </button>
        </div>
      </div>

      {/* Run header */}
      <div className="bg-white rounded-xl border border-gray-200 p-5 mb-6">
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
        {/* Main timeline */}
        <div className="lg:col-span-2">
          <h3 className="text-sm font-semibold text-gray-700 uppercase tracking-wide mb-3">
            Action Timeline ({actions.length})
          </h3>
          <ActionTimeline actions={actions} />
        </div>

        {/* Sidebar */}
        <div className="space-y-6">
          {/* Risk panel */}
          {(riskReport || policyViolations.length > 0) && (
            <div>
              <h3 className="text-sm font-semibold text-gray-700 uppercase tracking-wide mb-3">
                Risk & Compliance
              </h3>
              <RiskPanel riskReport={riskReport} policyViolations={policyViolations} />
            </div>
          )}

          {/* Environment snapshots */}
          {(run.initial_snapshot || run.final_snapshot) && (
            <div>
              <h3 className="text-sm font-semibold text-gray-700 uppercase tracking-wide mb-3">
                Environment
              </h3>
              <div className="bg-white rounded-lg border border-gray-200 p-4">
                <div className="flex gap-2 mb-3">
                  <button
                    onClick={() => setShowSnapshot(showSnapshot === 'initial' ? null : 'initial')}
                    className={`text-xs px-3 py-1.5 rounded-lg font-medium border transition-colors ${
                      showSnapshot === 'initial'
                        ? 'bg-indigo-50 border-indigo-300 text-indigo-700'
                        : 'bg-gray-50 border-gray-200 text-gray-500 hover:border-gray-300'
                    }`}
                  >
                    Initial State
                  </button>
                  {run.final_snapshot && (
                    <button
                      onClick={() => setShowSnapshot(showSnapshot === 'final' ? null : 'final')}
                      className={`text-xs px-3 py-1.5 rounded-lg font-medium border transition-colors ${
                        showSnapshot === 'final'
                          ? 'bg-indigo-50 border-indigo-300 text-indigo-700'
                          : 'bg-gray-50 border-gray-200 text-gray-500 hover:border-gray-300'
                      }`}
                    >
                      Final State
                    </button>
                  )}
                </div>
                {snapshot && (
                  <div className="space-y-3">
                    {Object.keys(snapshot.filesystem || {}).length > 0 && (
                      <div>
                        <div className="text-xs font-medium text-gray-500 mb-1">
                          Files ({Object.keys(snapshot.filesystem).length})
                        </div>
                        {Object.keys(snapshot.filesystem).map(path => (
                          <div key={path} className="text-xs text-gray-600 font-mono">{path}</div>
                        ))}
                      </div>
                    )}
                    {Object.keys(snapshot.database || {}).length > 0 && (
                      <div>
                        <div className="text-xs font-medium text-gray-500 mb-1">
                          Tables ({Object.keys(snapshot.database).length})
                        </div>
                        {Object.entries(snapshot.database).map(([table, rows]) => (
                          <div key={table} className="text-xs text-gray-600">
                            <span className="font-mono">{table}</span>
                            <span className="text-gray-400"> ({(rows as unknown[]).length} rows)</span>
                          </div>
                        ))}
                      </div>
                    )}
                    {(snapshot.emails_sent || []).length > 0 && (
                      <div className="text-xs text-gray-600">
                        Emails sent: {snapshot.emails_sent.length}
                      </div>
                    )}
                  </div>
                )}
              </div>
            </div>
          )}

          {/* State diffs */}
          {run.diffs && run.diffs.length > 0 && (
            <div>
              <h3 className="text-sm font-semibold text-gray-700 uppercase tracking-wide mb-3">
                State Changes ({run.diffs.length})
              </h3>
              <DiffView diffs={run.diffs} />
            </div>
          )}

          {/* Approval */}
          {status === 'complete' && (
            <div>
              <h3 className="text-sm font-semibold text-gray-700 uppercase tracking-wide mb-3">
                Approval
              </h3>
              <ApprovalPanel
                run={run}
                onApproved={refresh}
                onReplayCreated={onViewRun}
              />
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
