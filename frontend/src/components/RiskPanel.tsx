import type { PolicyViolation, RiskReport } from '../types';

interface Props {
  riskReport: RiskReport | null;
  policyViolations: PolicyViolation[];
}

const LEVEL_COLORS: Record<string, { text: string; bg: string; bar: string }> = {
  low: { text: 'text-emerald-700', bg: 'bg-emerald-50', bar: 'bg-emerald-500' },
  medium: { text: 'text-amber-700', bg: 'bg-amber-50', bar: 'bg-amber-500' },
  high: { text: 'text-orange-700', bg: 'bg-orange-50', bar: 'bg-orange-500' },
  critical: { text: 'text-red-700', bg: 'bg-red-50', bar: 'bg-red-500' },
};

export default function RiskPanel({ riskReport, policyViolations }: Props) {
  return (
    <div className="space-y-3">
      {policyViolations.length > 0 && (
        <div className="bg-red-50 border border-red-100 rounded-lg p-4">
          <h4 className="text-[13px] font-medium text-red-800 mb-2">
            Policy Violations ({policyViolations.length})
          </h4>
          <div className="space-y-1.5">
            {policyViolations.map((v, i) => (
              <div key={i} className="flex items-start gap-2 text-xs">
                <span className={`mt-0.5 px-1.5 py-0.5 rounded text-[10px] font-medium ${
                  v.policy_action === 'block' ? 'bg-red-100 text-red-700' :
                  v.policy_action === 'require_approval' ? 'bg-orange-100 text-orange-700' :
                  'bg-amber-100 text-amber-700'
                }`}>
                  {v.policy_action}
                </span>
                <span className="text-text-secondary">{v.description}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {riskReport && (() => {
        const colors = LEVEL_COLORS[riskReport.risk_level] ?? LEVEL_COLORS.low;
        return (
          <div className="bg-white border border-border rounded-lg p-4">
            <div className="flex items-center justify-between mb-3">
              <h4 className="text-[13px] font-medium text-text-primary">Risk Assessment</h4>
              <div className="flex items-center gap-2">
                <span className={`text-xs font-medium px-2 py-0.5 rounded ${colors.bg} ${colors.text}`}>
                  {riskReport.risk_level}
                </span>
                <span className="text-sm font-semibold text-text-primary">{riskReport.overall_score}</span>
              </div>
            </div>

            {/* Score bar */}
            <div className="h-1.5 bg-surface-secondary rounded-full overflow-hidden mb-3">
              <div className={`h-full rounded-full ${colors.bar}`} style={{ width: `${riskReport.overall_score}%` }} />
            </div>

            <p className="text-xs text-text-secondary mb-3">{riskReport.summary}</p>

            {riskReport.signals.length > 0 && (
              <div className="mb-3">
                <div className="text-xs font-medium text-text-tertiary mb-2">Signals</div>
                <div className="space-y-1">
                  {riskReport.signals.slice(0, 8).map((s, i) => (
                    <div key={i} className="flex items-center gap-2 text-xs">
                      <span className="text-text-tertiary w-6 text-right font-mono">{s.severity}</span>
                      <div className="flex-shrink-0 w-12">
                        <div className="h-1 bg-surface-secondary rounded-full overflow-hidden">
                          <div
                            className={`h-full rounded-full ${
                              s.severity >= 80 ? 'bg-red-400' :
                              s.severity >= 60 ? 'bg-orange-400' :
                              s.severity >= 40 ? 'bg-amber-400' :
                              'bg-emerald-400'
                            }`}
                            style={{ width: `${s.severity}%` }}
                          />
                        </div>
                      </div>
                      <span className="text-text-secondary">{s.description}</span>
                    </div>
                  ))}
                  {riskReport.signals.length > 8 && (
                    <div className="text-xs text-text-tertiary">+{riskReport.signals.length - 8} more</div>
                  )}
                </div>
              </div>
            )}

            {riskReport.recommendations.length > 0 && (
              <div>
                <div className="text-xs font-medium text-text-tertiary mb-1.5">Recommendations</div>
                <ul className="space-y-1">
                  {riskReport.recommendations.map((rec, i) => (
                    <li key={i} className="text-xs text-text-secondary flex gap-1.5">
                      <span className="text-text-tertiary flex-shrink-0">-</span>
                      {rec}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        );
      })()}
    </div>
  );
}
