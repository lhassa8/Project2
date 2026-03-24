import { useEffect, useState } from 'react';
import { createRun, getTemplateDetail } from '../hooks/useApi';
import EnvironmentEditor from './EnvironmentEditor';

const DEFAULT_TOOLS = [
  { name: 'read_file', enabled: true },
  { name: 'write_file', enabled: true },
  { name: 'send_email', enabled: true },
  { name: 'http_request', enabled: true },
  { name: 'query_database', enabled: true },
];

const EMPTY_ENV = {
  filesystem: {} as Record<string, string>,
  database: {} as Record<string, Record<string, unknown>[]>,
  http_stubs: [] as { url_pattern: string; method?: string; status_code?: number; response_body?: unknown }[],
};

interface Props {
  templateId?: string;
  onCreated: (id: string) => void;
  onCancel: () => void;
}

export default function NewRunForm({ templateId, onCreated, onCancel }: Props) {
  const [name, setName] = useState('My Agent');
  const [goal, setGoal] = useState('');
  const [persona, setPersona] = useState('Enterprise user');
  const [initialState, setInitialState] = useState('{}');
  const [tools, setTools] = useState(DEFAULT_TOOLS.map(t => ({ ...t })));
  const [environment, setEnvironment] = useState({ ...EMPTY_ENV });
  const [showEnv, setShowEnv] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [templateLoading, setTemplateLoading] = useState(false);

  useEffect(() => {
    if (!templateId) return;
    setTemplateLoading(true);
    getTemplateDetail(templateId).then(tmpl => {
      setName(tmpl.agent_definition.name);
      setGoal(tmpl.agent_definition.goal);
      setPersona(tmpl.run_context.user_persona);
      setInitialState(JSON.stringify(tmpl.run_context.initial_state, null, 2));
      setTools(tmpl.agent_definition.tools);
      if (tmpl.run_context.environment) {
        setEnvironment({
          filesystem: tmpl.run_context.environment.filesystem || {},
          database: tmpl.run_context.environment.database || {},
          http_stubs: tmpl.run_context.environment.http_stubs || [],
        });
        const env = tmpl.run_context.environment;
        if (Object.keys(env.filesystem || {}).length > 0 || Object.keys(env.database || {}).length > 0 || (env.http_stubs || []).length > 0) {
          setShowEnv(true);
        }
      }
      setTemplateLoading(false);
    }).catch(() => setTemplateLoading(false));
  }, [templateId]);

  const toggleTool = (toolName: string) => {
    setTools(prev => prev.map(t =>
      t.name === toolName ? { ...t, enabled: !t.enabled } : t
    ));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!goal.trim()) return;

    let parsedState = {};
    try { parsedState = JSON.parse(initialState); } catch {}

    setSubmitting(true);
    try {
      const result = await createRun({
        agent_definition: { name, goal, tools, model: 'claude-sonnet-4-20250514', max_tokens: 4096, temperature: 0 },
        run_context: { user_persona: persona, initial_state: parsedState, environment },
      });
      onCreated(result.id);
    } catch (err) {
      console.error('Failed to create run:', err);
      setSubmitting(false);
    }
  };

  if (templateLoading) {
    return <div className="text-center py-12 text-text-tertiary">Loading template...</div>;
  }

  return (
    <div className="max-w-2xl mx-auto">
      <h2 className="text-lg font-semibold text-text-primary mb-1">New Sandbox Run</h2>
      {templateId && (
        <p className="text-[13px] text-accent mb-4">Loaded from template</p>
      )}

      <form onSubmit={handleSubmit} className="bg-white rounded-lg border border-border p-6 space-y-5">
        <div>
          <label className="block text-[13px] font-medium text-text-primary mb-1.5">Agent Name</label>
          <input
            type="text"
            value={name}
            onChange={e => setName(e.target.value)}
            className="w-full px-3 py-2 border border-border rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-accent/30 focus:border-accent bg-white"
          />
        </div>

        <div>
          <label className="block text-[13px] font-medium text-text-primary mb-1.5">Agent Goal</label>
          <textarea
            value={goal}
            onChange={e => setGoal(e.target.value)}
            rows={4}
            placeholder="Describe what the agent should accomplish..."
            className="w-full px-3 py-2 border border-border rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-accent/30 focus:border-accent resize-none bg-white"
          />
        </div>

        <div>
          <label className="block text-[13px] font-medium text-text-primary mb-1.5">User Persona</label>
          <input
            type="text"
            value={persona}
            onChange={e => setPersona(e.target.value)}
            className="w-full px-3 py-2 border border-border rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-accent/30 focus:border-accent bg-white"
          />
        </div>

        <div>
          <label className="block text-[13px] font-medium text-text-primary mb-1.5">Initial State (JSON)</label>
          <textarea
            value={initialState}
            onChange={e => setInitialState(e.target.value)}
            rows={3}
            className="w-full px-3 py-2 border border-border rounded-md text-xs font-mono focus:outline-none focus:ring-2 focus:ring-accent/30 focus:border-accent resize-none bg-white"
          />
        </div>

        <div>
          <label className="block text-[13px] font-medium text-text-primary mb-2">Allowed Tools</label>
          <div className="flex flex-wrap gap-2">
            {tools.map(tool => (
              <button
                key={tool.name}
                type="button"
                onClick={() => toggleTool(tool.name)}
                className={`px-3 py-1.5 rounded-md text-xs font-medium border transition-colors ${
                  tool.enabled
                    ? 'bg-accent-light border-accent/30 text-accent-dark'
                    : 'bg-surface-secondary border-border text-text-tertiary'
                }`}
              >
                {tool.name}
              </button>
            ))}
          </div>
        </div>

        <div>
          <button
            type="button"
            onClick={() => setShowEnv(!showEnv)}
            className="flex items-center gap-2 text-[13px] font-medium text-text-secondary hover:text-text-primary transition-colors"
          >
            <svg className={`w-3.5 h-3.5 transition-transform ${showEnv ? 'rotate-180' : ''}`} fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" d="m19.5 8.25-7.5 7.5-7.5-7.5" />
            </svg>
            Sandbox Environment
            {(Object.keys(environment.filesystem).length > 0 || Object.keys(environment.database).length > 0 || environment.http_stubs.length > 0) && (
              <span className="text-[11px] text-accent bg-accent-light px-1.5 py-0.5 rounded">configured</span>
            )}
          </button>
          <p className="text-xs text-text-tertiary mt-1 mb-2">
            Seed files, database tables, and HTTP stubs for realistic simulation.
          </p>
          {showEnv && <EnvironmentEditor value={environment} onChange={setEnvironment} />}
        </div>

        <div className="flex justify-end gap-3 pt-2 border-t border-border">
          <button type="button" onClick={onCancel} className="px-4 py-2 text-[13px] text-text-tertiary hover:text-text-secondary">
            Cancel
          </button>
          <button
            type="submit"
            disabled={submitting || !goal.trim()}
            className="px-5 py-2 bg-text-primary text-white text-[13px] font-medium rounded-md hover:bg-black/80 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
          >
            {submitting ? 'Starting...' : 'Start Sandbox Run'}
          </button>
        </div>
      </form>
    </div>
  );
}
