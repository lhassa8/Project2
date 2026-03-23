import { usePolicies } from '../hooks/useApi';

const ACTION_STYLES: Record<string, { bg: string; text: string }> = {
  allow: { bg: 'bg-green-100', text: 'text-green-700' },
  warn: { bg: 'bg-yellow-100', text: 'text-yellow-700' },
  block: { bg: 'bg-red-100', text: 'text-red-700' },
  require_approval: { bg: 'bg-orange-100', text: 'text-orange-700' },
};

export default function PoliciesView() {
  const { policies, loading } = usePolicies();

  if (loading) {
    return <div className="text-center py-12 text-gray-400">Loading policies...</div>;
  }

  return (
    <div>
      <div className="mb-6">
        <h2 className="text-lg font-semibold text-gray-800">Security Policies</h2>
        <p className="text-sm text-gray-500 mt-1">
          Configurable rules that are evaluated in real-time during agent execution.
          Policies can warn, block, or require approval for specific actions.
        </p>
      </div>

      <div className="space-y-3">
        {policies.map(policy => {
          const style = ACTION_STYLES[policy.action] ?? ACTION_STYLES.warn;
          return (
            <div
              key={policy.name}
              className="bg-white rounded-xl border border-gray-200 p-5 flex items-start justify-between gap-4"
            >
              <div className="flex-1">
                <div className="flex items-center gap-2 mb-1">
                  <h3 className="text-sm font-semibold text-gray-900">
                    {policy.name.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())}
                  </h3>
                  <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${style.bg} ${style.text}`}>
                    {policy.action.replace(/_/g, ' ')}
                  </span>
                </div>
                <p className="text-sm text-gray-500">{policy.description}</p>
              </div>
              <div className="flex items-center gap-2">
                <span className={`w-2.5 h-2.5 rounded-full ${policy.enabled ? 'bg-green-400' : 'bg-gray-300'}`} />
                <span className="text-xs text-gray-500">{policy.enabled ? 'Active' : 'Disabled'}</span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
