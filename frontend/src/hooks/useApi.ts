import { useCallback, useEffect, useRef, useState } from 'react';
import type {
  AgentAction,
  Analytics,
  PolicyConfig,
  RunComparison,
  SandboxRun,
  Template,
  TemplateDetail,
  Workspace,
} from '../types';

const API = '/api/runs';

// ── Shared headers (API key support) ──────────────────────────────────────

function getHeaders(): Record<string, string> {
  const headers: Record<string, string> = { 'Content-Type': 'application/json' };
  const apiKey = localStorage.getItem('agent_sandbox_api_key');
  if (apiKey) headers['X-API-Key'] = apiKey;
  return headers;
}

function authFetch(url: string, opts: RequestInit = {}): Promise<Response> {
  const headers = { ...getHeaders(), ...opts.headers };
  return fetch(url, { ...opts, headers });
}

// ── Runs ──────────────────────────────────────────────────────────────────

export function useRuns(filters?: { status?: string; agent_name?: string; limit?: number; offset?: number }) {
  const [runs, setRuns] = useState<SandboxRun[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);

  const fetchRuns = useCallback(async () => {
    setLoading(true);
    const params = new URLSearchParams();
    if (filters?.status) params.set('status', filters.status);
    if (filters?.agent_name) params.set('agent_name', filters.agent_name);
    if (filters?.limit) params.set('limit', String(filters.limit));
    if (filters?.offset) params.set('offset', String(filters.offset));
    const qs = params.toString();
    const res = await authFetch(`${API}${qs ? `?${qs}` : ''}`);
    const data = await res.json();
    setRuns(data.runs ?? data);
    setTotal(data.total ?? (data.runs ?? data).length);
    setLoading(false);
  }, [filters?.status, filters?.agent_name, filters?.limit, filters?.offset]);

  useEffect(() => { fetchRuns(); }, [fetchRuns]);

  return { runs, total, loading, refresh: fetchRuns };
}

export function useRun(runId: string | null) {
  const [run, setRun] = useState<SandboxRun | null>(null);
  const [loading, setLoading] = useState(false);

  const fetchRun = useCallback(async () => {
    if (!runId) return;
    setLoading(true);
    const res = await authFetch(`${API}/${runId}`);
    if (res.ok) setRun(await res.json());
    setLoading(false);
  }, [runId]);

  useEffect(() => { fetchRun(); }, [fetchRun]);

  return { run, loading, refresh: fetchRun, setRun };
}

export function useRunStream(runId: string | null) {
  const [actions, setActions] = useState<AgentAction[]>([]);
  const [status, setStatus] = useState<string>('running');
  const [riskReport, setRiskReport] = useState<SandboxRun['risk_report']>(null);
  const [policyViolations, setPolicyViolations] = useState<SandboxRun['policy_violations']>([]);
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    if (!runId) return;

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const ws = new WebSocket(`${protocol}//${window.location.host}/api/runs/${runId}/ws`);
    wsRef.current = ws;

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      if (data.type === 'action') {
        setActions(prev => [...prev, data.action]);
      } else if (data.type === 'run_complete') {
        setStatus(data.status);
        if (data.risk_report) setRiskReport(data.risk_report);
        if (data.policy_violations) setPolicyViolations(data.policy_violations);
      } else if (data.type === 'risk_report') {
        setRiskReport(data.report);
      } else if (data.type === 'policy_violation') {
        setPolicyViolations(prev => [...prev, data.violation]);
      }
    };

    ws.onopen = () => {
      const interval = setInterval(() => {
        if (ws.readyState === WebSocket.OPEN) ws.send('ping');
      }, 30000);
      ws.addEventListener('close', () => clearInterval(interval));
    };

    return () => { ws.close(); };
  }, [runId]);

  return { actions, status, riskReport, policyViolations, setActions, setStatus };
}

export async function createRun(body: {
  agent_definition: { name: string; goal: string; tools: { name: string; enabled: boolean }[]; model: string; max_tokens: number; temperature: number };
  run_context: { user_persona: string; initial_state: Record<string, unknown>; environment?: { filesystem: Record<string, string>; database: Record<string, Record<string, unknown>[]>; http_stubs: unknown[] } };
}) {
  const res = await authFetch(API, {
    method: 'POST',
    body: JSON.stringify(body),
  });
  return res.json();
}

export async function submitApproval(
  runId: string,
  decision: 'approved' | 'changes_requested' | 'rejected',
  notes: string,
) {
  const res = await authFetch(`${API}/${runId}/approve`, {
    method: 'POST',
    body: JSON.stringify({ decision, reviewer_notes: notes }),
  });
  return res.json();
}

export async function exportRun(runId: string) {
  const res = await authFetch(`${API}/${runId}/export`);
  return res.json();
}

// ── Comparison ──────────────────────────────────────────────────────────────

export async function compareRuns(runIdA: string, runIdB: string): Promise<RunComparison> {
  const res = await authFetch(`${API}/compare`, {
    method: 'POST',
    body: JSON.stringify({ run_id_a: runIdA, run_id_b: runIdB }),
  });
  return res.json();
}

// ── Replay ──────────────────────────────────────────────────────────────────

export async function replayRun(runId: string, target: 'sandbox' | 'live' = 'sandbox', environmentOverrides?: Record<string, unknown>) {
  const res = await authFetch(`${API}/${runId}/replay`, {
    method: 'POST',
    body: JSON.stringify({ target, environment_overrides: environmentOverrides || {} }),
  });
  return res.json();
}

// ── Templates ──────────────────────────────────────────────────────────────

export function useTemplates() {
  const [templates, setTemplates] = useState<Template[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    authFetch('/api/templates')
      .then(r => r.json())
      .then(data => { setTemplates(data); setLoading(false); })
      .catch(() => setLoading(false));
  }, []);

  return { templates, loading };
}

export async function getTemplateDetail(templateId: string): Promise<TemplateDetail> {
  const res = await authFetch(`/api/templates/${templateId}`);
  return res.json();
}

// ── Analytics ──────────────────────────────────────────────────────────────

export function useAnalytics() {
  const [data, setData] = useState<Analytics | null>(null);
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    setLoading(true);
    const res = await authFetch('/api/analytics');
    setData(await res.json());
    setLoading(false);
  }, []);

  useEffect(() => { refresh(); }, [refresh]);

  return { data, loading, refresh };
}

// ── Policies ───────────────────────────────────────────────────────────────

export function usePolicies() {
  const [builtin, setBuiltin] = useState<PolicyConfig[]>([]);
  const [custom, setCustom] = useState<PolicyConfig[]>([]);
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      const res = await authFetch('/api/policies');
      const data = await res.json();
      setBuiltin(data.builtin ?? data);
      setCustom(data.custom ?? []);
    } catch { /* ignore */ }
    setLoading(false);
  }, []);

  useEffect(() => { refresh(); }, [refresh]);

  return { builtin, custom, policies: [...builtin, ...custom], loading, refresh };
}

export async function createPolicy(policy: { name: string; description: string; action: string; tool_name?: string; pattern?: string; target_field?: string }) {
  const res = await authFetch('/api/policies', { method: 'POST', body: JSON.stringify(policy) });
  return res.json();
}

export async function updatePolicy(id: number, updates: Record<string, unknown>) {
  const res = await authFetch(`/api/policies/${id}`, { method: 'PUT', body: JSON.stringify(updates) });
  return res.json();
}

export async function deletePolicy(id: number) {
  const res = await authFetch(`/api/policies/${id}`, { method: 'DELETE' });
  return res.json();
}

// ── Workspace ──────────────────────────────────────────────────────────────

export function useWorkspace() {
  const [workspace, setWorkspace] = useState<Workspace | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    authFetch('/api/workspaces/me')
      .then(r => r.json())
      .then(data => { setWorkspace(data); setLoading(false); })
      .catch(() => setLoading(false));
  }, []);

  return { workspace, loading };
}

export async function createWorkspace(name: string) {
  const res = await authFetch('/api/workspaces', {
    method: 'POST',
    body: JSON.stringify({ name }),
  });
  return res.json();
}

export async function createApiKey(name: string, role: string = 'admin') {
  const res = await authFetch('/api/workspaces/api-keys', {
    method: 'POST',
    body: JSON.stringify({ name, role }),
  });
  return res.json();
}

export async function listApiKeys(): Promise<{ key: string; name: string; role: string }[]> {
  const res = await authFetch('/api/workspaces/api-keys');
  return res.json();
}

// ── Audit log ─────────────────────────────────────────────────────────────

export function useAuditLog(filters?: { event_type?: string; resource_type?: string; limit?: number; offset?: number }) {
  const [events, setEvents] = useState<Record<string, unknown>[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    setLoading(true);
    const params = new URLSearchParams();
    if (filters?.event_type) params.set('event_type', filters.event_type);
    if (filters?.resource_type) params.set('resource_type', filters.resource_type);
    if (filters?.limit) params.set('limit', String(filters.limit));
    if (filters?.offset) params.set('offset', String(filters.offset));
    const qs = params.toString();
    const res = await authFetch(`/api/audit${qs ? `?${qs}` : ''}`);
    const data = await res.json();
    setEvents(data.events ?? []);
    setTotal(data.total ?? 0);
    setLoading(false);
  }, [filters?.event_type, filters?.resource_type, filters?.limit, filters?.offset]);

  useEffect(() => { refresh(); }, [refresh]);

  return { events, total, loading, refresh };
}

// ── Webhooks ──────────────────────────────────────────────────────────────

export function useWebhooks() {
  const [webhooks, setWebhooks] = useState<Record<string, unknown>[]>([]);
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    setLoading(true);
    const res = await authFetch('/api/webhooks');
    setWebhooks(await res.json());
    setLoading(false);
  }, []);

  useEffect(() => { refresh(); }, [refresh]);

  return { webhooks, loading, refresh };
}

export async function createWebhook(data: { name: string; url: string; events: string[]; secret?: string }) {
  const res = await authFetch('/api/webhooks', { method: 'POST', body: JSON.stringify(data) });
  return res.json();
}

export async function deleteWebhook(id: number) {
  const res = await authFetch(`/api/webhooks/${id}`, { method: 'DELETE' });
  return res.json();
}

export async function testWebhook(id: number) {
  const res = await authFetch(`/api/webhooks/${id}/test`, { method: 'POST' });
  return res.json();
}
