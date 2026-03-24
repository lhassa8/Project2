import { useState } from 'react';
import { useTemplates, quickRunTemplate } from '../hooks/useApi';

interface Props {
  onUseTemplate: (templateId: string) => void;
  onViewRun?: (id: string) => void;
}

const DIFFICULTY_STYLES: Record<string, string> = {
  low: 'text-emerald-600 bg-emerald-50',
  medium: 'text-amber-600 bg-amber-50',
  high: 'text-red-600 bg-red-50',
};

const CATEGORY_DESCRIPTIONS: Record<string, string> = {
  'Getting Started': 'Simple scenarios to learn how AgentSandbox works. Start here!',
  'Sales & CRM': 'Lead management, enrichment, and customer outreach automation.',
  'DevOps & SRE': 'Incident response, monitoring, and infrastructure management.',
  'HR & People Ops': 'Employee onboarding, offboarding, and HR workflows.',
  'Data Engineering': 'Pipeline management, data quality, and reporting.',
  'Security & Compliance': 'Access reviews, audits, and compliance automation.',
  'Customer Success': 'Support escalation, retention, and customer communication.',
};

export default function TemplateLibrary({ onUseTemplate, onViewRun }: Props) {
  const { templates, loading } = useTemplates();
  const [launching, setLaunching] = useState<string | null>(null);

  if (loading) return <div className="text-center py-12 text-text-tertiary">Loading templates...</div>;

  const grouped: Record<string, typeof templates> = {};
  for (const t of templates) (grouped[t.category] ??= []).push(t);

  // Ensure "Getting Started" is first
  const categories = Object.keys(grouped).sort((a, b) => {
    if (a === 'Getting Started') return -1;
    if (b === 'Getting Started') return 1;
    return 0;
  });

  const handleQuickRun = async (templateId: string) => {
    setLaunching(templateId);
    try {
      const result = await quickRunTemplate(templateId);
      onViewRun?.(result.id);
    } catch {
      setLaunching(null);
    }
  };

  return (
    <div>
      <div className="mb-6">
        <h2 className="text-lg font-semibold text-text-primary">Scenario Templates</h2>
        <p className="text-[13px] text-text-tertiary mt-1">
          Pre-built agent scenarios ready to run. Pick a template to customize it, or click "Run Now" to launch instantly.
        </p>
        <p className="text-xs text-text-tertiary mt-1">
          Running templates requires an Anthropic API key configured in the backend. Use "Customize" to review the setup first.
        </p>
      </div>

      <div className="space-y-8">
        {categories.map(category => {
          const tmpls = grouped[category];
          const isGettingStarted = category === 'Getting Started';
          return (
            <div key={category}>
              <div className="mb-3">
                <h3 className={`text-[11px] font-medium uppercase tracking-wider ${isGettingStarted ? 'text-accent' : 'text-text-tertiary'}`}>{category}</h3>
                {CATEGORY_DESCRIPTIONS[category] && (
                  <p className="text-xs text-text-tertiary mt-0.5">{CATEGORY_DESCRIPTIONS[category]}</p>
                )}
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {tmpls.map(t => (
                  <div key={t.id} className={`bg-white rounded-lg border p-5 hover:border-border-strong transition-colors flex flex-col ${isGettingStarted ? 'border-accent/20 ring-1 ring-accent/10' : 'border-border'}`}>
                    <div className="flex items-center gap-2 mb-2">
                      <span className={`text-[11px] font-medium px-1.5 py-0.5 rounded ${DIFFICULTY_STYLES[t.difficulty]}`}>{t.difficulty}</span>
                      <span className="text-xs text-text-tertiary">~{t.estimated_actions} actions</span>
                    </div>
                    <h4 className="text-[13px] font-medium text-text-primary mb-1">{t.name}</h4>
                    <p className="text-xs text-text-tertiary flex-1 mb-3 leading-relaxed">{t.description}</p>
                    <div className="flex gap-2">
                      <button
                        onClick={() => handleQuickRun(t.id)}
                        disabled={launching === t.id}
                        className="px-3 py-1.5 bg-text-primary text-white text-xs font-medium rounded-md hover:bg-black/80 disabled:opacity-50 transition-colors"
                      >
                        {launching === t.id ? 'Starting...' : 'Run Now'}
                      </button>
                      <button
                        onClick={() => onUseTemplate(t.id)}
                        className="px-3 py-1.5 bg-surface-secondary text-text-secondary text-xs font-medium rounded-md hover:bg-surface-secondary/80 transition-colors"
                      >
                        Customize
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
