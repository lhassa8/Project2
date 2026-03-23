import { useState } from 'react';
import { useWebhooks, createWebhook, deleteWebhook, testWebhook } from '../hooks/useApi';

const AVAILABLE_EVENTS = [
  'run.completed',
  'run.failed',
  'approval.submitted',
  'policy.violation',
  'risk.critical',
  'risk.high',
];

export default function WebhooksView() {
  const { webhooks, loading, refresh } = useWebhooks();
  const [showCreate, setShowCreate] = useState(false);
  const [newHook, setNewHook] = useState({ name: '', url: '', secret: '', events: [] as string[] });
  const [creating, setCreating] = useState(false);
  const [testing, setTesting] = useState<number | null>(null);
  const [testResult, setTestResult] = useState<{ id: number; success: boolean; status_code?: number } | null>(null);

  const toggleEvent = (event: string) => {
    setNewHook(prev => ({
      ...prev,
      events: prev.events.includes(event)
        ? prev.events.filter(e => e !== event)
        : [...prev.events, event],
    }));
  };

  const handleCreate = async () => {
    if (!newHook.name.trim() || !newHook.url.trim() || newHook.events.length === 0) return;
    setCreating(true);
    try {
      await createWebhook({
        name: newHook.name,
        url: newHook.url,
        events: newHook.events,
        secret: newHook.secret || undefined,
      });
      setNewHook({ name: '', url: '', secret: '', events: [] });
      setShowCreate(false);
      refresh();
    } catch (err) {
      console.error('Failed to create webhook:', err);
    } finally {
      setCreating(false);
    }
  };

  const handleTest = async (id: number) => {
    setTesting(id);
    setTestResult(null);
    try {
      const result = await testWebhook(id);
      setTestResult({ id, success: result.success, status_code: result.status_code });
    } catch {
      setTestResult({ id, success: false });
    } finally {
      setTesting(null);
    }
  };

  const handleDelete = async (id: number) => {
    await deleteWebhook(id);
    refresh();
  };

  if (loading) {
    return <div className="text-center py-12 text-gray-400">Loading webhooks...</div>;
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-lg font-semibold text-gray-800">Webhooks</h2>
          <p className="text-sm text-gray-500 mt-1">
            Get notified when runs complete, approvals are submitted, or risk thresholds are exceeded.
          </p>
        </div>
        <button
          onClick={() => setShowCreate(!showCreate)}
          className="px-4 py-2 bg-gradient-to-r from-indigo-600 to-violet-600 text-white text-sm font-medium rounded-lg hover:from-indigo-700 hover:to-violet-700 transition-all shadow-sm"
        >
          {showCreate ? 'Cancel' : 'New Webhook'}
        </button>
      </div>

      {/* Create form */}
      {showCreate && (
        <div className="bg-white rounded-xl border border-indigo-200 p-5 mb-6 space-y-4">
          <h3 className="text-sm font-semibold text-gray-700">New Webhook</h3>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-medium text-gray-500 mb-1">Name</label>
              <input
                type="text"
                value={newHook.name}
                onChange={e => setNewHook(h => ({ ...h, name: e.target.value }))}
                placeholder="e.g. Slack notifications"
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-500 mb-1">Signing Secret (optional)</label>
              <input
                type="text"
                value={newHook.secret}
                onChange={e => setNewHook(h => ({ ...h, secret: e.target.value }))}
                placeholder="HMAC-SHA256 secret"
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
              />
            </div>
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-500 mb-1">URL</label>
            <input
              type="url"
              value={newHook.url}
              onChange={e => setNewHook(h => ({ ...h, url: e.target.value }))}
              placeholder="https://hooks.slack.com/services/..."
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm font-mono focus:outline-none focus:ring-2 focus:ring-indigo-500"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-500 mb-2">Events</label>
            <div className="flex flex-wrap gap-2">
              {AVAILABLE_EVENTS.map(event => (
                <button
                  key={event}
                  type="button"
                  onClick={() => toggleEvent(event)}
                  className={`px-3 py-1.5 rounded-lg text-xs font-medium border transition-colors ${
                    newHook.events.includes(event)
                      ? 'bg-indigo-50 border-indigo-300 text-indigo-700'
                      : 'bg-gray-50 border-gray-200 text-gray-400'
                  }`}
                >
                  {event}
                </button>
              ))}
            </div>
          </div>
          <div className="flex justify-end">
            <button
              onClick={handleCreate}
              disabled={creating || !newHook.name.trim() || !newHook.url.trim() || newHook.events.length === 0}
              className="px-4 py-2 bg-indigo-600 text-white text-sm font-medium rounded-lg hover:bg-indigo-700 disabled:opacity-50 transition-colors"
            >
              {creating ? 'Creating...' : 'Create Webhook'}
            </button>
          </div>
        </div>
      )}

      {/* Webhook list */}
      {webhooks.length === 0 ? (
        <div className="text-center py-12 bg-white rounded-xl border border-gray-200">
          <p className="text-gray-400">No webhooks configured yet.</p>
        </div>
      ) : (
        <div className="space-y-3">
          {webhooks.map((hook: any) => (
            <div key={hook.id} className="bg-white rounded-xl border border-gray-200 p-5">
              <div className="flex items-start justify-between gap-4">
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-1">
                    <h3 className="text-sm font-semibold text-gray-900">{hook.name}</h3>
                    <span className={`w-2 h-2 rounded-full ${hook.is_active ? 'bg-green-400' : 'bg-gray-300'}`} />
                  </div>
                  <code className="text-xs text-gray-400 font-mono break-all">{hook.url}</code>
                  <div className="flex flex-wrap gap-1.5 mt-2">
                    {(hook.events || []).map((event: string) => (
                      <span key={event} className="text-xs px-2 py-0.5 bg-gray-100 text-gray-600 rounded-full">
                        {event}
                      </span>
                    ))}
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => handleTest(hook.id)}
                    disabled={testing === hook.id}
                    className="text-xs px-3 py-1.5 border border-gray-300 text-gray-600 rounded-lg hover:bg-gray-50 disabled:opacity-50 transition-colors"
                  >
                    {testing === hook.id ? 'Testing...' : 'Test'}
                  </button>
                  <button
                    onClick={() => handleDelete(hook.id)}
                    className="text-xs text-red-500 hover:text-red-700"
                  >
                    Delete
                  </button>
                </div>
              </div>
              {testResult && testResult.id === hook.id && (
                <div className={`mt-2 text-xs px-3 py-2 rounded-lg ${
                  testResult.success ? 'bg-green-50 text-green-700' : 'bg-red-50 text-red-700'
                }`}>
                  {testResult.success
                    ? `Test delivered successfully (HTTP ${testResult.status_code})`
                    : `Test failed${testResult.status_code ? ` (HTTP ${testResult.status_code})` : ''}`
                  }
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
