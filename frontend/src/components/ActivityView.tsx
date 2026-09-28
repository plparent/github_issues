import { useState } from "react";
import { fetchIssueActivity } from "../api";
import { formatDate } from "../format";
import type { IssueEventCount, RepoTimeframe } from "../types";

export default function ActivityView({ owner, repo, start, end }: RepoTimeframe) {
  const [rows, setRows] = useState<IssueEventCount[] | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function run() {
    setLoading(true);
    setError(null);
    try {
      setRows(await fetchIssueActivity(owner, repo, start, end));
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
          Issues ranked by how many timeline events fell in the timeframe. Issues with no
          events in the window are left out.
        </p>
        <button onClick={run} disabled={loading}>
          {loading ? "Running…" : "Run"}
        </button>
      </div>

      {error && <p className="error">{error}</p>}

      {rows && rows.length === 0 && <p className="empty">No issues had activity in this timeframe.</p>}

      {rows && rows.length > 0 && (
        <table>
          <thead>
            <tr>
              <th>Issue</th>
              <th>Status</th>
              <th>Created</th>
              <th>Closed</th>
              <th>Events</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row.issue_number}>
                <td>#{row.issue_number}</td>
                <td>
                  <span className={`badge badge-${row.status}`}>{row.status}</span>
                </td>
                <td>{formatDate(row.created_at)}</td>
                <td>{formatDate(row.closed_at)}</td>
                <td className="num">{row.event_count}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
