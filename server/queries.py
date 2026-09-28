"""
Database query functions for the issue-activity API.

Pure SQLAlchemy Core, async: every function here takes an open
AsyncConnection and returns plain data (lists of row mappings / dicts). No
FastAPI or HTTP concerns belong in this file - that's api.py's job.
"""
from datetime import timedelta

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncConnection

from database.models import issue_timeline_events, issues


async def get_issue_activity(conn: AsyncConnection, owner: str, repo: str, start, end):
    """
    Return the repo's issues that had at least one timeline event between
    `start` and `end` (both inclusive), each with its total event count in
    that window, ordered by event count descending.

    Issues with no events in the timeframe are omitted: the inner join below
    only matches issues that have at least one qualifying event row, so
    nothing further (e.g. a HAVING clause) is needed to exclude them.
    """
    i, t = issues, issue_timeline_events
    stmt = (
        select(
            i.c.issue_number,
            i.c.status,
            i.c.created_at,
            i.c.closed_at,
            func.count(t.c.id).label("event_count"),
        )
        .select_from(
            i.join(
                t,
                and_(
                    i.c.owner == t.c.owner,
                    i.c.repo == t.c.repo,
                    i.c.issue_number == t.c.issue_number,
                ),
            )
        )
        .where(
            i.c.owner == owner,
            i.c.repo == repo,
            i.c.created_at >= start,
            i.c.created_at <= end,
        )
        .group_by(i.c.issue_number, i.c.status, i.c.created_at, i.c.closed_at)
        .order_by(func.count(t.c.id).desc())
    )
    result = await conn.execute(stmt)
    return result.mappings().all()


async def get_issue_activity_detail(conn: AsyncConnection, owner: str, repo: str, start, end):
    """
    Like get_issue_activity, but each issue also carries a breakdown of event
    counts by event_type (e.g. how many were comments vs. commits vs. closes)
    and a count of distinct actors who triggered an event. Same ordering and
    same no-events exclusion, meant for feeding a richer summary to an LLM.

    Returns a list of dicts, each with: issue_number, status, created_at,
    closed_at, event_count, distinct_actors, last_event_at (the most recent
    event's timestamp, useful for judging staleness), event_type_counts (a
    dict of event_type -> count).
    """
    i, t = issues, issue_timeline_events
    join_cond = and_(
        i.c.owner == t.c.owner,
        i.c.repo == t.c.repo,
        i.c.issue_number == t.c.issue_number,
    )
    where_cond = (
        i.c.owner == owner,
        i.c.repo == repo,
        i.c.created_at >= start,
        i.c.created_at <= end,
    )

    totals_stmt = (
        select(
            i.c.issue_number,
            i.c.status,
            i.c.created_at,
            i.c.closed_at,
            func.count(t.c.id).label("event_count"),
            func.count(func.distinct(t.c.actor)).label("distinct_actors"),
            func.max(t.c.created_at).label("last_event_at"),
        )
        .select_from(i.join(t, join_cond))
        .where(*where_cond)
        .group_by(i.c.issue_number, i.c.status, i.c.created_at, i.c.closed_at)
        .order_by(func.count(t.c.id).desc())
    )
    totals = (await conn.execute(totals_stmt)).mappings().all()
    if not totals:
        return []

    breakdown_stmt = (
        select(
            i.c.issue_number,
            t.c.event_type,
            func.count(t.c.id).label("count"),
        )
        .select_from(i.join(t, join_cond))
        .where(*where_cond)
        .group_by(i.c.issue_number, t.c.event_type)
    )
    breakdown_rows = (await conn.execute(breakdown_stmt)).mappings().all()

    counts_by_issue = {}
    for row in breakdown_rows:
        counts_by_issue.setdefault(row["issue_number"], {})[row["event_type"]] = row["count"]

    results = []
    for row in totals:
        d = dict(row)
        d["event_type_counts"] = counts_by_issue.get(row["issue_number"], {})
        results.append(d)
    return results


async def get_stale_issues(
    conn: AsyncConnection, owner: str, repo: str, start, end, stale_days: int, now
):
    """
    Find open issues, created between `start` and `end` (both inclusive),
    that have had no timeline event for at least `stale_days` days as of
    `now`. An issue with no timeline events at all is judged against its own
    created_at instead, since that's the only activity timestamp it has.

    Ordered by last activity ascending, so the most stale issues (the
    longest gap since anything happened) come first.

    Returns a list of dicts, each with: issue_number, status, created_at,
    closed_at, last_event_at (None if the issue has no timeline events),
    last_activity_at (last_event_at, or created_at when there are no events -
    this is what's actually compared against the staleness cutoff).
    """
    i, t = issues, issue_timeline_events
    cutoff = now - timedelta(days=stale_days)

    # Aggregated separately (rather than joined directly against `issues`)
    # because this must consider *every* event ever recorded for the issue,
    # not just ones in [start, end] - start/end here only bounds when the
    # issue itself was created.
    last_event_subq = (
        select(
            t.c.owner,
            t.c.repo,
            t.c.issue_number,
            func.max(t.c.created_at).label("last_event_at"),
        )
        .group_by(t.c.owner, t.c.repo, t.c.issue_number)
        .subquery()
    )
    last_activity_at = func.coalesce(
        last_event_subq.c.last_event_at, i.c.created_at
    ).label("last_activity_at")

    stmt = (
        select(
            i.c.issue_number,
            i.c.status,
            i.c.created_at,
            i.c.closed_at,
            last_event_subq.c.last_event_at,
            last_activity_at,
        )
        .select_from(
            i.outerjoin(
                last_event_subq,
                and_(
                    i.c.owner == last_event_subq.c.owner,
                    i.c.repo == last_event_subq.c.repo,
                    i.c.issue_number == last_event_subq.c.issue_number,
                ),
            )
        )
        .where(
            i.c.owner == owner,
            i.c.repo == repo,
            i.c.status == "open",
            i.c.created_at >= start,
            i.c.created_at <= end,
            last_activity_at <= cutoff,
        )
        .order_by(last_activity_at.asc())
    )
    result = await conn.execute(stmt)
    return result.mappings().all()
