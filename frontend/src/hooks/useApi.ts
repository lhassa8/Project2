import { useCallback, useEffect, useRef, useState } from 'react';
import type { AgentAction, Analytics, PolicyConfig, SandboxRun, Template, TemplateDetail } from '../types';

const API = '/api/runs';

export function useRuns() {
  const [runs, setRuns] = useState<SandboxRun[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchRuns = useCallback(async () => {
    setLoading(true);
    const res = await fetch(API);
    setRuns(await res.json());
    setLoading(false);
  }, []);

  useEffect(() => { fetchRuns(); }, [fetchRuns]);

  return { runs, loading, refresh: fetchRuns };
}

export function useRun(runId: string | null) {
  const [run, setRun] = useState<SandboxRun | null>(null);
  const [loading, setLoading] = useState(false);

  const fetchRun = useCallback(async () => {
    if (!runId) return;
    setLoading(true);
    const res = await fetch(`${API}/${runId}`);
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
  run_context: { user_persona: string; initial_state: Record<string, unknown> };
}) {
  const res = await fetch(API, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  return res.json();
}

export async function submitApproval(
  runId: string,
  decision: 'approved' | 'changes_requested' | 'rejected',
  notes: string,
) {
  const res = await fetch(`${API}/${runId}/approve`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ decision, reviewer_notes: notes }),
  });
  return res.json();
}

export async function exportRun(runId: string) {
  const res = await fetch(`${API}/${runId}/export`);
  return res.json();
}

// ── Templates ──────────────────────────────────────────────────────────────

export function useTemplates() {
  const [templates, setTemplates] = useState<Template[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch('/api/templates')
      .then(r => r.json())
      .then(data => { setTemplates(data); setLoading(false); })
      .catch(() => setLoading(false));
  }, []);

  return { templates, loading };
}

export async function getTemplateDetail(templateId: string): Promise<TemplateDetail> {
  const res = await fetch(`/api/templates/${templateId}`);
  return res.json();
}

// ── Analytics ──────────────────────────────────────────────────────────────

export function useAnalytics() {
  const [data, setData] = useState<Analytics | null>(null);
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    setLoading(true);
    const res = await fetch('/api/analytics');
    setData(await res.json());
    setLoading(false);
  }, []);

  useEffect(() => { refresh(); }, [refresh]);

  return { data, loading, refresh };
}

// ── Policies ───────────────────────────────────────────────────────────────

export function usePolicies() {
  const [policies, setPolicies] = useState<PolicyConfig[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch('/api/policies')
      .then(r => r.json())
      .then(data => { setPolicies(data); setLoading(false); })
      .catch(() => setLoading(false));
  }, []);

  return { policies, loading };
}
