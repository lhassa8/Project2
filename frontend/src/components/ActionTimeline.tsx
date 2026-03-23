import { useState } from 'react';
import type { AgentAction } from '../types';

interface Props {
  actions: AgentAction[];
}

const ACTION_STYLES: Record<string, { bg: string; border: string; label: string; icon: string }> = {
  thought: { bg: 'bg-purple-50', border: 'border-purple-200', label: 'Thought', icon: '🧠' },
  tool_call: { bg: 'bg-blue-50', border: 'border-blue-200', label: 'Tool Call', icon: '⚡' },
  tool_response: { bg: 'bg-emerald-50', border: 'border-emerald-200', label: 'Response', icon: '📦' },
  final_output: { bg: 'bg-amber-50', border: 'border-amber-200', label: 'Output', icon: '✅' },
};

export default function ActionTimeline({ actions }: Props) {
  const [expandedSet, setExpandedSet] = useState<Set<number>>(new Set());

  const toggle = (seq: number) => {
    setExpandedSet(prev => {
      const next = new Set(prev);
      if (next.has(seq)) next.delete(seq);
      else next.add(seq);
      return next;
    });
  };

  if (actions.length === 0) {
    return (
      <div className="bg-white rounded-lg border border-gray-200 p-8 text-center text-gray-400">
        <div className="animate-pulse">Waiting for agent actions...</div>
      </div>
    );
  }

  return (
    <div className="space-y-2">
      {actions.map((action) => {
        const style = ACTION_STYLES[action.action_type] ?? ACTION_STYLES.thought;
        const expanded = expandedSet.has(action.sequence);
        const toolName = typeof action.content.tool === 'string' ? action.content.tool : '';
        const textContent = typeof action.content.text === 'string' ? action.content.text : '';

        return (
          <div
            key={action.sequence}
            className={`${style.bg} border ${style.border} rounded-lg overflow-hidden`}
          >
            <button
              onClick={() => toggle(action.sequence)}
              className="w-full text-left px-4 py-3 flex items-center justify-between"
            >
              <div className="flex items-center gap-3">
                <span className="text-base">{style.icon}</span>
                <span className="text-xs font-medium text-gray-500">#{action.sequence}</span>
                <span className="text-sm font-medium text-gray-800">{style.label}</span>
                {action.action_type === 'tool_call' && toolName && (
                  <code className="text-xs bg-white/60 px-2 py-0.5 rounded font-mono">
                    {toolName}
                  </code>
                )}
                {action.action_type === 'thought' && textContent && (
                  <span className="text-sm text-gray-600 truncate max-w-md">
                    {textContent.slice(0, 80)}
                    {textContent.length > 80 ? '...' : ''}
                  </span>
                )}
                {action.action_type === 'final_output' && textContent && (
                  <span className="text-sm text-gray-600 truncate max-w-md">
                    {textContent.slice(0, 80)}
                    {textContent.length > 80 ? '...' : ''}
                  </span>
                )}
              </div>
              <div className="flex items-center gap-3 text-xs text-gray-400">
                {action.mock_system && (
                  <span className="bg-white/60 px-2 py-0.5 rounded">{action.mock_system}</span>
                )}
                {action.duration_ms > 0 && <span>{action.duration_ms}ms</span>}
                <span>{expanded ? '▾' : '▸'}</span>
              </div>
            </button>

            {expanded && (
              <div className="px-4 pb-3 border-t border-inherit">
                <pre className="text-xs text-gray-700 whitespace-pre-wrap font-mono mt-2 max-h-80 overflow-auto">
                  {JSON.stringify(action.content, null, 2)}
                </pre>
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
