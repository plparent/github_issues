import os
from datetime import datetime, timezone

from sqlalchemy import create_engine, select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from database.models import issue_timeline_events, issues, sync_state


def get_engine(url=None):
    """Create an engine from `url`, or from the DATABASE_URL environment variable."""
    url = url or os.environ["DATABASE_URL"]
    # SQLAlchemy doesn't accept the legacy "postgres://" scheme.
    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://"):]
    return create_engine(url)


def _parse_ts(value):
    """Turn a GitHub ISO 8601 string (e.g. 2024-03-15T12:34:56Z) into a datetime."""
    if value is None:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


# Every function below takes a SQLAlchemy `conn` (a Connection, not an Engine)
# and does not open or commit its own transaction. That's left to the caller,
# via `with engine.begin() as conn:` — so several of these can be composed
# into one atomic unit: either all of it commits, or none of it does.


def store_issues(conn, owner, repo, issue_list):
    """
    Insert or update issues (the list of dicts returned by fetch_issues) using
    `conn`. Issues already stored are updated in place, so re-running is safe.
    """
    if not issue_list:
        return
    rows = [
        {
            "owner": owner,
            "repo": repo,
            "issue_number": i["issue_number"],
            "status": i["status"],
            "created_at": _parse_ts(i["created_at"]),
            "closed_at": _parse_ts(i["closed_at"]),
        }
        for i in issue_list
    ]
    stmt = pg_insert(issues)
    stmt = stmt.on_conflict_do_update(
        index_elements=["owner", "repo", "issue_number"],
        set_={col: stmt.excluded[col] for col in ("status", "created_at", "closed_at")},
    )
    conn.execute(stmt, rows)


def store_timeline(conn, owner, repo, issue_number, events):
    """
    Insert or update an issue's timeline events (the list of dicts returned by
    fetch_issue_timeline) using `conn`. Events already stored are updated in
    place, keyed on (owner, repo, issue_number, event_id), so re-running is
    safe.

    The issue must already be in the issues table.
    """
    if not events:
        return
    rows = [
        {
            "owner": owner,
            "repo": repo,
            "issue_number": issue_number,
            "event_id": str(e["event_id"]),
            "created_at": _parse_ts(e["created_at"]),
            "event_type": e["event_type"],
            "actor": e["actor"],
        }
        for e in events
    ]
    stmt = pg_insert(issue_timeline_events)
    stmt = stmt.on_conflict_do_update(
        index_elements=["owner", "repo", "issue_number", "event_id"],
        set_={col: stmt.excluded[col] for col in ("created_at", "event_type", "actor")},
    )
    conn.execute(stmt, rows)


def get_last_updated(conn, owner, repo):
    """Return the repo's last update time as a timezone-aware datetime, or None."""
    stmt = select(sync_state.c.last_updated).where(
        sync_state.c.owner == owner, sync_state.c.repo == repo
    )
    return conn.execute(stmt).scalar_one_or_none()


def set_last_updated(conn, owner, repo, updated_at=None):
    """
    Record when the repo was last updated (defaults to now, in UTC), using `conn`.

    Capture the time *before* you start fetching and pass it in once the data is
    stored. That way, issues changed while the fetch was running are picked up
    on the next run instead of being missed.
    """
    updated_at = updated_at or datetime.now(timezone.utc)
    stmt = pg_insert(sync_state).values(
        owner=owner, repo=repo, last_updated=updated_at
    )
    stmt = stmt.on_conflict_do_update(
        index_elements=["owner", "repo"],
        set_={"last_updated": stmt.excluded.last_updated},
    )
    conn.execute(stmt)

