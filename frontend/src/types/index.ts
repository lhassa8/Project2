export interface ToolConfig {
  name: string;
  enabled: boolean;
}

export interface EnvironmentConfig {
  filesystem: Record<string, string>;
  database: Record<string, Record<string, unknown>[]>;
  http_stubs: {
    url_pattern: string;
    method?: string;
    status_code?: number;
    response_body?: unknown;
    response_headers?: Record<string, string>;
  }[];
}

export interface AgentDefinition {
  name: string;
  goal: string;
  tools: ToolConfig[];
  model: string;
  max_tokens: number;
  temperature: number;
}

export interface RunContext {
  user_persona: string;
  initial_state: Record<string, unknown>;
  environment: EnvironmentConfig;
}

export interface AgentAction {
  sequence: number;
  action_type: 'thought' | 'tool_call' | 'tool_response' | 'final_output';
  content: Record<string, unknown>;
  timestamp: string;
  duration_ms: number;
  mock_system: string | null;
}

export interface StateDiff {
  system: string;
  resource_id: string;
  before: unknown;
  after: unknown;
  change_type: 'created' | 'modified' | 'deleted';
}

export interface ApprovalRecord {
  run_id: string;
  decision: 'approved' | 'changes_requested' | 'rejected';
  reviewer_notes: string;
  approved_at: string;
  signature: string;
}

export interface RiskSignal {
  category: string;
  description: string;
  severity: number;
  action_sequence: number | null;
}

export interface RiskReport {
  overall_score: number;
  risk_level: 'low' | 'medium' | 'high' | 'critical';
  signals: RiskSignal[];
  summary: string;
  recommendations: string[];
}

export interface PolicyViolation {
  policy_name: string;
  policy_action: 'allow' | 'warn' | 'block' | 'require_approval';
  description: string;
  action_sequence: number | null;
  details: Record<string, unknown>;
}

export interface EnvironmentSnapshot {
  filesystem: Record<string, string>;
  database: Record<string, Record<string, unknown>[]>;
  emails_sent: Record<string, unknown>[];
  http_log: Record<string, unknown>[];
}

export interface SandboxRun {
  id: string;
  workspace_id?: string;
  agent_definition: AgentDefinition;
  run_context: RunContext;
  status: 'running' | 'complete' | 'failed';
  actions: AgentAction[];
  diffs: StateDiff[];
  approval: ApprovalRecord | null;
  risk_report: RiskReport | null;
  policy_violations: PolicyViolation[];
  error: string | null;
  initial_snapshot: EnvironmentSnapshot | null;
  final_snapshot: EnvironmentSnapshot | null;
  created_at: string;
}

export interface Template {
  id: string;
  name: string;
  description: string;
  category: string;
  difficulty: 'low' | 'medium' | 'high';
  estimated_actions: number;
}

export interface TemplateDetail extends Template {
  agent_definition: AgentDefinition;
  run_context: RunContext;
}

export interface Analytics {
  total_runs: number;
  status_breakdown: Record<string, number>;
  approval_breakdown: Record<string, number>;
  tool_usage: Record<string, number>;
  avg_actions_per_run: number;
  risk_distribution: Record<string, number>;
  systems_touched: Record<string, number>;
  runs_over_time: { date: string; count: number }[];
  top_agents: { name: string; run_count: number }[];
}

export interface PolicyConfig {
  name: string;
  description: string;
  enabled: boolean;
  action: string;
}

export interface Workspace {
  id: string;
  name: string;
  role: string;
  api_key_name?: string;
  created_at: string;
}

export interface RunComparison {
  run_a_id: string;
  run_b_id: string;
  metadata: {
    run_a: { name: string; status: string; action_count: number; diff_count: number; created_at: string };
    run_b: { name: string; status: string; action_count: number; diff_count: number; created_at: string };
  };
  tool_usage: {
    run_a_total: number;
    run_b_total: number;
    per_tool: { tool: string; run_a_count: number; run_b_count: number; difference: number }[];
    tools_only_in_a: string[];
    tools_only_in_b: string[];
  };
  risk: {
    run_a: { overall_score: number; risk_level: string; signal_count: number };
    run_b: { overall_score: number; risk_level: string; signal_count: number };
    score_difference: number;
    risk_level_changed: boolean;
  };
  action_sequence: {
    run_a_sequence: string[];
    run_b_sequence: string[];
    sequences_identical: boolean;
    similarity: number;
  };
  environment: {
    available: boolean;
    filesystem?: { only_in_a: string[]; only_in_b: string[]; common: string[]; content_differs: string[] };
    database?: { only_in_a: string[]; only_in_b: string[]; common: string[]; row_count_diff: Record<string, number> };
    emails?: { run_a_count: number; run_b_count: number };
  };
  summary: string[];
}
