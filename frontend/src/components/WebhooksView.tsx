import { useState } from 'react';
import { useWebhooks, createWebhook, deleteWebhook, testWebhook } from '../hooks/useApi';

const AVAILABLE_EVENTS = ['run.completed', 'run.failed', 'approval.submitted', 'policy.violation', 'risk.critical', 'risk.high'];

export default function WebhooksView() {
  const { webhooks, loading, refresh } = useWebhooks();
  const [showCreate, setShowCreate] = useState(false);
  const [newHook, setNewHook] = useState({ name: '', url: '', secret: '', events: [] as string[] });
  const [creating, setCreating] = useState(false);
  const [testing, setTesting] = useState<number | null>(null);
  const [testResult, setTestResult] = useState<{ id: number; success: boolean; status_code?: number } | null>(null);

  const toggleEvent = (event: string) => {
    setNewHook(prev => ({ ...prev, events: prev.events.includes(event) ? prev.events.filter(e => e !== event) : [...prev.events, event] }));
  };

  const handleCreate = async () => {
    if (!newHook.name.trim() || !newHook.url.trim() || newHook.events.length === 0) return;
    setCreating(true);
    try { await createWebhook({ name: newHook.name, url: newHook.url, events: newHook.events, secret: newHook.secret || undefined }); setNewHook({ name: '', url: '', secret: '', events: [] }); setShowCreate(false); refresh(); }
    catch (err) { console.error('Failed:', err); }
    finally { setCreating(false); }
  };

  const handleTest = async (id: number) => {
    setTesting(id); setTestResult(null);
    try { const r = await testWebhook(id); setTestResult({ id, success: r.success, status_code: r.status_code }); }
    catch { setTestResult({ id, success: false }); }
    finally { setTesting(null); }
  };

  if (loading) return <div className="text-center py-12 text-text-tertiary">Loading webhooks...</div>;

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-lg font-semibold text-text-primary">Webhooks</h2>
          <p className="text-[13px] text-text-tertiary mt-1">Get notified on run completion, approvals, or risk thresholds.</p>
        </div>
        <button onClick={() => setShowCreate(!showCreate)} className="px-4 py-1.5 bg-text-primary text-white text-[13px] font-medium rounded-md hover:bg-black/80 transition-colors">
          {showCreate ? 'Cancel' : 'New Webhook'}
        </button>
      </div>

      {showCreate && (
        <div className="bg-white rounded-lg border border-border p-5 mb-6 space-y-4">
          <h3 className="text-[13px] font-medium text-text-primary">New Webhook</h3>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs text-text-tertiary mb-1">Name</label>
              <input type="text" value={newHook.name} onChange={e => setNewHook(h => ({ ...h, name: e.target.value }))} placeholder="e.g. Slack notifications" className="w-full px-3 py-2 border border-border rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-accent/30 focus:border-accent bg-white" />
            </div>
            <div>
              <label className="block text-xs text-text-tertiary mb-1">Secret (optional)</label>
              <input type="text" value={newHook.secret} onChange={e => setNewHook(h => ({ ...h, secret: e.target.value }))} placeholder="HMAC-SHA256 secret" className="w-full px-3 py-2 border border-border rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-accent/30 focus:border-accent bg-white" />
            </div>
          </div>
          <div>
            <label className="block text-xs text-text-tertiary mb-1">URL</label>
            <input type="url" value={newHook.url} onChange={e => setNewHook(h => ({ ...h, url: e.target.value }))} placeholder="https://hooks.slack.com/services/..." className="w-full px-3 py-2 border border-border rounded-md text-sm font-mono focus:outline-none focus:ring-2 focus:ring-accent/30 focus:border-accent bg-white" />
          </div>
          <div>
            <label className="block text-xs text-text-tertiary mb-2">Events</label>
            <div className="flex flex-wrap gap-2">
              {AVAILABLE_EVENTS.map(event => (
                <button key={event} type="button" onClick={() => toggleEvent(event)} className={`px-3 py-1.5 rounded-md text-xs font-medium border transition-colors ${newHook.events.includes(event) ? 'bg-accent-light border-accent/30 text-accent-dark' : 'bg-surface-secondary border-border text-text-tertiary'}`}>
                  {event}
                </button>
              ))}
            </div>
          </div>
          <div className="flex justify-end">
            <button onClick={handleCreate} disabled={creating || !newHook.name.trim() || !newHook.url.trim() || newHook.events.length === 0} className="px-4 py-2 bg-text-primary text-white text-[13px] font-medium rounded-md hover:bg-black/80 disabled:opacity-40 transition-colors">
              {creating ? 'Creating...' : 'Create Webhook'}
            </button>
          </div>
        </div>
      )}

      {webhooks.length === 0 ? (
        <div className="text-center py-12 bg-white rounded-lg border border-border">
          <p className="text-text-tertiary text-sm">No webhooks configured yet.</p>
        </div>
      ) : (
        <div className="space-y-2">
          {webhooks.map((hook: any) => (
            <div key={hook.id} className="bg-white rounded-lg border border-border p-4">
              <div className="flex items-start justify-between gap-4">
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-1">
                    <h3 className="text-[13px] font-medium text-text-primary">{hook.name}</h3>
                    <span className={`w-1.5 h-1.5 rounded-full ${hook.is_active ? 'bg-emerald-400' : 'bg-gray-300'}`} />
                  </div>
                  <code className="text-xs text-text-tertiary font-mono break-all">{hook.url}</code>
                  <div className="flex flex-wrap gap-1.5 mt-2">
                    {(hook.events || []).map((event: string) => (
                      <span key={event} className="text-[11px] px-1.5 py-0.5 bg-surface-secondary text-text-secondary rounded">{event}</span>
                    ))}
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <button onClick={() => handleTest(hook.id)} disabled={testing === hook.id} className="text-xs px-3 py-1.5 border border-border text-text-secondary rounded-md hover:bg-surface-secondary disabled:opacity-50 transition-colors">
                    {testing === hook.id ? 'Testing...' : 'Test'}
                  </button>
                  <button onClick={() => { deleteWebhook(hook.id); refresh(); }} className="text-xs text-red-500 hover:text-red-600">Delete</button>
                </div>
              </div>
              {testResult && testResult.id === hook.id && (
                <div className={`mt-2 text-xs px-3 py-2 rounded-md ${testResult.success ? 'bg-emerald-50 text-emerald-700' : 'bg-red-50 text-red-700'}`}>
                  {testResult.success ? `Delivered (HTTP ${testResult.status_code})` : `Failed${testResult.status_code ? ` (HTTP ${testResult.status_code})` : ''}`}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
