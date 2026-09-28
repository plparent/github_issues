// Mirrors the Pydantic response models in api.py.

export interface IssueEventCount {
  issue_number: number;
  status: string;
  created_at: string;
  closed_at: string | null;
  event_count: number;
}

export interface NarrativeResponse {
  narrative: string;
  confidence: number | null;
  issues_considered: number;
  total_events: number;
}

export interface StaleIssue {
  issue_number: number;
  status: string;
  created_at: string;
  closed_at: string | null;
  last_event_at: string | null;
  days_since_last_event: number;
}

export interface RepoTimeframe {
  owner: string;
  repo: string;
  /** date input value ("YYYY-MM-DD"), treated as UTC for this demo - see api.ts */
  start: string;
  end: string;
}
