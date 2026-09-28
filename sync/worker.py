"""
Sync a public GitHub repo's issues and their timelines into Postgres.

Fetches everything changed since the last successful run (via sync_state),
stores it, then advances the watermark. Run repeatedly (e.g. from cron) to
keep the database up to date incrementally.
"""
import logging
import sys
import os
import time
from datetime import datetime, timezone

from queries import get_engine, get_last_updated, set_last_updated, store_issues, store_timeline
from github_pull import fetch_issue_timeline, fetch_issues

logger = logging.getLogger("github_sync")

BATCH_SIZE = int(os.environ.get("BATCH_SIZE", "50"))
UPDATE_TIME = int(os.environ.get("UPDATE_TIME", "600"))


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


def _chunk(items, size):
    for i in range(0, len(items), size):
        yield items[i:i + size]


def sync_repo(engine, owner, repo, token=None, batch_size=BATCH_SIZE):
    """
    Pull issues (and their timelines) changed since the last sync, and store
    them. Returns the number of issues synced.

    Issues are fetched and stored in batches of `batch_size`, each batch's
    issues and timelines committed together in one transaction: a batch
    either fully lands or, if a write fails partway through, rolls back to
    where the previous batch left off. A batch's timelines aren't held in
    memory once its transaction commits, so a very large first-time backfill
    doesn't need to hold the whole repo's data in memory at once.

    The watermark, however, is only advanced once every batch in this run has
    committed. If a batch fails, all the batches before it stay committed,
    but the watermark isn't moved, so the next run starts from the same point
    and re-fetches the whole run rather than silently continuing from the
    middle. That re-fetch is safe (storing is an upsert, so re-storing
    already-committed issues and timelines just overwrites them with the same
    data) - it just costs extra API calls for a large repo.
    """
    logger.info("Starting sync for %s/%s", owner, repo)

    # Captured before fetching starts, so anything changed mid-run is picked
    # up on the next sync rather than missed.
    started_at = datetime.now(timezone.utc)

    with engine.connect() as conn:
        since = get_last_updated(conn, owner, repo)
    if since:
        logger.info("Last synced at %s; fetching changes since then", since)
    else:
        logger.info("No previous sync found; fetching all issues")

    try:
        fetched = fetch_issues(owner, repo, since=since, token=token)
    except Exception:
        logger.exception("Failed to fetch issue list for %s/%s", owner, repo)
        raise
    total = len(fetched)
    logger.info("Fetched %d changed issue(s)", total)

    batches = list(_chunk(fetched, batch_size))
    for batch_num, batch in enumerate(batches, start=1):
        timelines = {}
        for issue in batch:
            number = issue["issue_number"]
            try:
                timelines[number] = fetch_issue_timeline(owner, repo, number, token=token)
            except Exception:
                logger.exception("Failed to fetch timeline for %s/%s#%d", owner, repo, number)
                raise
            logger.debug("Issue #%d: fetched %d timeline event(s)", number, len(timelines[number]))

        try:
            with engine.begin() as conn:
                store_issues(conn, owner, repo, batch)
                for issue in batch:
                    number = issue["issue_number"]
                    store_timeline(conn, owner, repo, number, timelines[number])
        except Exception:
            logger.exception(
                "Database write failed on batch %d/%d for %s/%s; that batch rolled back, "
                "%d earlier batch(es) stay committed, watermark not advanced",
                batch_num, len(batches), owner, repo, batch_num - 1,
            )
            raise
        logger.info(
            "Committed batch %d/%d for %s/%s (%d issue(s))",
            batch_num, len(batches), owner, repo, len(batch),
        )

    try:
        with engine.begin() as conn:
            set_last_updated(conn, owner, repo, started_at)
    except Exception:
        logger.exception(
            "Failed to advance watermark for %s/%s after a successful sync; "
            "next run will re-fetch and re-store everything from this run",
            owner, repo,
        )
        raise

    logger.info("Sync complete for %s/%s: %d issue(s) updated", owner, repo, total)
    return total


def main():
    owner = os.getenv("REPO_OWNER")
    repo = os.getenv("REPO")
    if owner is None or repo is None:
        logger.error("Sync failed for %s/%s", owner, repo)
        sys.exit(1)
    token = os.getenv("GITHUB_TOKEN")

    engine = get_engine()
    while True:
        try:
            sync_repo(engine, owner, repo, token=token)
        except Exception:
            logger.error("Sync failed for %s/%s", owner, repo)
            sys.exit(1)
        time.sleep(UPDATE_TIME)


if __name__ == "__main__":
    main()
