import { useTemplates } from '../hooks/useApi';

interface Props {
  onUseTemplate: (templateId: string) => void;
}

const DIFFICULTY_STYLES: Record<string, string> = {
  low: 'text-emerald-600',
  medium: 'text-amber-600',
  high: 'text-red-600',
};

export default function TemplateLibrary({ onUseTemplate }: Props) {
  const { templates, loading } = useTemplates();

  if (loading) return <div className="text-center py-12 text-text-tertiary">Loading templates...</div>;

  const grouped: Record<string, typeof templates> = {};
  for (const t of templates) (grouped[t.category] ??= []).push(t);

  return (
    <div>
      <div className="mb-6">
        <h2 className="text-lg font-semibold text-text-primary">Scenario Templates</h2>
        <p className="text-[13px] text-text-tertiary mt-1">Pre-built agent scenarios for common enterprise use cases.</p>
      </div>

      <div className="space-y-8">
        {Object.entries(grouped).map(([category, tmpls]) => (
          <div key={category}>
            <h3 className="text-[11px] font-medium text-text-tertiary uppercase tracking-wider mb-3">{category}</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {tmpls.map(t => (
                <div key={t.id} className="bg-white rounded-lg border border-border p-5 hover:border-border-strong transition-colors flex flex-col">
                  <div className="flex items-center gap-2 mb-2">
                    <span className={`text-xs font-medium ${DIFFICULTY_STYLES[t.difficulty]}`}>{t.difficulty}</span>
                    <span className="text-xs text-text-tertiary">~{t.estimated_actions} actions</span>
                  </div>
                  <h4 className="text-[13px] font-medium text-text-primary mb-1">{t.name}</h4>
                  <p className="text-xs text-text-tertiary flex-1 mb-3 leading-relaxed">{t.description}</p>
                  <button
                    onClick={() => onUseTemplate(t.id)}
                    className="self-start px-3 py-1.5 bg-text-primary text-white text-xs font-medium rounded-md hover:bg-black/80 transition-colors"
                  >
                    Use Template
                  </button>
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
