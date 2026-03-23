import { useTemplates } from '../hooks/useApi';

interface Props {
  onUseTemplate: (templateId: string) => void;
}

const CATEGORY_STYLES: Record<string, string> = {
  'Sales & CRM': 'bg-blue-100 text-blue-700',
  'DevOps & SRE': 'bg-orange-100 text-orange-700',
  'HR & People Ops': 'bg-purple-100 text-purple-700',
  'Data Engineering': 'bg-emerald-100 text-emerald-700',
  'Security & Compliance': 'bg-red-100 text-red-700',
  'Customer Success': 'bg-amber-100 text-amber-700',
};

const DIFFICULTY_STYLES: Record<string, string> = {
  low: 'text-green-600',
  medium: 'text-yellow-600',
  high: 'text-red-600',
};

export default function TemplateLibrary({ onUseTemplate }: Props) {
  const { templates, loading } = useTemplates();

  if (loading) {
    return <div className="text-center py-12 text-gray-400">Loading templates...</div>;
  }

  // Group by category
  const grouped: Record<string, typeof templates> = {};
  for (const t of templates) {
    (grouped[t.category] ??= []).push(t);
  }

  return (
    <div>
      <div className="mb-6">
        <h2 className="text-lg font-semibold text-gray-800">Scenario Templates</h2>
        <p className="text-sm text-gray-500 mt-1">
          Pre-built agent scenarios for common enterprise use cases. Select a template to start a sandbox run.
        </p>
      </div>

      <div className="space-y-8">
        {Object.entries(grouped).map(([category, tmpls]) => (
          <div key={category}>
            <h3 className="text-sm font-semibold text-gray-600 uppercase tracking-wide mb-3">{category}</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {tmpls.map(t => (
                <div
                  key={t.id}
                  className="bg-white rounded-xl border border-gray-200 p-5 hover:border-indigo-300 hover:shadow-md transition-all flex flex-col"
                >
                  <div className="flex items-center gap-2 mb-2">
                    <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${CATEGORY_STYLES[category] ?? 'bg-gray-100 text-gray-600'}`}>
                      {category}
                    </span>
                    <span className={`text-xs font-medium ${DIFFICULTY_STYLES[t.difficulty]}`}>
                      {t.difficulty}
                    </span>
                  </div>
                  <h4 className="text-sm font-semibold text-gray-900 mb-1">{t.name}</h4>
                  <p className="text-xs text-gray-500 flex-1 mb-3">{t.description}</p>
                  <div className="flex items-center justify-between">
                    <span className="text-xs text-gray-400">~{t.estimated_actions} actions</span>
                    <button
                      onClick={() => onUseTemplate(t.id)}
                      className="px-3 py-1.5 bg-indigo-600 text-white text-xs font-medium rounded-lg hover:bg-indigo-700 transition-colors"
                    >
                      Use Template
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
