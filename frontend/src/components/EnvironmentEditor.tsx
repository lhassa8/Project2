import { useState } from 'react';

interface EnvironmentConfig {
  filesystem: Record<string, string>;
  database: Record<string, Record<string, unknown>[]>;
  http_stubs: { url_pattern: string; method?: string; status_code?: number; response_body?: unknown }[];
}

interface Props {
  value: EnvironmentConfig;
  onChange: (env: EnvironmentConfig) => void;
}

type Tab = 'filesystem' | 'database' | 'http_stubs';

export default function EnvironmentEditor({ value, onChange }: Props) {
  const [tab, setTab] = useState<Tab>('filesystem');
  const [newFilePath, setNewFilePath] = useState('');
  const [newFileContent, setNewFileContent] = useState('');
  const [newTableName, setNewTableName] = useState('');
  const [newTableJson, setNewTableJson] = useState('[]');
  const [newStubUrl, setNewStubUrl] = useState('');
  const [newStubMethod, setNewStubMethod] = useState('GET');
  const [newStubStatus, setNewStubStatus] = useState('200');
  const [newStubBody, setNewStubBody] = useState('{}');

  const tabs: { key: Tab; label: string; count: number }[] = [
    { key: 'filesystem', label: 'Files', count: Object.keys(value.filesystem).length },
    { key: 'database', label: 'Database', count: Object.keys(value.database).length },
    { key: 'http_stubs', label: 'HTTP Stubs', count: value.http_stubs.length },
  ];

  const addFile = () => { if (!newFilePath.trim()) return; onChange({ ...value, filesystem: { ...value.filesystem, [newFilePath]: newFileContent } }); setNewFilePath(''); setNewFileContent(''); };
  const removeFile = (path: string) => { const next = { ...value.filesystem }; delete next[path]; onChange({ ...value, filesystem: next }); };
  const addTable = () => { if (!newTableName.trim()) return; try { const rows = JSON.parse(newTableJson); onChange({ ...value, database: { ...value.database, [newTableName]: Array.isArray(rows) ? rows : [] } }); setNewTableName(''); setNewTableJson('[]'); } catch {} };
  const removeTable = (name: string) => { const next = { ...value.database }; delete next[name]; onChange({ ...value, database: next }); };
  const addStub = () => { if (!newStubUrl.trim()) return; try { const body = JSON.parse(newStubBody); onChange({ ...value, http_stubs: [...value.http_stubs, { url_pattern: newStubUrl, method: newStubMethod, status_code: parseInt(newStubStatus, 10), response_body: body }] }); setNewStubUrl(''); setNewStubBody('{}'); } catch {} };
  const removeStub = (idx: number) => { onChange({ ...value, http_stubs: value.http_stubs.filter((_, i) => i !== idx) }); };

  return (
    <div className="border border-border rounded-lg overflow-hidden">
      <div className="flex border-b border-border bg-surface-secondary">
        {tabs.map(t => (
          <button key={t.key} type="button" onClick={() => setTab(t.key)} className={`px-4 py-2 text-xs font-medium border-b-2 transition-colors ${tab === t.key ? 'border-text-primary text-text-primary bg-white' : 'border-transparent text-text-tertiary hover:text-text-secondary'}`}>
            {t.label}{t.count > 0 && <span className="text-text-tertiary ml-1">({t.count})</span>}
          </button>
        ))}
      </div>

      <div className="p-4">
        {tab === 'filesystem' && (
          <div className="space-y-3">
            {Object.entries(value.filesystem).map(([path, content]) => (
              <div key={path} className="bg-surface-secondary rounded-md p-3">
                <div className="flex items-center justify-between mb-1">
                  <code className="text-xs text-text-secondary font-mono">{path}</code>
                  <button type="button" onClick={() => removeFile(path)} className="text-xs text-red-500 hover:text-red-600">Remove</button>
                </div>
                <pre className="text-xs text-text-tertiary max-h-20 overflow-auto">{content.slice(0, 200)}{content.length > 200 ? '...' : ''}</pre>
              </div>
            ))}
            <div className="border border-dashed border-border rounded-md p-3 space-y-2">
              <input type="text" value={newFilePath} onChange={e => setNewFilePath(e.target.value)} placeholder="/path/to/file.txt" className="w-full px-2 py-1 border border-border rounded text-xs font-mono focus:outline-none focus:ring-1 focus:ring-accent/30 bg-white" />
              <textarea value={newFileContent} onChange={e => setNewFileContent(e.target.value)} placeholder="File content..." rows={3} className="w-full px-2 py-1 border border-border rounded text-xs font-mono focus:outline-none focus:ring-1 focus:ring-accent/30 resize-none bg-white" />
              <button type="button" onClick={addFile} className="text-xs text-accent hover:text-accent-dark font-medium">+ Add File</button>
            </div>
          </div>
        )}

        {tab === 'database' && (
          <div className="space-y-3">
            {Object.entries(value.database).map(([name, rows]) => (
              <div key={name} className="bg-surface-secondary rounded-md p-3">
                <div className="flex items-center justify-between mb-1">
                  <span className="text-xs font-medium text-text-secondary">{name} <span className="text-text-tertiary">({rows.length} rows)</span></span>
                  <button type="button" onClick={() => removeTable(name)} className="text-xs text-red-500 hover:text-red-600">Remove</button>
                </div>
                {rows.length > 0 && (
                  <div className="overflow-auto max-h-32">
                    <table className="text-xs w-full">
                      <thead><tr>{Object.keys(rows[0]).map(col => <th key={col} className="text-left py-1 px-2 text-text-tertiary font-medium">{col}</th>)}</tr></thead>
                      <tbody>{rows.slice(0, 5).map((row, i) => <tr key={i} className="border-t border-border">{Object.values(row).map((val, j) => <td key={j} className="py-1 px-2 text-text-secondary">{String(val)}</td>)}</tr>)}</tbody>
                    </table>
                    {rows.length > 5 && <div className="text-xs text-text-tertiary px-2">+{rows.length - 5} more</div>}
                  </div>
                )}
              </div>
            ))}
            <div className="border border-dashed border-border rounded-md p-3 space-y-2">
              <input type="text" value={newTableName} onChange={e => setNewTableName(e.target.value)} placeholder="Table name" className="w-full px-2 py-1 border border-border rounded text-xs focus:outline-none focus:ring-1 focus:ring-accent/30 bg-white" />
              <textarea value={newTableJson} onChange={e => setNewTableJson(e.target.value)} placeholder='[{"id": 1, "name": "Example"}]' rows={3} className="w-full px-2 py-1 border border-border rounded text-xs font-mono focus:outline-none focus:ring-1 focus:ring-accent/30 resize-none bg-white" />
              <button type="button" onClick={addTable} className="text-xs text-accent hover:text-accent-dark font-medium">+ Add Table</button>
            </div>
          </div>
        )}

        {tab === 'http_stubs' && (
          <div className="space-y-3">
            {value.http_stubs.map((stub, i) => (
              <div key={i} className="bg-surface-secondary rounded-md p-3">
                <div className="flex items-center justify-between mb-1">
                  <span className="text-xs text-text-secondary">
                    <span className="font-medium text-accent">{stub.method || '*'}</span>{' '}
                    <code className="font-mono">{stub.url_pattern}</code>{' '}
                    <span className="text-text-tertiary">({stub.status_code || 200})</span>
                  </span>
                  <button type="button" onClick={() => removeStub(i)} className="text-xs text-red-500 hover:text-red-600">Remove</button>
                </div>
                <pre className="text-xs text-text-tertiary max-h-16 overflow-auto">{JSON.stringify(stub.response_body, null, 2)?.slice(0, 200)}</pre>
              </div>
            ))}
            <div className="border border-dashed border-border rounded-md p-3 space-y-2">
              <div className="grid grid-cols-4 gap-2">
                <select value={newStubMethod} onChange={e => setNewStubMethod(e.target.value)} className="px-2 py-1 border border-border rounded text-xs focus:outline-none focus:ring-1 focus:ring-accent/30 bg-white">
                  <option value="*">ANY</option><option value="GET">GET</option><option value="POST">POST</option><option value="PUT">PUT</option><option value="DELETE">DELETE</option>
                </select>
                <input type="text" value={newStubUrl} onChange={e => setNewStubUrl(e.target.value)} placeholder="URL pattern" className="col-span-2 px-2 py-1 border border-border rounded text-xs font-mono focus:outline-none focus:ring-1 focus:ring-accent/30 bg-white" />
                <input type="text" value={newStubStatus} onChange={e => setNewStubStatus(e.target.value)} placeholder="200" className="px-2 py-1 border border-border rounded text-xs focus:outline-none focus:ring-1 focus:ring-accent/30 bg-white" />
              </div>
              <textarea value={newStubBody} onChange={e => setNewStubBody(e.target.value)} placeholder='{"status": "ok"}' rows={2} className="w-full px-2 py-1 border border-border rounded text-xs font-mono focus:outline-none focus:ring-1 focus:ring-accent/30 resize-none bg-white" />
              <button type="button" onClick={addStub} className="text-xs text-accent hover:text-accent-dark font-medium">+ Add Stub</button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
