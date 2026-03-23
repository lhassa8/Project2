import { useCallback, useEffect, useRef, useState } from 'react';
import type { AgentAction, SandboxRun } from '../types';

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
      }
    };

    ws.onopen = () => {
      // Send a ping to keep alive
      const interval = setInterval(() => {
        if (ws.readyState === WebSocket.OPEN) ws.send('ping');
      }, 30000);
      ws.addEventListener('close', () => clearInterval(interval));
    };

    return () => {
      ws.close();
    };
  }, [runId]);

  return { actions, status, setActions, setStatus };
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
