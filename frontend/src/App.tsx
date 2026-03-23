import { useState } from 'react';
import RunHistory from './components/RunHistory';
import RunDetail from './components/RunDetail';
import NewRunForm from './components/NewRunForm';

type View = { page: 'history' } | { page: 'detail'; runId: string } | { page: 'new' };

export default function App() {
  const [view, setView] = useState<View>({ page: 'history' });

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white border-b border-gray-200 sticky top-0 z-10">
        <div className="max-w-6xl mx-auto px-4 py-3 flex items-center justify-between">
          <button
            onClick={() => setView({ page: 'history' })}
            className="flex items-center gap-2 hover:opacity-80"
          >
            <div className="w-8 h-8 bg-indigo-600 rounded-lg flex items-center justify-center">
              <span className="text-white font-bold text-sm">AS</span>
            </div>
            <h1 className="text-lg font-semibold text-gray-900">AgentSandbox</h1>
          </button>
          <button
            onClick={() => setView({ page: 'new' })}
            className="px-4 py-2 bg-indigo-600 text-white text-sm font-medium rounded-lg hover:bg-indigo-700 transition-colors"
          >
            New Run
          </button>
        </div>
      </header>

      <main className="max-w-6xl mx-auto px-4 py-6">
        {view.page === 'history' && (
          <RunHistory onSelect={(id) => setView({ page: 'detail', runId: id })} />
        )}
        {view.page === 'detail' && (
          <RunDetail
            runId={view.runId}
            onBack={() => setView({ page: 'history' })}
          />
        )}
        {view.page === 'new' && (
          <NewRunForm
            onCreated={(id) => setView({ page: 'detail', runId: id })}
            onCancel={() => setView({ page: 'history' })}
          />
        )}
      </main>
    </div>
  );
}
