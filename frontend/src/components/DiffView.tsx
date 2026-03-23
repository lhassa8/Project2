import type { StateDiff } from '../types';

interface Props {
  diffs: StateDiff[];
}

const SYSTEM_STYLES: Record<string, string> = {
  filesystem: 'bg-blue-100 text-blue-700',
  email: 'bg-purple-100 text-purple-700',
  database: 'bg-amber-100 text-amber-700',
  http: 'bg-emerald-100 text-emerald-700',
};

const CHANGE_LABELS: Record<string, string> = {
  created: '+ Created',
  modified: '~ Modified',
  deleted: '- Deleted',
};

const CHANGE_STYLES: Record<string, string> = {
  created: 'text-green-600',
  modified: 'text-yellow-600',
  deleted: 'text-red-600',
};

export default function DiffView({ diffs }: Props) {
  if (diffs.length === 0) return null;

  return (
    <div className="space-y-3">
      {diffs.map((diff, i) => (
        <div key={i} className="bg-white rounded-lg border border-gray-200 p-4">
          <div className="flex items-center gap-2 mb-2">
            <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${SYSTEM_STYLES[diff.system] ?? 'bg-gray-100 text-gray-600'}`}>
              {diff.system}
            </span>
            <span className={`text-xs font-medium ${CHANGE_STYLES[diff.change_type]}`}>
              {CHANGE_LABELS[diff.change_type]}
            </span>
          </div>
          <div className="text-xs font-mono text-gray-500 mb-2 break-all">{diff.resource_id}</div>

          {diff.before !== null && diff.before !== undefined && (
            <div className="mb-2">
              <div className="text-xs font-medium text-red-500 mb-1">Before</div>
              <pre className="text-xs bg-red-50 text-red-800 p-2 rounded overflow-auto max-h-32 font-mono">
                {typeof diff.before === 'string' ? diff.before : JSON.stringify(diff.before, null, 2)}
              </pre>
            </div>
          )}

          <div>
            <div className="text-xs font-medium text-green-500 mb-1">After</div>
            <pre className="text-xs bg-green-50 text-green-800 p-2 rounded overflow-auto max-h-32 font-mono">
              {typeof diff.after === 'string' ? diff.after : JSON.stringify(diff.after, null, 2)}
            </pre>
          </div>
        </div>
      ))}
    </div>
  );
}
