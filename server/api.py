"""
FastAPI service exposing issue activity from the synced GitHub database.

Swagger UI (interactive docs) is served automatically at /docs, and the raw
OpenAPI schema at /openapi.json.
"""
import json
import logging
import os
import time
from datetime import datetime, timezone
from typing import List, Optional

import httpx
from fastapi import Depends, FastAPI, HTTPException, Path, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncConnection, create_async_engine

from queries import get_issue_activity, get_issue_activity_detail, get_stale_issues

logger = logging.getLogger("github_api")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://ollama:11434")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "granite4.2:3b")
OLLAMA_TIMEOUT = float(os.environ.get("OLLAMA_TIMEOUT", "120"))
MAX_ISSUES_IN_PROMPT = int(os.environ.get("MAX_ISSUES_IN_PROMPT", "10"))
# Origins allowed to call this API from a browser (e.g. the demo frontend's
# dev server). Comma-separated; defaults to Vite's default dev port.
CORS_ALLOWED_ORIGINS = [
    origin.strip()
    for origin in os.environ.get("CORS_ALLOWED_ORIGINS", "http://localhost:5173").split(",")
    if origin.strip()
]

app = FastAPI(
    title="GitHub Issue Activity API",
    description="Ranks a repo's issues by how many timeline events fell in a given timeframe.",
    version="1.0.0",
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ALLOWED_ORIGINS,
    allow_methods=["GET"],
    allow_headers=["*"],
)


def _async_database_url():
    """
    Build an async-driver database URL from DATABASE_URL, the same
    environment variable the sync scripts (sync.py, github_db.py, Alembic)
    use. Those use psycopg2; this rewrites the URL to use asyncpg instead, so
    one env var serves both without the user having to set two.
    """
    url = os.environ["DATABASE_URL"]
    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://"):]
    if url.startswith("postgresql://"):
        url = "postgresql+asyncpg://" + url[len("postgresql://"):]
    return url


@app.on_event("startup")
async def startup():
    # One Engine (and its connection pool) for the app's lifetime; each
    # request checks out its own connection via the get_conn dependency.
    app.state.engine = create_async_engine(_async_database_url())
    logger.info("Started up; database engine ready")


@app.on_event("shutdown")
async def shutdown():
    await app.state.engine.dispose()
    logger.info("Shut down; database engine disposed")


async def get_conn(request: Request):
    """Per-request database connection, closed automatically after the request."""
    async with request.app.state.engine.connect() as conn:
        yield conn


@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    elapsed_ms = (time.perf_counter() - start) * 1000
    logger.info(
        "%s %s -> %d (%.1f ms)",
        request.method, request.url.path, response.status_code, elapsed_ms,
    )
    return response


class IssueEventCount(BaseModel):
    issue_number: int
    status: str
    created_at: datetime
    closed_at: Optional[datetime] = None
    event_count: int


class NarrativeResponse(BaseModel):
    narrative: str
    confidence: Optional[float] = Field(
        None, ge=0, le=1, description="Model's confidence that the narrative reflects the data, 0-1"
    )
    issues_considered: int
    total_events: int


class StaleIssue(BaseModel):
    issue_number: int
    status: str
    created_at: datetime
    closed_at: Optional[datetime] = None
    last_event_at: Optional[datetime] = Field(
        None, description="Most recent timeline event ever recorded for this issue, if any"
    )
    days_since_last_event: int = Field(
        description="Days since the last event (or since creation, if the issue has no events)"
    )


@app.get(
    "/{owner}/{repo}/issues/activity",
    response_model=List[IssueEventCount],
    summary="Rank issues by timeline event count within a timeframe",
)
async def get_issues_by_activity(
    owner: str = Path(..., description="Repository owner, e.g. 'nats-io'"),
    repo: str = Path(..., description="Repository name, e.g. 'nats.go'"),
    start: datetime = Query(..., description="Start of the timeframe (inclusive), ISO 8601"),
    end: datetime = Query(..., description="End of the timeframe (inclusive), ISO 8601"),
    conn: AsyncConnection = Depends(get_conn),
):
    """
    Return the repo's issues created between `start` and `end` (both inclusive), 
    ordered by event count, descending.
    """
    if start > end:
        logger.warning("Rejected request: start (%s) is after end (%s)", start, end)
        raise HTTPException(status_code=400, detail="`start` must not be after `end`")

    logger.info("Fetching issue activity for %s/%s between %s and %s", owner, repo, start, end)
    try:
        rows = await get_issue_activity(conn, owner, repo, start, end)
    except Exception:
        logger.exception("Database query failed for %s/%s", owner, repo)
        raise HTTPException(status_code=500, detail="Database query failed")

    logger.info("Found %d issue(s) with activity for %s/%s", len(rows), owner, repo)
    return [IssueEventCount(**row) for row in rows]


@app.get(
    "/{owner}/{repo}/issues/stale",
    response_model=List[StaleIssue],
    summary="Find open issues, created in a timeframe, with no recent activity",
)
async def get_stale_issues_endpoint(
    owner: str = Path(..., description="Repository owner, e.g. 'nats-io'"),
    repo: str = Path(..., description="Repository name, e.g. 'nats.go'"),
    start: datetime = Query(..., description="Issues created at or after this time (inclusive), ISO 8601"),
    end: datetime = Query(..., description="Issues created at or before this time (inclusive), ISO 8601"),
    stale_days: int = Query(
        ..., gt=0, description="Days without any timeline event for an open issue to count as stale"
    ),
    conn: AsyncConnection = Depends(get_conn),
):
    """
    Return the repo's still-open issues that were created between `start`
    and `end` (both inclusive) and have had no timeline event for at least
    `stale_days` days, ordered with the most stale (longest gap since any
    activity) first. An issue with no timeline events at all is judged
    against its own creation date, since that's its only timestamp.
    """
    if start > end:
        logger.warning("Rejected request: start (%s) is after end (%s)", start, end)
        raise HTTPException(status_code=400, detail="`start` must not be after `end`")

    now = datetime.now(timezone.utc)
    logger.info(
        "Fetching stale issues for %s/%s created between %s and %s, stale_days=%d",
        owner, repo, start, end, stale_days,
    )
    try:
        rows = await get_stale_issues(conn, owner, repo, start, end, stale_days, now)
    except Exception:
        logger.exception("Database query failed for %s/%s", owner, repo)
        raise HTTPException(status_code=500, detail="Database query failed")

    results = [
        StaleIssue(
            issue_number=row["issue_number"],
            status=row["status"],
            created_at=row["created_at"],
            closed_at=row["closed_at"],
            last_event_at=row["last_event_at"],
            days_since_last_event=(now - row["last_activity_at"]).days,
        )
        for row in rows
    ]
    logger.info("Found %d stale issue(s) for %s/%s", len(results), owner, repo)
    return results


def _build_narrative_prompt(owner, repo, start, end, now, details):
    shown = details[:MAX_ISSUES_IN_PROMPT]
    lines = [
        f"You are analyzing GitHub issue activity for {owner}/{repo} "
        f"between {start.isoformat()} and {end.isoformat()}.",
        f"Today's date is {now.isoformat()}.",
        f"{len(details)} issue(s) had at least one event in this window "
        f"(showing the top {len(shown)} by event count).",
        "",
        "Data (issue_number, status, created_at, closed_at, total_events, "
        "distinct_actors, last_event_at, event_type_counts):",
    ]
    for d in shown:
        lines.append(
            f"- #{d['issue_number']} | status={d['status']} "
            f"| created={d['created_at'].isoformat()} "
            f"| closed={d['closed_at'].isoformat() if d['closed_at'] else 'open'} "
            f"| total_events={d['event_count']} | distinct_actors={d['distinct_actors']} "
            f"| last_event_at={d['last_event_at'].isoformat() if d['last_event_at'] else 'unknown'} "
            f"| event_types={d['event_type_counts']}"
        )
    lines += [
        "",
        "Write a short 2-4 sentence narrative describing what's interesting or unusual: "
        "which issue(s) stand out, whether the activity looks like popularity (many "
        "comments/reactions from many distinct actors), active development (commits, "
        "reviews), or churn (repeated labeling/reopening); whether the issue is now "
        "closed; and, for any issue still open, whether it looks stale (its last_event_at "
        "is a long time before today's date) or still active. Only cite numbers that "
        "appear in the data above.",
        "",
        "Respond with ONLY a JSON object and nothing else, matching exactly this schema:",
        '{"narrative": "<string>", "confidence": <number 0-1 or null, your confidence '
        'that this narrative accurately reflects the data above>}',
    ]
    return "\n".join(lines)


@app.get(
    "/{owner}/{repo}/issues/narrative",
    response_model=NarrativeResponse,
    summary="LLM-generated narrative over issue activity within a timeframe",
)
async def get_issues_narrative(
    owner: str = Path(..., description="Repository owner, e.g. 'nats-io'"),
    repo: str = Path(..., description="Repository name, e.g. 'nats.go'"),
    start: datetime = Query(..., description="Start of the timeframe (inclusive), ISO 8601"),
    end: datetime = Query(..., description="End of the timeframe (inclusive), ISO 8601"),
    conn: AsyncConnection = Depends(get_conn),
):
    """
    Same inputs as /{owner}/{repo}/issues/activity, but instead of returning
    the raw ranked list, sends a summary of the numbers (including a
    breakdown of event types, distinct actors, and each issue's most recent
    event timestamp) to a local Ollama model and returns its short narrative
    with a confidence score.
    """
    if start > end:
        logger.warning("Rejected request: start (%s) is after end (%s)", start, end)
        raise HTTPException(status_code=400, detail="`start` must not be after `end`")

    logger.info("Building narrative for %s/%s between %s and %s", owner, repo, start, end)
    try:
        details = await get_issue_activity_detail(conn, owner, repo, start, end)
    except Exception:
        logger.exception("Database query failed for %s/%s", owner, repo)
        raise HTTPException(status_code=500, detail="Database query failed")


    if not details:
        logger.info("No activity for %s/%s in range; skipping the LLM call", owner, repo)
        return NarrativeResponse(
            narrative="No issues had any timeline events in this timeframe.",
            issues_considered=0,
            total_events=0,
        )

    prompt = _build_narrative_prompt(owner, repo, start, end, datetime.now(timezone.utc), details)
    logger.debug("Ollama prompt is %d chars", len(prompt))

    try:
        async with httpx.AsyncClient(timeout=OLLAMA_TIMEOUT) as client:
            response = await client.post(
                f"{OLLAMA_URL}/api/generate",
                json={
                    "model": OLLAMA_MODEL,
                    "prompt": prompt,
                    "stream": False,
                    "format": "json",
                },
            )
            response.raise_for_status()
    except httpx.HTTPError:
        logger.exception("Failed to reach Ollama at %s", OLLAMA_URL)
        raise HTTPException(
            status_code=502, detail=f"Could not reach the Ollama server at {OLLAMA_URL}"
        )

    raw_text = response.json().get("response", "")
    try:
        parsed = json.loads(raw_text)
        narrative = parsed["narrative"]
        confidence = parsed.get("confidence")
    except (json.JSONDecodeError, KeyError, TypeError):
        logger.warning(
            "Ollama's response wasn't the expected JSON shape for %s/%s; "
            "returning the raw text as the narrative",
            owner, repo,
        )
        narrative = raw_text.strip() or "The model returned an empty response."
        confidence = None

    issues_considered=len(details) if len(details) < MAX_ISSUES_IN_PROMPT else MAX_ISSUES_IN_PROMPT
    total_events = sum(d["event_count"] for d in details[:issues_considered])
    logger.info(
        "Narrative generated for %s/%s (%d issue(s), %d event(s))",
        owner, repo, issues_considered, total_events,
    )
    return NarrativeResponse(
        narrative=narrative,
        confidence=confidence,
        issues_considered=issues_considered,
        total_events=total_events,
    )

