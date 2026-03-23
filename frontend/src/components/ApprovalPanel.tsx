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
    try {
      await submitApproval(run.id, decision, notes);
      onApproved();
    } catch (err) {
      console.error('Approval failed:', err);
    } finally {
      setSubmitting(false);
    }
  };

  const handleReplay = async (target: 'sandbox' | 'live') => {
    setReplaying(true);
    try {
      const result = await replayRun(run.id, target);
      setReplayResult(result);
      if (result.id && onReplayCreated) {
        onReplayCreated(result.id);
      }
    } catch (err) {
      console.error('Replay failed:', err);
    } finally {
      setReplaying(false);
    }
  };

  if (run.approval) {
    const a = run.approval;
    const decisionStyle =
      a.decision === 'approved' ? 'bg-green-50 border-green-200' :
      a.decision === 'rejected' ? 'bg-red-50 border-red-200' :
      'bg-yellow-50 border-yellow-200';
    const decisionText =
      a.decision === 'approved' ? 'Approved' :
      a.decision === 'rejected' ? 'Rejected' :
      'Changes Requested';

    return (
      <div className="space-y-3">
        <div className={`rounded-lg border p-4 ${decisionStyle}`}>
          <div className="text-sm font-semibold mb-1">{decisionText}</div>
          {a.reviewer_notes && <p className="text-sm text-gray-600 mb-2">{a.reviewer_notes}</p>}
          <div className="text-xs text-gray-400 space-y-1">
            <div>At: {new Date(a.approved_at).toLocaleString()}</div>
            <div className="font-mono break-all">Sig: {a.signature.slice(0, 32)}...</div>
          </div>
        </div>

        {/* Replay controls (only for approved runs) */}
        {a.decision === 'approved' && (
          <div className="bg-white rounded-lg border border-gray-200 p-4">
            <h4 className="text-sm font-semibold text-gray-700 mb-2">Replay</h4>
            <p className="text-xs text-gray-500 mb-3">
              Re-run this approved agent against a sandbox or queue it for live execution.
            </p>
            <div className="flex gap-2">
              <button
                onClick={() => handleReplay('sandbox')}
                disabled={replaying}
                className="flex-1 px-3 py-2 bg-indigo-600 text-white text-sm font-medium rounded-lg hover:bg-indigo-700 disabled:opacity-50 transition-colors"
              >
                {replaying ? 'Replaying...' : 'Replay in Sandbox'}
              </button>
              <button
                onClick={() => handleReplay('live')}
                disabled={replaying}
                className="flex-1 px-3 py-2 border border-orange-300 text-orange-700 text-sm font-medium rounded-lg hover:bg-orange-50 disabled:opacity-50 transition-colors"
              >
                Queue Live Replay
              </button>
            </div>
            {replayResult && (
              <div className="mt-2 p-2 bg-gray-50 rounded text-xs text-gray-600">
                {replayResult.id ? (
                  <span>New run created: <code className="font-mono">{replayResult.id}</code></span>
                ) : (
                  <span>{replayResult.message}</span>
                )}
              </div>
            )}
          </div>
        )}
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg border border-gray-200 p-4">
      <p className="text-sm text-gray-600 mb-3">Review this run and submit your decision.</p>

      <div className="mb-3">
        <label className="block text-xs font-medium text-gray-500 mb-1">Reviewer Notes</label>
        <textarea
          value={notes}
          onChange={e => setNotes(e.target.value)}
          rows={3}
          placeholder="Optional notes..."
          className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent resize-none"
        />
      </div>

      <div className="flex gap-2">
        <button
          onClick={() => handleSubmit('approved')}
          disabled={submitting}
          className="flex-1 px-3 py-2 bg-green-600 text-white text-sm font-medium rounded-lg hover:bg-green-700 disabled:opacity-50 transition-colors"
        >
          Approve
        </button>
        <button
          onClick={() => handleSubmit('changes_requested')}
          disabled={submitting}
          className="flex-1 px-3 py-2 bg-yellow-500 text-white text-sm font-medium rounded-lg hover:bg-yellow-600 disabled:opacity-50 transition-colors"
        >
          Changes
        </button>
        <button
          onClick={() => handleSubmit('rejected')}
          disabled={submitting}
          className="flex-1 px-3 py-2 bg-red-600 text-white text-sm font-medium rounded-lg hover:bg-red-700 disabled:opacity-50 transition-colors"
        >
          Reject
        </button>
      </div>
    </div>
  );
}
