import type { StateDiff } from '../types';

interface Props {
  diffs: StateDiff[];
}

const SYSTEM_LABELS: Record<string, string> = {
  filesystem: 'File',
  email: 'Email',
  database: 'Database',
  http: 'HTTP',
};

export default function DiffView({ diffs }: Props) {
  if (diffs.length === 0) return null;

  return (
    <div className="space-y-2">
      {diffs.map((diff, i) => (
        <div key={i} className="bg-white rounded-lg border border-border p-3">
          <div className="flex items-center gap-2 mb-2">
            <span className="text-[11px] font-medium text-text-tertiary uppercase tracking-wide">
              {SYSTEM_LABELS[diff.system] ?? diff.system}
            </span>
            <span className={`text-[11px] font-medium ${
              diff.change_type === 'created' ? 'text-emerald-600' :
              diff.change_type === 'modified' ? 'text-amber-600' :
              'text-red-600'
            }`}>
              {diff.change_type}
            </span>
          </div>
          <div className="text-xs font-mono text-text-tertiary mb-2 break-all">{diff.resource_id}</div>

          {diff.before !== null && diff.before !== undefined && (
            <div className="mb-1.5">
              <pre className="text-xs bg-red-50/60 text-red-800 p-2 rounded overflow-auto max-h-28 font-mono leading-relaxed">
                {typeof diff.before === 'string' ? diff.before : JSON.stringify(diff.before, null, 2)}
              </pre>
            </div>
          )}

          <div>
            <pre className="text-xs bg-emerald-50/60 text-emerald-800 p-2 rounded overflow-auto max-h-28 font-mono leading-relaxed">
              {typeof diff.after === 'string' ? diff.after : JSON.stringify(diff.after, null, 2)}
            </pre>
          </div>
        </div>
      ))}
    </div>
  );
}
