import { useState } from 'react';
import { usePolicies, createPolicy, updatePolicy, deletePolicy } from '../hooks/useApi';

const ACTION_STYLES: Record<string, { bg: string; text: string }> = {
  allow: { bg: 'bg-green-100', text: 'text-green-700' },
  warn: { bg: 'bg-yellow-100', text: 'text-yellow-700' },
  block: { bg: 'bg-red-100', text: 'text-red-700' },
  require_approval: { bg: 'bg-orange-100', text: 'text-orange-700' },
};

export default function PoliciesView() {
  const { builtin, custom, loading, refresh } = usePolicies();
  const [showCreate, setShowCreate] = useState(false);
  const [newPolicy, setNewPolicy] = useState({
    name: '',
    description: '',
    action: 'warn',
    tool_name: '',
    pattern: '',
    target_field: '',
  });
  const [creating, setCreating] = useState(false);

  const handleCreate = async () => {
    if (!newPolicy.name.trim() || !newPolicy.description.trim()) return;
    setCreating(true);
    try {
      await createPolicy({
        name: newPolicy.name,
        description: newPolicy.description,
        action: newPolicy.action,
        tool_name: newPolicy.tool_name || undefined,
        pattern: newPolicy.pattern || undefined,
        target_field: newPolicy.target_field || undefined,
      });
      setNewPolicy({ name: '', description: '', action: 'warn', tool_name: '', pattern: '', target_field: '' });
      setShowCreate(false);
      refresh();
    } catch (err) {
      console.error('Failed to create policy:', err);
    } finally {
      setCreating(false);
    }
  };

  const handleToggle = async (id: number, currentlyEnabled: boolean) => {
    await updatePolicy(id, { enabled: !currentlyEnabled });
    refresh();
  };

  const handleDelete = async (id: number) => {
    await deletePolicy(id);
    refresh();
  };

  if (loading) {
    return <div className="text-center py-12 text-gray-400">Loading policies...</div>;
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-lg font-semibold text-gray-800">Security Policies</h2>
          <p className="text-sm text-gray-500 mt-1">
            Rules evaluated in real-time during agent execution. Built-in policies ship with defaults; custom policies are workspace-specific.
          </p>
        </div>
        <button
          onClick={() => setShowCreate(!showCreate)}
          className="px-4 py-2 bg-gradient-to-r from-indigo-600 to-violet-600 text-white text-sm font-medium rounded-lg hover:from-indigo-700 hover:to-violet-700 transition-all shadow-sm"
        >
          {showCreate ? 'Cancel' : 'New Policy'}
        </button>
      </div>

      {/* Create policy form */}
      {showCreate && (
        <div className="bg-white rounded-xl border border-indigo-200 p-5 mb-6 space-y-3">
          <h3 className="text-sm font-semibold text-gray-700">Create Custom Policy</h3>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-medium text-gray-500 mb-1">Name</label>
              <input
                type="text"
                value={newPolicy.name}
                onChange={e => setNewPolicy(p => ({ ...p, name: e.target.value }))}
                placeholder="e.g. no_pii_in_emails"
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-500 mb-1">Action</label>
              <select
                value={newPolicy.action}
                onChange={e => setNewPolicy(p => ({ ...p, action: e.target.value }))}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
              >
                <option value="warn">Warn</option>
                <option value="block">Block</option>
                <option value="require_approval">Require Approval</option>
              </select>
            </div>
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-500 mb-1">Description</label>
            <input
              type="text"
              value={newPolicy.description}
              onChange={e => setNewPolicy(p => ({ ...p, description: e.target.value }))}
              placeholder="What does this policy enforce?"
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
            />
          </div>
          <div className="grid grid-cols-3 gap-3">
            <div>
              <label className="block text-xs font-medium text-gray-500 mb-1">Tool (optional)</label>
              <select
                value={newPolicy.tool_name}
                onChange={e => setNewPolicy(p => ({ ...p, tool_name: e.target.value }))}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
              >
                <option value="">All tools</option>
                <option value="read_file">read_file</option>
                <option value="write_file">write_file</option>
                <option value="send_email">send_email</option>
                <option value="http_request">http_request</option>
                <option value="query_database">query_database</option>
              </select>
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-500 mb-1">Target Field</label>
              <select
                value={newPolicy.target_field}
                onChange={e => setNewPolicy(p => ({ ...p, target_field: e.target.value }))}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
              >
                <option value="">Any</option>
                <option value="path">path</option>
                <option value="url">url</option>
                <option value="query">query</option>
                <option value="to">to (email)</option>
                <option value="body">body</option>
              </select>
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-500 mb-1">Pattern (regex)</label>
              <input
                type="text"
                value={newPolicy.pattern}
                onChange={e => setNewPolicy(p => ({ ...p, pattern: e.target.value }))}
                placeholder="e.g. prod\\..*\\.com"
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-xs font-mono focus:outline-none focus:ring-2 focus:ring-indigo-500"
              />
            </div>
          </div>
          <div className="flex justify-end">
            <button
              onClick={handleCreate}
              disabled={creating || !newPolicy.name.trim() || !newPolicy.description.trim()}
              className="px-4 py-2 bg-indigo-600 text-white text-sm font-medium rounded-lg hover:bg-indigo-700 disabled:opacity-50 transition-colors"
            >
              {creating ? 'Creating...' : 'Create Policy'}
            </button>
          </div>
        </div>
      )}

      {/* Built-in policies */}
      <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wide mb-3">Built-in Policies</h3>
      <div className="space-y-2 mb-8">
        {builtin.map(policy => {
          const style = ACTION_STYLES[policy.action] ?? ACTION_STYLES.warn;
          return (
            <div
              key={policy.name}
              className="bg-white rounded-xl border border-gray-200 p-5 flex items-start justify-between gap-4"
            >
              <div className="flex-1">
                <div className="flex items-center gap-2 mb-1">
                  <h3 className="text-sm font-semibold text-gray-900">
                    {policy.name.replace(/_/g, ' ').replace(/\b\w/g, (c: string) => c.toUpperCase())}
                  </h3>
                  <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${style.bg} ${style.text}`}>
                    {policy.action.replace(/_/g, ' ')}
                  </span>
                  <span className="text-xs px-2 py-0.5 rounded-full bg-gray-100 text-gray-500">built-in</span>
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

      {/* Custom policies */}
      {custom.length > 0 && (
        <>
          <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wide mb-3">Custom Policies</h3>
          <div className="space-y-2">
            {custom.map((policy: any) => {
              const style = ACTION_STYLES[policy.action] ?? ACTION_STYLES.warn;
              return (
                <div
                  key={policy.id}
                  className="bg-white rounded-xl border border-indigo-100 p-5 flex items-start justify-between gap-4"
                >
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-1">
                      <h3 className="text-sm font-semibold text-gray-900">
                        {policy.name.replace(/_/g, ' ').replace(/\b\w/g, (c: string) => c.toUpperCase())}
                      </h3>
                      <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${style.bg} ${style.text}`}>
                        {policy.action.replace(/_/g, ' ')}
                      </span>
                      <span className="text-xs px-2 py-0.5 rounded-full bg-indigo-50 text-indigo-600">custom</span>
                    </div>
                    <p className="text-sm text-gray-500">{policy.description}</p>
                    {(policy.tool_name || policy.pattern) && (
                      <div className="flex gap-3 mt-1.5 text-xs text-gray-400">
                        {policy.tool_name && <span>Tool: <code>{policy.tool_name}</code></span>}
                        {policy.target_field && <span>Field: <code>{policy.target_field}</code></span>}
                        {policy.pattern && <span>Pattern: <code className="font-mono">{policy.pattern}</code></span>}
                      </div>
                    )}
                  </div>
                  <div className="flex items-center gap-3">
                    <button
                      onClick={() => handleToggle(policy.id, policy.enabled)}
                      className={`text-xs px-3 py-1 rounded-lg border transition-colors ${
                        policy.enabled
                          ? 'border-green-300 text-green-700 bg-green-50 hover:bg-green-100'
                          : 'border-gray-300 text-gray-500 bg-gray-50 hover:bg-gray-100'
                      }`}
                    >
                      {policy.enabled ? 'Active' : 'Disabled'}
                    </button>
                    <button
                      onClick={() => handleDelete(policy.id)}
                      className="text-xs text-red-500 hover:text-red-700"
                    >
                      Delete
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        </>
      )}
    </div>
  );
}
