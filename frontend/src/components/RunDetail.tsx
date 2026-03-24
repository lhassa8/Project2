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
    return <div className="text-center py-12 text-text-tertiary">Loading run...</div>;
  }
  if (!run) {
    return <div className="text-center py-12 text-text-tertiary">Run not found</div>;
  }

  const snapshot = showSnapshot === 'initial' ? run.initial_snapshot : showSnapshot === 'final' ? run.final_snapshot : null;

  return (
    <div>
      <div className="flex items-center justify-between mb-5">
        <button onClick={onBack} className="text-[13px] text-text-tertiary hover:text-text-secondary">
          &larr; Back to runs
        </button>
        <div className="flex gap-2">
          {onCompare && status === 'complete' && (
            <button
              onClick={() => onCompare(runId)}
              className="px-3 py-1.5 border border-border text-[13px] text-text-secondary rounded-md hover:bg-surface-secondary transition-colors"
            >
              Compare
            </button>
          )}
          <button
            onClick={handleExport}
            disabled={exporting}
            className="px-3 py-1.5 border border-border text-[13px] text-text-secondary rounded-md hover:bg-surface-secondary disabled:opacity-50 transition-colors"
          >
            {exporting ? 'Exporting...' : 'Export'}
          </button>
        </div>
      </div>

      {/* Run header */}
      <div className="bg-white rounded-lg border border-border p-5 mb-6">
        <div className="flex items-center justify-between mb-2">
          <div className="flex items-center gap-3">
            <h2 className="text-lg font-semibold text-text-primary">{run.agent_definition.name}</h2>
            <StatusBadge status={status} />
          </div>
          <span className="text-xs text-text-tertiary">{new Date(run.created_at).toLocaleString()}</span>
        </div>
        <p className="text-[13px] text-text-secondary mb-2">{run.agent_definition.goal}</p>
        <div className="flex gap-4 text-xs text-text-tertiary">
          <span>Model: {run.agent_definition.model}</span>
          <span>Persona: {run.run_context.user_persona}</span>
          <span className="font-mono">{run.id}</span>
        </div>
        {run.error && (
          <div className="mt-3 p-3 bg-red-50 border border-red-100 rounded-md text-[13px] text-red-700">
            {run.error}
          </div>
        )}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2">
          <h3 className="text-[11px] font-medium text-text-tertiary uppercase tracking-wider mb-3">
            Action Timeline ({actions.length})
          </h3>
          <ActionTimeline actions={actions} />
        </div>

        <div className="space-y-6">
          {(riskReport || policyViolations.length > 0) && (
            <div>
              <h3 className="text-[11px] font-medium text-text-tertiary uppercase tracking-wider mb-3">
                Risk & Compliance
              </h3>
              <RiskPanel riskReport={riskReport} policyViolations={policyViolations} />
            </div>
          )}

          {(run.initial_snapshot || run.final_snapshot) && (
            <div>
              <h3 className="text-[11px] font-medium text-text-tertiary uppercase tracking-wider mb-3">
                Environment
              </h3>
              <div className="bg-white rounded-lg border border-border p-4">
                <div className="flex gap-2 mb-3">
                  {['initial', 'final'].map(type => {
                    const snap = type === 'initial' ? run.initial_snapshot : run.final_snapshot;
                    if (!snap) return null;
                    return (
                      <button
                        key={type}
                        onClick={() => setShowSnapshot(showSnapshot === type ? null : type as 'initial' | 'final')}
                        className={`text-xs px-3 py-1.5 rounded-md font-medium border transition-colors ${
                          showSnapshot === type
                            ? 'bg-accent-light border-accent/30 text-accent-dark'
                            : 'bg-surface-secondary border-border text-text-tertiary hover:text-text-secondary'
                        }`}
                      >
                        {type === 'initial' ? 'Initial' : 'Final'} State
                      </button>
                    );
                  })}
                </div>
                {snapshot && (
                  <div className="space-y-3">
                    {Object.keys(snapshot.filesystem || {}).length > 0 && (
                      <div>
                        <div className="text-[11px] font-medium text-text-tertiary mb-1">Files ({Object.keys(snapshot.filesystem).length})</div>
                        {Object.keys(snapshot.filesystem).map(path => (
                          <div key={path} className="text-xs text-text-secondary font-mono">{path}</div>
                        ))}
                      </div>
                    )}
                    {Object.keys(snapshot.database || {}).length > 0 && (
                      <div>
                        <div className="text-[11px] font-medium text-text-tertiary mb-1">Tables ({Object.keys(snapshot.database).length})</div>
                        {Object.entries(snapshot.database).map(([table, rows]) => (
                          <div key={table} className="text-xs text-text-secondary">
                            <span className="font-mono">{table}</span>
                            <span className="text-text-tertiary"> ({(rows as unknown[]).length} rows)</span>
                          </div>
                        ))}
                      </div>
                    )}
                    {(snapshot.emails_sent || []).length > 0 && (
                      <div className="text-xs text-text-secondary">
                        Emails sent: {snapshot.emails_sent.length}
                      </div>
                    )}
                  </div>
                )}
              </div>
            </div>
          )}

          {run.diffs && run.diffs.length > 0 && (
            <div>
              <h3 className="text-[11px] font-medium text-text-tertiary uppercase tracking-wider mb-3">
                State Changes ({run.diffs.length})
              </h3>
              <DiffView diffs={run.diffs} />
            </div>
          )}

          {status === 'complete' && (
            <div>
              <h3 className="text-[11px] font-medium text-text-tertiary uppercase tracking-wider mb-3">
                Approval
              </h3>
              <ApprovalPanel run={run} onApproved={refresh} onReplayCreated={onViewRun} />
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
