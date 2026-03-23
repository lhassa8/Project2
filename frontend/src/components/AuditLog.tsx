import { useState } from 'react';
import { useAuditLog } from '../hooks/useApi';

const EVENT_STYLES: Record<string, string> = {
  'run.created': 'bg-blue-100 text-blue-700',
  'run.completed': 'bg-green-100 text-green-700',
  'run.failed': 'bg-red-100 text-red-700',
  'approval.approved': 'bg-green-100 text-green-700',
  'approval.rejected': 'bg-red-100 text-red-700',
  'approval.submitted': 'bg-yellow-100 text-yellow-700',
  'policy.updated': 'bg-purple-100 text-purple-700',
  'api_key.created': 'bg-indigo-100 text-indigo-700',
  'api_key.revoked': 'bg-orange-100 text-orange-700',
  'run.replayed': 'bg-violet-100 text-violet-700',
  'run.exported': 'bg-gray-100 text-gray-700',
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
          <h2 className="text-lg font-semibold text-gray-800">Audit Log</h2>
          <p className="text-sm text-gray-500 mt-1">
            Immutable record of all actions for compliance and forensics. {total > 0 && `${total} events total.`}
          </p>
        </div>
        <div className="flex gap-2">
          <select
            value={filter}
            onChange={e => setFilter(e.target.value)}
            className="px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
          >
            <option value="">All events</option>
            {eventTypes.filter(Boolean).map(t => (
              <option key={t} value={t}>{t}</option>
            ))}
          </select>
          <button
            onClick={refresh}
            className="px-3 py-2 border border-gray-300 rounded-lg text-sm text-gray-600 hover:bg-gray-50"
          >
            Refresh
          </button>
        </div>
      </div>

      {loading ? (
        <div className="text-center py-12 text-gray-400">Loading audit log...</div>
      ) : events.length === 0 ? (
        <div className="text-center py-12 text-gray-400">No audit events recorded yet.</div>
      ) : (
        <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-200 bg-gray-50">
                <th className="text-left px-4 py-3 text-xs font-medium text-gray-500 uppercase">Time</th>
                <th className="text-left px-4 py-3 text-xs font-medium text-gray-500 uppercase">Event</th>
                <th className="text-left px-4 py-3 text-xs font-medium text-gray-500 uppercase">Actor</th>
                <th className="text-left px-4 py-3 text-xs font-medium text-gray-500 uppercase">Resource</th>
                <th className="text-left px-4 py-3 text-xs font-medium text-gray-500 uppercase">Details</th>
              </tr>
            </thead>
            <tbody>
              {events.map((event: any, i: number) => {
                const style = EVENT_STYLES[event.event_type] || 'bg-gray-100 text-gray-600';
                return (
                  <tr key={event.id ?? i} className="border-b border-gray-100 hover:bg-gray-50">
                    <td className="px-4 py-3 text-xs text-gray-500 whitespace-nowrap">
                      {event.timestamp ? new Date(event.timestamp).toLocaleString() : '-'}
                    </td>
                    <td className="px-4 py-3">
                      <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${style}`}>
                        {event.event_type}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-xs text-gray-600">{event.actor}</td>
                    <td className="px-4 py-3">
                      <span className="text-xs text-gray-500">{event.resource_type}</span>
                      {event.resource_id && (
                        <code className="ml-1 text-xs text-gray-400 font-mono">{event.resource_id}</code>
                      )}
                    </td>
                    <td className="px-4 py-3 text-xs text-gray-500 max-w-xs truncate">
                      {event.details ? JSON.stringify(event.details).slice(0, 80) : '-'}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
