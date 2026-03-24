import { useState } from 'react';
import { usePolicies, createPolicy, updatePolicy, deletePolicy } from '../hooks/useApi';

const ACTION_STYLES: Record<string, string> = {
  allow: 'bg-emerald-50 text-emerald-600',
  warn: 'bg-amber-50 text-amber-600',
  block: 'bg-red-50 text-red-600',
  require_approval: 'bg-orange-50 text-orange-600',
};

export default function PoliciesView() {
  const { builtin, custom, loading, refresh } = usePolicies();
  const [showCreate, setShowCreate] = useState(false);
  const [newPolicy, setNewPolicy] = useState({ name: '', description: '', action: 'warn', tool_name: '', pattern: '', target_field: '' });
  const [creating, setCreating] = useState(false);

  const handleCreate = async () => {
    if (!newPolicy.name.trim() || !newPolicy.description.trim()) return;
    setCreating(true);
    try {
      await createPolicy({
        name: newPolicy.name, description: newPolicy.description, action: newPolicy.action,
        tool_name: newPolicy.tool_name || undefined, pattern: newPolicy.pattern || undefined, target_field: newPolicy.target_field || undefined,
      });
      setNewPolicy({ name: '', description: '', action: 'warn', tool_name: '', pattern: '', target_field: '' });
      setShowCreate(false);
      refresh();
    } catch (err) { console.error('Failed to create policy:', err); }
    finally { setCreating(false); }
  };

  const handleToggle = async (id: number, enabled: boolean) => { await updatePolicy(id, { enabled: !enabled }); refresh(); };
  const handleDelete = async (id: number) => { await deletePolicy(id); refresh(); };

  if (loading) return <div className="text-center py-12 text-text-tertiary">Loading policies...</div>;

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-lg font-semibold text-text-primary">Security Policies</h2>
          <p className="text-[13px] text-text-tertiary mt-1">Rules evaluated during agent execution.</p>
        </div>
        <button onClick={() => setShowCreate(!showCreate)} className="px-4 py-1.5 bg-text-primary text-white text-[13px] font-medium rounded-md hover:bg-black/80 transition-colors">
          {showCreate ? 'Cancel' : 'New Policy'}
        </button>
      </div>

      {showCreate && (
        <div className="bg-white rounded-lg border border-border p-5 mb-6 space-y-3">
          <h3 className="text-[13px] font-medium text-text-primary">Create Custom Policy</h3>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs text-text-tertiary mb-1">Name</label>
              <input type="text" value={newPolicy.name} onChange={e => setNewPolicy(p => ({ ...p, name: e.target.value }))} placeholder="e.g. no_pii_in_emails" className="w-full px-3 py-2 border border-border rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-accent/30 focus:border-accent bg-white" />
            </div>
            <div>
              <label className="block text-xs text-text-tertiary mb-1">Action</label>
              <select value={newPolicy.action} onChange={e => setNewPolicy(p => ({ ...p, action: e.target.value }))} className="w-full px-3 py-2 border border-border rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-accent/30 focus:border-accent bg-white">
                <option value="warn">Warn</option><option value="block">Block</option><option value="require_approval">Require Approval</option>
              </select>
            </div>
          </div>
          <div>
            <label className="block text-xs text-text-tertiary mb-1">Description</label>
            <input type="text" value={newPolicy.description} onChange={e => setNewPolicy(p => ({ ...p, description: e.target.value }))} placeholder="What does this policy enforce?" className="w-full px-3 py-2 border border-border rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-accent/30 focus:border-accent bg-white" />
          </div>
          <div className="grid grid-cols-3 gap-3">
            <div>
              <label className="block text-xs text-text-tertiary mb-1">Tool (optional)</label>
              <select value={newPolicy.tool_name} onChange={e => setNewPolicy(p => ({ ...p, tool_name: e.target.value }))} className="w-full px-3 py-2 border border-border rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-accent/30 focus:border-accent bg-white">
                <option value="">All tools</option><option value="read_file">read_file</option><option value="write_file">write_file</option><option value="send_email">send_email</option><option value="http_request">http_request</option><option value="query_database">query_database</option>
              </select>
            </div>
            <div>
              <label className="block text-xs text-text-tertiary mb-1">Target Field</label>
              <select value={newPolicy.target_field} onChange={e => setNewPolicy(p => ({ ...p, target_field: e.target.value }))} className="w-full px-3 py-2 border border-border rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-accent/30 focus:border-accent bg-white">
                <option value="">Any</option><option value="path">path</option><option value="url">url</option><option value="query">query</option><option value="to">to</option><option value="body">body</option>
              </select>
            </div>
            <div>
              <label className="block text-xs text-text-tertiary mb-1">Pattern (regex)</label>
              <input type="text" value={newPolicy.pattern} onChange={e => setNewPolicy(p => ({ ...p, pattern: e.target.value }))} placeholder="e.g. prod\..*\.com" className="w-full px-3 py-2 border border-border rounded-md text-xs font-mono focus:outline-none focus:ring-2 focus:ring-accent/30 focus:border-accent bg-white" />
            </div>
          </div>
          <div className="flex justify-end">
            <button onClick={handleCreate} disabled={creating || !newPolicy.name.trim() || !newPolicy.description.trim()} className="px-4 py-2 bg-text-primary text-white text-[13px] font-medium rounded-md hover:bg-black/80 disabled:opacity-40 transition-colors">
              {creating ? 'Creating...' : 'Create Policy'}
            </button>
          </div>
        </div>
      )}

      <h3 className="text-[11px] font-medium text-text-tertiary uppercase tracking-wider mb-3">Built-in Policies</h3>
      <div className="space-y-2 mb-8">
        {builtin.map(policy => (
          <div key={policy.name} className="bg-white rounded-lg border border-border p-4 flex items-start justify-between gap-4">
            <div className="flex-1">
              <div className="flex items-center gap-2 mb-1">
                <h3 className="text-[13px] font-medium text-text-primary">{policy.name.replace(/_/g, ' ').replace(/\b\w/g, (c: string) => c.toUpperCase())}</h3>
                <span className={`text-[11px] px-1.5 py-0.5 rounded font-medium ${ACTION_STYLES[policy.action] ?? 'bg-gray-50 text-text-secondary'}`}>{policy.action.replace(/_/g, ' ')}</span>
              </div>
              <p className="text-xs text-text-tertiary">{policy.description}</p>
            </div>
            <div className="flex items-center gap-2">
              <span className={`w-2 h-2 rounded-full ${policy.enabled ? 'bg-emerald-400' : 'bg-gray-300'}`} />
              <span className="text-xs text-text-tertiary">{policy.enabled ? 'Active' : 'Off'}</span>
            </div>
          </div>
        ))}
      </div>

      {custom.length > 0 && (
        <>
          <h3 className="text-[11px] font-medium text-text-tertiary uppercase tracking-wider mb-3">Custom Policies</h3>
          <div className="space-y-2">
            {custom.map((policy: any) => (
              <div key={policy.id} className="bg-white rounded-lg border border-border p-4 flex items-start justify-between gap-4">
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-1">
                    <h3 className="text-[13px] font-medium text-text-primary">{policy.name.replace(/_/g, ' ').replace(/\b\w/g, (c: string) => c.toUpperCase())}</h3>
                    <span className={`text-[11px] px-1.5 py-0.5 rounded font-medium ${ACTION_STYLES[policy.action] ?? 'bg-gray-50 text-text-secondary'}`}>{policy.action.replace(/_/g, ' ')}</span>
                  </div>
                  <p className="text-xs text-text-tertiary">{policy.description}</p>
                  {(policy.tool_name || policy.pattern) && (
                    <div className="flex gap-3 mt-1 text-xs text-text-tertiary font-mono">
                      {policy.tool_name && <span>{policy.tool_name}</span>}
                      {policy.pattern && <span>{policy.pattern}</span>}
                    </div>
                  )}
                </div>
                <div className="flex items-center gap-3">
                  <button onClick={() => handleToggle(policy.id, policy.enabled)} className={`text-xs px-2.5 py-1 rounded-md border transition-colors ${policy.enabled ? 'border-emerald-200 text-emerald-600 hover:bg-emerald-50' : 'border-border text-text-tertiary hover:bg-surface-secondary'}`}>
                    {policy.enabled ? 'Active' : 'Off'}
                  </button>
                  <button onClick={() => handleDelete(policy.id)} className="text-xs text-red-500 hover:text-red-600">Delete</button>
                </div>
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  );
}
