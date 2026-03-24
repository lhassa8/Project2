import { useCallback, useEffect, useState } from 'react';
import RunHistory from './components/RunHistory';
import RunDetail from './components/RunDetail';
import NewRunForm from './components/NewRunForm';
import Dashboard from './components/Dashboard';
import TemplateLibrary from './components/TemplateLibrary';
import PoliciesView from './components/PoliciesView';
import RunComparisonView from './components/RunComparison';
import AuditLog from './components/AuditLog';
import WebhooksView from './components/WebhooksView';
import ErrorBoundary from './components/ErrorBoundary';

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

function viewToPath(view: View): string {
  switch (view.page) {
    case 'dashboard': return '/';
    case 'history': return '/runs';
    case 'detail': return `/runs/${view.runId}`;
    case 'new': return view.templateId ? `/new?template=${view.templateId}` : '/new';
    case 'templates': return '/templates';
    case 'policies': return '/policies';
    case 'compare': return view.initialRunA ? `/compare?run=${view.initialRunA}` : '/compare';
    case 'audit': return '/audit';
    case 'webhooks': return '/webhooks';
  }
}

function pathToView(path: string, search: string): View {
  const params = new URLSearchParams(search);
  if (path === '/' || path === '') return { page: 'dashboard' };
  if (path === '/runs') return { page: 'history' };
  if (path.startsWith('/runs/')) return { page: 'detail', runId: path.slice(6) };
  if (path === '/new') return { page: 'new', templateId: params.get('template') || undefined };
  if (path === '/templates') return { page: 'templates' };
  if (path === '/policies') return { page: 'policies' };
  if (path === '/compare') return { page: 'compare', initialRunA: params.get('run') || undefined };
  if (path === '/audit') return { page: 'audit' };
  if (path === '/webhooks') return { page: 'webhooks' };
  return { page: 'dashboard' };
}

export default function App() {
  const [view, setViewState] = useState<View>(() =>
    pathToView(window.location.pathname, window.location.search)
  );

  const setView = useCallback((v: View) => {
    setViewState(v);
    const path = viewToPath(v);
    window.history.pushState(null, '', path);
  }, []);

  useEffect(() => {
    const onPop = () => {
      setViewState(pathToView(window.location.pathname, window.location.search));
    };
    window.addEventListener('popstate', onPop);
    return () => window.removeEventListener('popstate', onPop);
  }, []);

  return (
    <div className="min-h-screen bg-page">
      <header className="bg-white border-b border-border sticky top-0 z-10">
        <div className="max-w-6xl mx-auto px-6 flex items-center justify-between">
          <div className="flex items-center gap-8">
            <button
              onClick={() => setView({ page: 'dashboard' })}
              className="flex items-center gap-2 py-4 hover:opacity-70 transition-opacity"
            >
              <span className="text-[15px] font-semibold text-text-primary tracking-tight">AgentSandbox</span>
            </button>

            <nav className="flex items-center gap-1">
              {NAV_ITEMS.map(({ page, label }) => (
                <button
                  key={page}
                  onClick={() => setView({ page } as View)}
                  className={`px-3 py-4 text-[13px] font-medium border-b-2 transition-colors ${
                    view.page === page
                      ? 'border-text-primary text-text-primary'
                      : 'border-transparent text-text-tertiary hover:text-text-secondary'
                  }`}
                >
                  {label}
                </button>
              ))}
            </nav>
          </div>

          <button
            onClick={() => setView({ page: 'new' })}
            className="px-4 py-1.5 bg-text-primary text-white text-[13px] font-medium rounded-md hover:bg-black/80 transition-colors"
          >
            New Run
          </button>
        </div>
      </header>

      <main className="max-w-6xl mx-auto px-6 py-8">
        <ErrorBoundary>
          {view.page === 'dashboard' && (
            <Dashboard
              onViewRun={(id) => setView({ page: 'detail', runId: id })}
              onNewRun={() => setView({ page: 'new' })}
              onViewTemplates={() => setView({ page: 'templates' })}
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
              onViewRun={(id) => setView({ page: 'detail', runId: id })}
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
        </ErrorBoundary>
      </main>
    </div>
  );
}
