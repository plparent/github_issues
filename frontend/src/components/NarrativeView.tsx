import { useState } from "react";
import { fetchIssueNarrative } from "../api";
import type { NarrativeResponse, RepoTimeframe } from "../types";

export default function NarrativeView({ owner, repo, start, end }: RepoTimeframe) {
  const [result, setResult] = useState<NarrativeResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function run() {
    setLoading(true);
    setError(null);
    try {
      setResult(await fetchIssueNarrative(owner, repo, start, end));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Request failed");
      setResult(null);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="panel">
      <div className="panel-header">
        <p className="panel-description">
          Sends the same numbers to a local Ollama model and asks it for a short narrative.
          Can take a while on first run, or on a slow model.
        </p>
        <button onClick={run} disabled={loading}>
          {loading ? "Asking Ollama…" : "Run"}
        </button>
      </div>

      {error && <p className="error">{error}</p>}

      {result && (
        <div className="narrative-card">
          <p className="narrative-text">{result.narrative}</p>
          <div className="narrative-stats">
            <div>
              <span className="stat-value">{result.issues_considered}</span>
              <span className="stat-label">issues considered</span>
            </div>
            <div>
              <span className="stat-value">{result.total_events}</span>
              <span className="stat-label">total events</span>
            </div>
            <div>
              <span className="stat-value">
                {result.confidence != null ? `${Math.round(result.confidence * 100)}%` : "—"}
              </span>
              <span className="stat-label">confidence</span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
