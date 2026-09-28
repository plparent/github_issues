import type { RepoTimeframe } from "../types";

interface Props {
  value: RepoTimeframe;
  onChange: (value: RepoTimeframe) => void;
}

export default function TimeframeForm({ value, onChange }: Props) {
  return (
    <div className="panel timeframe-form">
      <div className="field">
        <label htmlFor="owner">Owner</label>
        <input
          id="owner"
          value={value.owner}
          onChange={(e) => onChange({ ...value, owner: e.target.value })}
          placeholder="psf"
        />
      </div>
      <div className="field">
        <label htmlFor="repo">Repo</label>
        <input
          id="repo"
          value={value.repo}
          onChange={(e) => onChange({ ...value, repo: e.target.value })}
          placeholder="requests"
        />
      </div>
      <div className="field">
        <label htmlFor="start">Start</label>
        <input
          id="start"
          type="date"
          value={value.start}
          onChange={(e) => onChange({ ...value, start: e.target.value })}
        />
      </div>
      <div className="field">
        <label htmlFor="end">End</label>
        <input
          id="end"
          type="date"
          value={value.end}
          onChange={(e) => onChange({ ...value, end: e.target.value })}
        />
      </div>
    </div>
  );
}
