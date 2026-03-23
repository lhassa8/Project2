import { useState } from 'react';
import RunHistory from './components/RunHistory';
import RunDetail from './components/RunDetail';
import NewRunForm from './components/NewRunForm';
import Dashboard from './components/Dashboard';
import TemplateLibrary from './components/TemplateLibrary';
import PoliciesView from './components/PoliciesView';
import RunComparisonView from './components/RunComparison';
import AuditLog from './components/AuditLog';
import WebhooksView from './components/WebhooksView';

type View =
  | { page: 'dashboard' }
  | { page: 'history' }
  | { page: 'detail'; runId: string }
  | { page: 'new'; templateId?: string }
  | { page: 'templates' }
  | { page: 'policies' }
  | { page: 'compare'; initialRunA?: string }
  | { page: 'audit' }
  | { page: 'webhooks' };

const NAV_ITEMS: { page: View['page']; label: string }[] = [
  { page: 'dashboard', label: 'Dashboard' },
  { page: 'history', label: 'Runs' },
  { page: 'templates', label: 'Templates' },
  { page: 'compare', label: 'Compare' },
  { page: 'policies', label: 'Policies' },
  { page: 'audit', label: 'Audit' },
  { page: 'webhooks', label: 'Webhooks' },
];

export default function App() {
  const [view, setView] = useState<View>({ page: 'dashboard' });

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white border-b border-gray-200 sticky top-0 z-10">
        <div className="max-w-7xl mx-auto px-4 py-0 flex items-center justify-between">
          <div className="flex items-center gap-6">
            <button
              onClick={() => setView({ page: 'dashboard' })}
              className="flex items-center gap-2.5 py-3 hover:opacity-80"
            >
              <div className="w-8 h-8 bg-gradient-to-br from-indigo-600 to-violet-600 rounded-lg flex items-center justify-center shadow-sm">
                <span className="text-white font-bold text-xs tracking-tight">AS</span>
              </div>
              <div>
                <h1 className="text-base font-semibold text-gray-900 leading-tight">AgentSandbox</h1>
                <p className="text-[10px] text-gray-400 leading-tight">Enterprise Simulation Layer</p>
              </div>
            </button>

            <nav className="flex items-center gap-0.5 ml-2">
              {NAV_ITEMS.map(({ page, label }) => (
                <button
                  key={page}
                  onClick={() => setView({ page } as View)}
                  className={`px-2.5 py-4 text-sm font-medium border-b-2 transition-colors ${
                    view.page === page
                      ? 'border-indigo-600 text-indigo-600'
                      : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                  }`}
                >
                  {label}
                </button>
              ))}
            </nav>
          </div>

          <button
            onClick={() => setView({ page: 'new' })}
            className="px-4 py-2 bg-gradient-to-r from-indigo-600 to-violet-600 text-white text-sm font-medium rounded-lg hover:from-indigo-700 hover:to-violet-700 transition-all shadow-sm"
          >
            New Run
          </button>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 py-6">
        {view.page === 'dashboard' && (
          <Dashboard
            onViewRun={(id) => setView({ page: 'detail', runId: id })}
            onNewRun={() => setView({ page: 'new' })}
          />
        )}
        {view.page === 'history' && (
          <RunHistory onSelect={(id) => setView({ page: 'detail', runId: id })} />
        )}
        {view.page === 'detail' && (
          <RunDetail
            runId={view.runId}
            onBack={() => setView({ page: 'history' })}
            onViewRun={(id) => setView({ page: 'detail', runId: id })}
            onCompare={(id) => setView({ page: 'compare', initialRunA: id })}
          />
        )}
        {view.page === 'new' && (
          <NewRunForm
            templateId={view.templateId}
            onCreated={(id) => setView({ page: 'detail', runId: id })}
            onCancel={() => setView({ page: 'history' })}
          />
        )}
        {view.page === 'templates' && (
          <TemplateLibrary
            onUseTemplate={(id) => setView({ page: 'new', templateId: id })}
          />
        )}
        {view.page === 'compare' && (
          <RunComparisonView
            initialRunA={view.initialRunA}
            onViewRun={(id) => setView({ page: 'detail', runId: id })}
          />
        )}
        {view.page === 'policies' && <PoliciesView />}
        {view.page === 'audit' && <AuditLog />}
        {view.page === 'webhooks' && <WebhooksView />}
      </main>
    </div>
  );
}
