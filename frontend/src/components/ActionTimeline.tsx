import { useState } from 'react';
import type { AgentAction } from '../types';

interface Props {
  actions: AgentAction[];
}

const ACTION_STYLES: Record<string, { bg: string; border: string; label: string; dot: string }> = {
  thought: { bg: 'bg-surface-secondary', border: 'border-border', label: 'Thought', dot: 'bg-text-tertiary' },
  tool_call: { bg: 'bg-white', border: 'border-border', label: 'Tool Call', dot: 'bg-accent' },
  tool_response: { bg: 'bg-white', border: 'border-border', label: 'Response', dot: 'bg-emerald-500' },
  final_output: { bg: 'bg-accent-light', border: 'border-accent/20', label: 'Output', dot: 'bg-accent-dark' },
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
      <div className="bg-white rounded-lg border border-border p-8 text-center text-text-tertiary">
        <div className="animate-pulse">Waiting for agent actions...</div>
      </div>
    );
  }

  return (
    <div className="space-y-1.5">
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
              className="w-full text-left px-4 py-2.5 flex items-center justify-between"
            >
              <div className="flex items-center gap-2.5">
                <span className={`w-2 h-2 rounded-full flex-shrink-0 ${style.dot}`} />
                <span className="text-xs text-text-tertiary font-mono">#{action.sequence}</span>
                <span className="text-[13px] font-medium text-text-primary">{style.label}</span>
                {action.action_type === 'tool_call' && toolName && (
                  <code className="text-xs bg-surface-secondary px-1.5 py-0.5 rounded font-mono text-text-secondary">
                    {toolName}
                  </code>
                )}
                {(action.action_type === 'thought' || action.action_type === 'final_output') && textContent && (
                  <span className="text-[13px] text-text-tertiary truncate max-w-md">
                    {textContent.slice(0, 80)}{textContent.length > 80 ? '...' : ''}
                  </span>
                )}
              </div>
              <div className="flex items-center gap-2.5 text-xs text-text-tertiary">
                {action.duration_ms > 0 && <span>{action.duration_ms}ms</span>}
                <svg className={`w-3.5 h-3.5 transition-transform ${expanded ? 'rotate-180' : ''}`} fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" d="m19.5 8.25-7.5 7.5-7.5-7.5" />
                </svg>
              </div>
            </button>

            {expanded && (
              <div className="px-4 pb-3 border-t border-border">
                <pre className="text-xs text-text-secondary whitespace-pre-wrap font-mono mt-2 max-h-80 overflow-auto leading-relaxed">
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
