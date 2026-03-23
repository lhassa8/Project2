export interface ToolConfig {
  name: string;
  enabled: boolean;
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

export interface SandboxRun {
  id: string;
  agent_definition: AgentDefinition;
  run_context: RunContext;
  status: 'running' | 'complete' | 'failed';
  actions: AgentAction[];
  diffs: StateDiff[];
  approval: ApprovalRecord | null;
  error: string | null;
  created_at: string;
}
