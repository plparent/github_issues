import { useState } from "react";
import TimeframeForm from "./components/TimeframeForm";
import ActivityView from "./components/ActivityView";
import NarrativeView from "./components/NarrativeView";
import StaleView from "./components/StaleView";
import { toDateInputValue } from "./format";
import type { RepoTimeframe } from "./types";

type Tab = "activity" | "narrative" | "stale";

const TABS: { id: Tab; label: string }[] = [
  { id: "activity", label: "Activity" },
  { id: "narrative", label: "Narrative" },
  { id: "stale", label: "Stale issues" },
];

const now = new Date();
const thirtyDaysAgo = new Date(now.getTime() - 30 * 24 * 60 * 60 * 1000);

export default function App() {
  const [timeframe, setTimeframe] = useState<RepoTimeframe>({
    owner: "nats-io",
    repo: "nats.go",
    start: toDateInputValue(thirtyDaysAgo),
    end: toDateInputValue(now),
  });
  const [tab, setTab] = useState<Tab>("activity");

  return (
    <div className="app">
      <header className="app-header">
        <h1>Issue Activity</h1>
        <p>A small demo client for the GitHub issue-activity API.</p>
      </header>

      <TimeframeForm value={timeframe} onChange={setTimeframe} />

      <nav className="tabs">
        {TABS.map((t) => (
          <button
            key={t.id}
            className={`tab ${tab === t.id ? "tab-active" : ""}`}
            onClick={() => setTab(t.id)}
          >
            {t.label}
          </button>
        ))}
      </nav>

      {tab === "activity" && <ActivityView {...timeframe} />}
      {tab === "narrative" && <NarrativeView {...timeframe} />}
      {tab === "stale" && <StaleView {...timeframe} />}
    </div>
  );
}
