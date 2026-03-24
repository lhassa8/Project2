import { useState } from 'react';
import { useAuditLog } from '../hooks/useApi';

const EVENT_STYLES: Record<string, string> = {
  'run.created': 'bg-blue-50 text-blue-600',
  'run.completed': 'bg-emerald-50 text-emerald-600',
  'run.failed': 'bg-red-50 text-red-600',
  'approval.approved': 'bg-emerald-50 text-emerald-600',
  'approval.rejected': 'bg-red-50 text-red-600',
  'approval.submitted': 'bg-amber-50 text-amber-600',
  'policy.updated': 'bg-purple-50 text-purple-600',
  'api_key.created': 'bg-blue-50 text-blue-600',
  'api_key.revoked': 'bg-orange-50 text-orange-600',
  'run.replayed': 'bg-purple-50 text-purple-600',
  'run.exported': 'bg-gray-50 text-text-secondary',
};

export default function AuditLog() {
  const [filter, setFilter] = useState<string>('');
  const { events, total, loading, refresh } = useAuditLog(
    filter ? { event_type: filter, limit: 50 } : { limit: 50 }
  );

  const eventTypes = [
    '', 'run.created', 'run.completed', 'run.failed',
    'approval.approved', 'approval.rejected', 'approval.submitted',
    'policy.updated', 'api_key.created', 'api_key.revoked',
    'run.replayed', 'run.exported',
  ];

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-lg font-semibold text-text-primary">Audit Log</h2>
          <p className="text-[13px] text-text-tertiary mt-1">
            Immutable record of all actions.{total > 0 && ` ${total} events total.`}
          </p>
        </div>
        <div className="flex gap-2">
          <select
            value={filter}
            onChange={e => setFilter(e.target.value)}
            className="px-3 py-2 border border-border rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-accent/30 focus:border-accent bg-white"
          >
            <option value="">All events</option>
            {eventTypes.filter(Boolean).map(t => <option key={t} value={t}>{t}</option>)}
          </select>
          <button onClick={refresh} className="px-3 py-2 border border-border rounded-md text-[13px] text-text-secondary hover:bg-surface-secondary transition-colors">
            Refresh
          </button>
        </div>
      </div>

      {loading ? (
        <div className="text-center py-12 text-text-tertiary">Loading audit log...</div>
      ) : events.length === 0 ? (
        <div className="text-center py-12 text-text-tertiary">No audit events recorded yet.</div>
      ) : (
        <div className="bg-white rounded-lg border border-border overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border bg-surface-secondary">
                <th className="text-left px-4 py-3 text-[11px] font-medium text-text-tertiary uppercase tracking-wider">Time</th>
                <th className="text-left px-4 py-3 text-[11px] font-medium text-text-tertiary uppercase tracking-wider">Event</th>
                <th className="text-left px-4 py-3 text-[11px] font-medium text-text-tertiary uppercase tracking-wider">Actor</th>
                <th className="text-left px-4 py-3 text-[11px] font-medium text-text-tertiary uppercase tracking-wider">Resource</th>
                <th className="text-left px-4 py-3 text-[11px] font-medium text-text-tertiary uppercase tracking-wider">Details</th>
              </tr>
            </thead>
            <tbody>
              {events.map((event: any, i: number) => (
                <tr key={event.id ?? i} className="border-b border-border/50 hover:bg-surface-secondary/50">
                  <td className="px-4 py-3 text-xs text-text-tertiary whitespace-nowrap">
                    {event.timestamp ? new Date(event.timestamp).toLocaleString() : '-'}
                  </td>
                  <td className="px-4 py-3">
                    <span className={`text-[11px] px-1.5 py-0.5 rounded font-medium ${EVENT_STYLES[event.event_type] || 'bg-gray-50 text-text-secondary'}`}>
                      {event.event_type}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-xs text-text-secondary">{event.actor}</td>
                  <td className="px-4 py-3">
                    <span className="text-xs text-text-tertiary">{event.resource_type}</span>
                    {event.resource_id && <code className="ml-1 text-xs text-text-tertiary font-mono">{event.resource_id}</code>}
                  </td>
                  <td className="px-4 py-3 text-xs text-text-tertiary max-w-xs truncate">
                    {event.details ? JSON.stringify(event.details).slice(0, 80) : '-'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
