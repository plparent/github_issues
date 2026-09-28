import type { IssueEventCount, NarrativeResponse, StaleIssue } from "./types";

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

/**
 * The <input type="date"> widgets used in this demo return a plain
 * "YYYY-MM-DD" string with no time or timezone. For simplicity, this app
 * treats the picked date as UTC rather than the user's local timezone - fine
 * for a demo, but worth knowing if a boundary issue looks off by a day.
 *
 * `start` is sent as the beginning of that day (00:00:00Z) and `end` as the
 * end of it (23:59:59Z), so picking the same date for both covers that
 * whole day rather than a zero-length window.
 */
function toUtcIso(dateValue: string, boundary: "start" | "end"): string {
  if (dateValue.length !== 10) return dateValue; // already a full ISO string
  return boundary === "start" ? `${dateValue}T00:00:00Z` : `${dateValue}T23:59:59Z`;
}

async function getJson<T>(path: string, params: Record<string, string>): Promise<T> {
  const query = new URLSearchParams(params);
  const response = await fetch(`${API_BASE}${path}?${query.toString()}`);
  if (!response.ok) {
    // FastAPI's HTTPException responses are {"detail": "..."}.
    const body = await response.json().catch(() => null);
    const detail = body && typeof body === "object" && "detail" in body ? body.detail : null;
    throw new Error(typeof detail === "string" ? detail : `Request failed (${response.status})`);
  }
  return response.json() as Promise<T>;
}

export function fetchIssueActivity(
  owner: string,
  repo: string,
  start: string,
  end: string
): Promise<IssueEventCount[]> {
  return getJson(`/${encodeURIComponent(owner)}/${encodeURIComponent(repo)}/issues/activity`, {
    start: toUtcIso(start, "start"),
    end: toUtcIso(end, "end"),
  });
}

export function fetchIssueNarrative(
  owner: string,
  repo: string,
  start: string,
  end: string
): Promise<NarrativeResponse> {
  return getJson(`/${encodeURIComponent(owner)}/${encodeURIComponent(repo)}/issues/narrative`, {
    start: toUtcIso(start, "start"),
    end: toUtcIso(end, "end"),
  });
}

export function fetchStaleIssues(
  owner: string,
  repo: string,
  start: string,
  end: string,
  staleDays: number
): Promise<StaleIssue[]> {
  return getJson(`/${encodeURIComponent(owner)}/${encodeURIComponent(repo)}/issues/stale`, {
    start: toUtcIso(start, "start"),
    end: toUtcIso(end, "end"),
    stale_days: String(staleDays),
  });
}
