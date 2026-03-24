import { useState } from 'react';
import { seedDemoData, quickRunTemplate } from '../hooks/useApi';

interface Props {
  onViewRun: (id: string) => void;
  onNewRun: () => void;
  onViewTemplates: () => void;
  onRefresh: () => void;
}

const QUICK_START_TEMPLATES = [
  {
    id: 'hello-world-file',
    title: 'Hello World — File Ops',
    desc: 'Read a config, write a greeting. Simplest possible run.',
    icon: (
      <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 0 0-3.375-3.375h-1.5A1.125 1.125 0 0 1 13.5 7.125v-1.5a3.375 3.375 0 0 0-3.375-3.375H8.25m2.25 0H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 0 0-9-9Z" />
      </svg>
    ),
  },
  {
    id: 'simple-db-query',
    title: 'Database Query',
    desc: 'Query products and generate a report.',
    icon: (
      <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" d="M20.25 6.375c0 2.278-3.694 4.125-8.25 4.125S3.75 8.653 3.75 6.375m16.5 0c0-2.278-3.694-4.125-8.25-4.125S3.75 4.097 3.75 6.375m16.5 0v11.25c0 2.278-3.694 4.125-8.25 4.125s-8.25-1.847-8.25-4.125V6.375m16.5 0v3.75m-16.5-3.75v3.75m16.5 0v3.75C20.25 16.153 16.556 18 12 18s-8.25-1.847-8.25-4.125v-3.75m16.5 0c0 2.278-3.694 4.125-8.25 4.125s-8.25-1.847-8.25-4.125" />
      </svg>
    ),
  },
  {
    id: 'email-notification',
    title: 'Email Alert',
    desc: 'Check inventory and send low-stock warnings.',
    icon: (
      <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" d="M21.75 6.75v10.5a2.25 2.25 0 0 1-2.25 2.25h-15a2.25 2.25 0 0 1-2.25-2.25V6.75m19.5 0A2.25 2.25 0 0 0 19.5 4.5h-15a2.25 2.25 0 0 0-2.25 2.25m19.5 0v.243a2.25 2.25 0 0 1-1.07 1.916l-7.5 4.615a2.25 2.25 0 0 1-2.36 0L3.32 8.91a2.25 2.25 0 0 1-1.07-1.916V6.75" />
      </svg>
    ),
  },
];

export default function WelcomeGuide({ onViewRun, onNewRun, onViewTemplates, onRefresh }: Props) {
  const [seeding, setSeeding] = useState(false);
  const [launching, setLaunching] = useState<string | null>(null);
  const [seedResult, setSeedResult] = useState<string | null>(null);

  const handleSeedDemo = async () => {
    setSeeding(true);
    setSeedResult(null);
    try {
      const result = await seedDemoData();
      if (result.seeded) {
        setSeedResult(`Created ${result.runs_created} demo runs!`);
        onRefresh();
      } else {
        setSeedResult(result.message || 'Demo data already loaded.');
        onRefresh();
      }
    } catch {
      setSeedResult('Failed to seed demo data.');
    }
    setSeeding(false);
  };

  const handleQuickRun = async (templateId: string) => {
    setLaunching(templateId);
    try {
      const result = await quickRunTemplate(templateId);
      onViewRun(result.id);
    } catch {
      setLaunching(null);
    }
  };

  return (
    <div className="space-y-6">
      {/* Hero section */}
      <div className="bg-gradient-to-br from-blue-50 to-indigo-50 rounded-xl border border-blue-100 p-8">
        <h1 className="text-xl font-bold text-text-primary mb-2">Welcome to AgentSandbox</h1>
        <p className="text-sm text-text-secondary leading-relaxed max-w-2xl mb-6">
          Preview, debug, and approve autonomous AI agent actions <strong>before</strong> they touch real systems.
          Every tool call runs in a sandboxed environment with risk scoring, policy enforcement, and full audit trails.
        </p>

        <div className="flex flex-wrap gap-3">
          <button
            onClick={handleSeedDemo}
            disabled={seeding}
            className="px-5 py-2.5 bg-text-primary text-white text-sm font-medium rounded-lg hover:bg-black/80 disabled:opacity-50 transition-colors"
          >
            {seeding ? 'Loading...' : 'Load Demo Data'}
          </button>
          <button
            onClick={onNewRun}
            className="px-5 py-2.5 bg-white text-text-primary text-sm font-medium rounded-lg border border-border hover:border-border-strong transition-colors"
          >
            Create Custom Run
          </button>
          <button
            onClick={onViewTemplates}
            className="px-5 py-2.5 text-sm font-medium text-accent hover:text-accent-dark transition-colors"
          >
            Browse All Templates
          </button>
        </div>

        {seedResult && (
          <p className="mt-3 text-sm text-emerald-700 bg-emerald-50 px-3 py-1.5 rounded-md inline-block">{seedResult}</p>
        )}
      </div>

      {/* Quick Start */}
      <div>
        <h2 className="text-sm font-semibold text-text-primary mb-1">Quick Start — Run a Template in One Click</h2>
        <p className="text-xs text-text-tertiary mb-3">
          These simple scenarios launch instantly. No configuration needed. Requires an Anthropic API key in your backend .env file.
        </p>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {QUICK_START_TEMPLATES.map(t => (
            <div key={t.id} className="bg-white rounded-lg border border-border p-5 hover:border-border-strong transition-colors">
              <div className="flex items-center gap-2 text-accent mb-2">{t.icon}</div>
              <h3 className="text-[13px] font-medium text-text-primary mb-1">{t.title}</h3>
              <p className="text-xs text-text-tertiary mb-3 leading-relaxed">{t.desc}</p>
              <button
                onClick={() => handleQuickRun(t.id)}
                disabled={launching === t.id}
                className="px-3 py-1.5 bg-accent/10 text-accent text-xs font-medium rounded-md hover:bg-accent/20 disabled:opacity-50 transition-colors"
              >
                {launching === t.id ? 'Starting...' : 'Run Now'}
              </button>
            </div>
          ))}
        </div>
      </div>

      {/* How it works */}
      <div className="bg-white rounded-lg border border-border p-6">
        <h2 className="text-sm font-semibold text-text-primary mb-4">How AgentSandbox Works</h2>
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
          {[
            { step: '1', title: 'Define', desc: 'Set up an agent with a goal, tools, and a simulated environment (files, databases, APIs).' },
            { step: '2', title: 'Run', desc: 'The agent executes in a sandbox. Every tool call is intercepted and simulated — nothing touches real systems.' },
            { step: '3', title: 'Review', desc: 'Inspect the action timeline, state changes, risk score, and policy violations.' },
            { step: '4', title: 'Approve', desc: 'Approve safe runs for production replay, or reject and iterate on the agent configuration.' },
          ].map(s => (
            <div key={s.step}>
              <div className="w-7 h-7 rounded-full bg-accent/10 text-accent text-xs font-bold flex items-center justify-center mb-2">{s.step}</div>
              <h3 className="text-[13px] font-medium text-text-primary mb-1">{s.title}</h3>
              <p className="text-xs text-text-tertiary leading-relaxed">{s.desc}</p>
            </div>
          ))}
        </div>
      </div>

      {/* Feature overview */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="bg-white rounded-lg border border-border p-5">
          <h3 className="text-[13px] font-medium text-text-primary mb-2">Key Features</h3>
          <ul className="space-y-1.5 text-xs text-text-secondary">
            <li><strong>Sandbox Execution</strong> — File, DB, email, and HTTP calls are all simulated</li>
            <li><strong>Risk Scoring</strong> — Automated 0-100 risk assessment for every run</li>
            <li><strong>Policy Engine</strong> — 6 built-in policies block dangerous operations</li>
            <li><strong>Approval Workflow</strong> — HMAC-signed approvals for production replay</li>
            <li><strong>Run Comparison</strong> — Compare two runs side-by-side</li>
            <li><strong>Audit Log</strong> — Full compliance trail of every action</li>
          </ul>
        </div>
        <div className="bg-white rounded-lg border border-border p-5">
          <h3 className="text-[13px] font-medium text-text-primary mb-2">Getting Started Tips</h3>
          <ul className="space-y-1.5 text-xs text-text-secondary">
            <li><strong>No API key?</strong> — Click "Load Demo Data" above to explore with pre-built runs</li>
            <li><strong>Have an API key?</strong> — Try a Quick Start template or create a custom run</li>
            <li><strong>Templates</strong> tab has 9 ready-made scenarios from simple to complex</li>
            <li><strong>Policies</strong> tab lets you configure what agents can and cannot do</li>
            <li><strong>Compare</strong> tab lets you diff two runs side-by-side</li>
            <li><strong>Webhooks</strong> tab sends notifications when runs complete or risk is high</li>
          </ul>
        </div>
      </div>
    </div>
  );
}
