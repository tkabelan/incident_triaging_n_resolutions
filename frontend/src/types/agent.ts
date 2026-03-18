export type StageError = {
  type: string;
  message: string;
  is_rate_limited?: boolean;
  retryable?: boolean;
};

export type StageData = {
  status: string;
  confidence?: number | null;
  reasoning?: string | null;
  items?: Array<Record<string, unknown>>;
  notes?: string[];
  results?: number;
  direct_match?: boolean;
  evidence_count?: number;
  top_match_score?: number | null;
  direct_match_threshold?: number | null;
  passed?: boolean | null;
  needs_web_search?: boolean | null;
  classification?: string | null;
  resolution?: string | null;
  attempts?: number;
  next_action?: string | null;
  decision_reason?: string | null;
  reason?: string | null;
  error?: StageError | null;
};

export type WebSearchItem = {
  title?: string;
  url?: string;
  score?: number;
  content?: string;
};

export type AgentTrace = {
  final_status: string;
  outcome_source?: string | null;
  classification?: string | null;
  main_category?: string | null;
  subcategory?: string | null;
  resolution?: string | null;
  branch_explanation?: string | null;
  kb_update_triggered?: boolean;
  kb_update_reference?: string | null;
  kb_update_reason?: string | null;
  steps: string[];
  stages: Record<string, StageData>;
};

export type ProcessErrorRequest = {
  error_text: string;
  row_id?: string;
  source_file?: string;
  force_web_search?: boolean;
};

export type ProcessErrorResponse = {
  row_id: string;
  status: string;
  agent_trace: AgentTrace;
  models?: {
    primary_classification: string;
    verification: string;
  } | null;
  classification?: {
    category?: string | null;
    main_category?: string | null;
    subcategory?: string | null;
    confidence?: number | null;
    reasoning?: string | null;
    proposed_resolution?: string | null;
  } | null;
  verification?: Record<string, unknown> | null;
  kb_update_reference?: string | null;
  error?: StageError | null;
};

export type ProcessProgressEvent = {
  type: "progress";
  stage: string;
  status: string;
  title: string;
  description: string;
};

export type ProcessResultEvent = {
  type: "result";
  payload: ProcessErrorResponse;
};

export type ProcessDoneEvent = {
  type: "done";
};

export type ProcessStreamErrorEvent = {
  type: "error";
  payload: {
    message: string;
    error_type?: string;
  };
};

export type ProcessStreamEvent =
  | ProcessProgressEvent
  | ProcessResultEvent
  | ProcessDoneEvent
  | ProcessStreamErrorEvent;
