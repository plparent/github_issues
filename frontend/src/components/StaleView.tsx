import { useState } from "react";
import { fetchStaleIssues } from "../api";
import { formatDate } from "../format";
import type { RepoTimeframe, StaleIssue } from "../types";

export default function StaleView({ owner, repo, start, end }: RepoTimeframe) {
  const [staleDays, setStaleDays] = useState(30);
  const [rows, setRows] = useState<StaleIssue[] | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function run() {
    setLoading(true);
    setError(null);
    try {
      setRows(await fetchStaleIssues(owner, repo, start, end, staleDays));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Request failed");
      setRows(null);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="panel">
      <div className="panel-header">
        <p className="panel-description">
          Open issues created in the timeframe with no event for at least the given number of
          days, most stale first.
        </p>
        <div className="panel-controls">
          <div className="field field-inline">
            <label htmlFor="stale-days">Stale after (days)</label>
            <input
              id="stale-days"
              type="number"
              min={1}
              value={staleDays}
              onChange={(e) => setStaleDays(Number(e.target.value))}
            />
          </div>
          <button onClick={run} disabled={loading}>
            {loading ? "Running…" : "Run"}
          </button>
        </div>
      </div>

      {error && <p className="error">{error}</p>}

      {rows && rows.length === 0 && (
        <p className="empty">No stale issues found for this timeframe and threshold.</p>
      )}

      {rows && rows.length > 0 && (
        <table>
          <thead>
            <tr>
              <th>Issue</th>
              <th>Created</th>
              <th>Last event</th>
              <th>Days stale</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row.issue_number}>
                <td>#{row.issue_number}</td>
                <td>{formatDate(row.created_at)}</td>
                <td>{row.last_event_at ? formatDate(row.last_event_at) : "no events"}</td>
                <td className="num">{row.days_since_last_event}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
