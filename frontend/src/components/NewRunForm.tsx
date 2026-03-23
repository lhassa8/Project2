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

  // Load template if provided
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
    try {
      parsedState = JSON.parse(initialState);
    } catch {
      // ignore parse errors, use empty object
    }

    setSubmitting(true);
    try {
      const result = await createRun({
        agent_definition: {
          name,
          goal,
          tools,
          model: 'claude-sonnet-4-20250514',
          max_tokens: 4096,
          temperature: 0,
        },
        run_context: {
          user_persona: persona,
          initial_state: parsedState,
          environment,
        },
      });
      onCreated(result.id);
    } catch (err) {
      console.error('Failed to create run:', err);
      setSubmitting(false);
    }
  };

  if (templateLoading) {
    return <div className="text-center py-12 text-gray-400">Loading template...</div>;
  }

  return (
    <div className="max-w-2xl mx-auto">
      <h2 className="text-lg font-semibold text-gray-800 mb-1">New Sandbox Run</h2>
      {templateId && (
        <p className="text-sm text-indigo-600 mb-4">Loaded from template</p>
      )}

      <form onSubmit={handleSubmit} className="bg-white rounded-xl border border-gray-200 p-6 space-y-5">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Agent Name</label>
          <input
            type="text"
            value={name}
            onChange={e => setName(e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Agent Goal</label>
          <textarea
            value={goal}
            onChange={e => setGoal(e.target.value)}
            rows={4}
            placeholder="Describe what the agent should accomplish..."
            className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent resize-none"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">User Persona</label>
          <input
            type="text"
            value={persona}
            onChange={e => setPersona(e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Initial State (JSON)</label>
          <textarea
            value={initialState}
            onChange={e => setInitialState(e.target.value)}
            rows={3}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg text-xs font-mono focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent resize-none"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">Allowed Tools</label>
          <div className="flex flex-wrap gap-2">
            {tools.map(tool => (
              <button
                key={tool.name}
                type="button"
                onClick={() => toggleTool(tool.name)}
                className={`px-3 py-1.5 rounded-lg text-sm font-medium border transition-colors ${
                  tool.enabled
                    ? 'bg-indigo-50 border-indigo-300 text-indigo-700'
                    : 'bg-gray-50 border-gray-200 text-gray-400'
                }`}
              >
                {tool.name}
              </button>
            ))}
          </div>
        </div>

        {/* Environment config */}
        <div>
          <button
            type="button"
            onClick={() => setShowEnv(!showEnv)}
            className="flex items-center gap-2 text-sm font-medium text-gray-700 hover:text-indigo-600 transition-colors"
          >
            <span>{showEnv ? '▾' : '▸'}</span>
            Sandbox Environment
            {(Object.keys(environment.filesystem).length > 0 || Object.keys(environment.database).length > 0 || environment.http_stubs.length > 0) && (
              <span className="text-xs text-indigo-600 bg-indigo-50 px-2 py-0.5 rounded-full">configured</span>
            )}
          </button>
          <p className="text-xs text-gray-400 mt-1 mb-2">
            Seed files, database tables, and HTTP stubs for realistic simulation
          </p>
          {showEnv && (
            <EnvironmentEditor value={environment} onChange={setEnvironment} />
          )}
        </div>

        <div className="flex justify-end gap-3 pt-2">
          <button
            type="button"
            onClick={onCancel}
            className="px-4 py-2 text-sm text-gray-600 hover:text-gray-800"
          >
            Cancel
          </button>
          <button
            type="submit"
            disabled={submitting || !goal.trim()}
            className="px-5 py-2 bg-gradient-to-r from-indigo-600 to-violet-600 text-white text-sm font-medium rounded-lg hover:from-indigo-700 hover:to-violet-700 disabled:opacity-50 disabled:cursor-not-allowed transition-all shadow-sm"
          >
            {submitting ? 'Starting...' : 'Start Sandbox Run'}
          </button>
        </div>
      </form>
    </div>
  );
}
