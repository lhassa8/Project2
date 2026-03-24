import { useState } from 'react';
import { submitApproval, replayRun } from '../hooks/useApi';
import type { SandboxRun } from '../types';

interface Props {
  run: SandboxRun;
  onApproved: () => void;
  onReplayCreated?: (id: string) => void;
}

export default function ApprovalPanel({ run, onApproved, onReplayCreated }: Props) {
  const [notes, setNotes] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [replaying, setReplaying] = useState(false);
  const [replayResult, setReplayResult] = useState<{ id?: string; status?: string; message?: string } | null>(null);

  const handleSubmit = async (decision: 'approved' | 'changes_requested' | 'rejected') => {
    setSubmitting(true);
    try { await submitApproval(run.id, decision, notes); onApproved(); }
    catch (err) { console.error('Approval failed:', err); }
    finally { setSubmitting(false); }
  };

  const handleReplay = async (target: 'sandbox' | 'live') => {
    setReplaying(true);
    try {
      const result = await replayRun(run.id, target);
      setReplayResult(result);
      if (result.id && onReplayCreated) onReplayCreated(result.id);
    } catch (err) { console.error('Replay failed:', err); }
    finally { setReplaying(false); }
  };

  if (run.approval) {
    const a = run.approval;
    return (
      <div className="space-y-3">
        <div className={`rounded-lg border p-4 ${
          a.decision === 'approved' ? 'bg-emerald-50 border-emerald-100' :
          a.decision === 'rejected' ? 'bg-red-50 border-red-100' :
          'bg-amber-50 border-amber-100'
        }`}>
          <div className="text-[13px] font-medium mb-1 capitalize">
            {a.decision === 'changes_requested' ? 'Changes Requested' : a.decision}
          </div>
          {a.reviewer_notes && <p className="text-xs text-text-secondary mb-2">{a.reviewer_notes}</p>}
          <div className="text-[11px] text-text-tertiary space-y-0.5">
            <div>{new Date(a.approved_at).toLocaleString()}</div>
            <div className="font-mono break-all">Sig: {a.signature.slice(0, 32)}...</div>
          </div>
        </div>

        {a.decision === 'approved' && (
          <div className="bg-white rounded-lg border border-border p-4">
            <h4 className="text-[13px] font-medium text-text-primary mb-1">Replay</h4>
            <p className="text-xs text-text-tertiary mb-3">Re-run this agent in a sandbox or queue for live execution.</p>
            <div className="flex gap-2">
              <button onClick={() => handleReplay('sandbox')} disabled={replaying} className="flex-1 px-3 py-2 bg-text-primary text-white text-[13px] font-medium rounded-md hover:bg-black/80 disabled:opacity-40 transition-colors">
                {replaying ? 'Replaying...' : 'Replay in Sandbox'}
              </button>
              <button onClick={() => handleReplay('live')} disabled={replaying} className="flex-1 px-3 py-2 border border-border text-[13px] font-medium text-text-secondary rounded-md hover:bg-surface-secondary disabled:opacity-40 transition-colors">
                Queue Live
              </button>
            </div>
            {replayResult && (
              <div className="mt-2 p-2 bg-surface-secondary rounded-md text-xs text-text-secondary">
                {replayResult.id ? <>New run: <code className="font-mono">{replayResult.id}</code></> : replayResult.message}
              </div>
            )}
          </div>
        )}
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg border border-border p-4">
      <p className="text-[13px] text-text-secondary mb-3">Review this run and submit your decision.</p>
      <div className="mb-3">
        <label className="block text-xs text-text-tertiary mb-1">Reviewer Notes</label>
        <textarea
          value={notes}
          onChange={e => setNotes(e.target.value)}
          rows={3}
          placeholder="Optional notes..."
          className="w-full px-3 py-2 border border-border rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-accent/30 focus:border-accent resize-none bg-white"
        />
      </div>
      <div className="flex gap-2">
        <button onClick={() => handleSubmit('approved')} disabled={submitting} className="flex-1 px-3 py-2 bg-emerald-600 text-white text-[13px] font-medium rounded-md hover:bg-emerald-700 disabled:opacity-40 transition-colors">
          Approve
        </button>
        <button onClick={() => handleSubmit('changes_requested')} disabled={submitting} className="flex-1 px-3 py-2 bg-amber-500 text-white text-[13px] font-medium rounded-md hover:bg-amber-600 disabled:opacity-40 transition-colors">
          Changes
        </button>
        <button onClick={() => handleSubmit('rejected')} disabled={submitting} className="flex-1 px-3 py-2 bg-red-600 text-white text-[13px] font-medium rounded-md hover:bg-red-700 disabled:opacity-40 transition-colors">
          Reject
        </button>
      </div>
    </div>
  );
}
