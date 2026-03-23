import type { PolicyViolation, RiskReport } from '../types';

interface Props {
  riskReport: RiskReport | null;
  policyViolations: PolicyViolation[];
}

const LEVEL_STYLES: Record<string, { bg: string; border: string; text: string; ring: string }> = {
  low: { bg: 'bg-green-50', border: 'border-green-200', text: 'text-green-700', ring: 'text-green-500' },
  medium: { bg: 'bg-yellow-50', border: 'border-yellow-200', text: 'text-yellow-700', ring: 'text-yellow-500' },
  high: { bg: 'bg-orange-50', border: 'border-orange-200', text: 'text-orange-700', ring: 'text-orange-500' },
  critical: { bg: 'bg-red-50', border: 'border-red-200', text: 'text-red-700', ring: 'text-red-500' },
};

const CATEGORY_LABELS: Record<string, string> = {
  data_sensitivity: 'Data Sensitivity',
  blast_radius: 'Blast Radius',
  reversibility: 'Reversibility',
  privilege_escalation: 'Privilege Escalation',
  external_exposure: 'External Exposure',
};

export default function RiskPanel({ riskReport, policyViolations }: Props) {
  return (
    <div className="space-y-4">
      {/* Policy violations */}
      {policyViolations.length > 0 && (
        <div className="bg-red-50 border border-red-200 rounded-xl p-4">
          <h4 className="text-sm font-semibold text-red-800 mb-2">
            Policy Violations ({policyViolations.length})
          </h4>
          <div className="space-y-2">
            {policyViolations.map((v, i) => (
              <div key={i} className="flex items-start gap-2 text-xs">
                <span className={`mt-0.5 px-1.5 py-0.5 rounded font-medium ${
                  v.policy_action === 'block' ? 'bg-red-200 text-red-800' :
                  v.policy_action === 'require_approval' ? 'bg-orange-200 text-orange-800' :
                  'bg-yellow-200 text-yellow-800'
                }`}>
                  {v.policy_action}
                </span>
                <span className="text-red-700">{v.description}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Risk report */}
      {riskReport && (
        <div className={`rounded-xl border p-4 ${LEVEL_STYLES[riskReport.risk_level]?.bg} ${LEVEL_STYLES[riskReport.risk_level]?.border}`}>
          <div className="flex items-center justify-between mb-3">
            <h4 className="text-sm font-semibold text-gray-800">Risk Assessment</h4>
            <div className="flex items-center gap-2">
              <RiskScoreRing score={riskReport.overall_score} level={riskReport.risk_level} />
            </div>
          </div>

          <p className="text-xs text-gray-600 mb-3">{riskReport.summary}</p>

          {/* Signal categories */}
          {riskReport.signals.length > 0 && (
            <div className="mb-3">
              <div className="text-xs font-medium text-gray-500 mb-2">Signals</div>
              <div className="space-y-1.5">
                {riskReport.signals.slice(0, 8).map((s, i) => (
                  <div key={i} className="flex items-center gap-2 text-xs">
                    <div className="flex-shrink-0 w-16">
                      <div className="h-1.5 bg-gray-200 rounded-full overflow-hidden">
                        <div
                          className={`h-full rounded-full ${
                            s.severity >= 80 ? 'bg-red-500' :
                            s.severity >= 60 ? 'bg-orange-500' :
                            s.severity >= 40 ? 'bg-yellow-500' :
                            'bg-green-500'
                          }`}
                          style={{ width: `${s.severity}%` }}
                        />
                      </div>
                    </div>
                    <span className="text-gray-400 w-7 text-right">{s.severity}</span>
                    <span className="text-gray-600">{s.description}</span>
                    {s.action_sequence && (
                      <span className="text-gray-400">#{s.action_sequence}</span>
                    )}
                  </div>
                ))}
                {riskReport.signals.length > 8 && (
                  <div className="text-xs text-gray-400">
                    +{riskReport.signals.length - 8} more signals
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Recommendations */}
          {riskReport.recommendations.length > 0 && (
            <div>
              <div className="text-xs font-medium text-gray-500 mb-1.5">Recommendations</div>
              <ul className="space-y-1">
                {riskReport.recommendations.map((rec, i) => (
                  <li key={i} className="text-xs text-gray-600 flex gap-1.5">
                    <span className="text-gray-400 flex-shrink-0">-</span>
                    {rec}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function RiskScoreRing({ score, level }: { score: number; level: string }) {
  const style = LEVEL_STYLES[level] ?? LEVEL_STYLES.low;
  const circumference = 2 * Math.PI * 18;
  const offset = circumference - (score / 100) * circumference;

  return (
    <div className="relative w-12 h-12">
      <svg className="w-12 h-12 -rotate-90" viewBox="0 0 40 40">
        <circle cx="20" cy="20" r="18" fill="none" stroke="currentColor" strokeWidth="3" className="text-gray-200" />
        <circle
          cx="20" cy="20" r="18" fill="none" stroke="currentColor" strokeWidth="3"
          strokeDasharray={circumference} strokeDashoffset={offset}
          strokeLinecap="round" className={style.ring}
        />
      </svg>
      <div className="absolute inset-0 flex items-center justify-center">
        <span className={`text-xs font-bold ${style.text}`}>{score}</span>
      </div>
    </div>
  );
}
