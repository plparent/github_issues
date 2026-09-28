from datetime import datetime, timezone

import requests


def _to_iso_utc(value):
    """Convert a date, datetime, or ISO 8601 string to GitHub's UTC timestamp format."""
    if isinstance(value, str):
        value = datetime.fromisoformat(value.replace("Z", "+00:00"))
    elif not isinstance(value, datetime):  # a plain date
        value = datetime(value.year, value.month, value.day)
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def fetch_issues(owner, repo, state="all", since=None, token=None):
    """
    Fetch issues from a public GitHub repository.

    Args:
        owner: Repository owner (user or organization).
        repo:  Repository name.
        state: "open", "closed", or "all" (default).
        since: Optional cutoff passed to GitHub's `since` parameter. Only issues
               last updated at or after this time are returned (this is based on
               the update time, not the creation time). Accepts a date, a
               datetime, or an ISO string like "2024-01-01". Naive values are
               treated as UTC.
        token: Optional GitHub personal access token (raises the rate limit
               from 60 to 5,000 requests/hour).

    Returns:
        A list of dicts with keys: issue_number, status, created_at, closed_at
        (closed_at is None for issues that are still open).
    """
    url = f"https://api.github.com/repos/{owner}/{repo}/issues"
    headers = {"Accept": "application/vnd.github+json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    params = {"state": state, "per_page": 100}
    if since is not None:
        params["since"] = _to_iso_utc(since)

    issues = []

    while url:
        response = requests.get(url, headers=headers, params=params, timeout=30)
        response.raise_for_status()

        for item in response.json():
            # The issues endpoint also returns pull requests; skip them.
            if "pull_request" in item:
                continue
            issues.append({
                "issue_number": item["number"],
                "status": item["state"],
                "created_at": item["created_at"],
                "closed_at": item["closed_at"],
            })

        # Follow pagination; the "next" URL already includes the query params.
        url = response.links.get("next", {}).get("url")
        params = None

    return issues


def fetch_issue_timeline(owner, repo, issue_number, token=None):
    """
    Fetch the timeline of a single issue in a public GitHub repository.

    Args:
        owner:        Repository owner (user or organization).
        repo:         Repository name.
        issue_number: The issue's number (e.g. 1234).
        token:        Optional GitHub personal access token.

    Returns:
        A list of dicts with keys: event_id, created_at, event_type, actor
        (the actor's login, or None if GitHub doesn't report one). event_id
        and event_type are always present. In chronological order.
    """
    url = f"https://api.github.com/repos/{owner}/{repo}/issues/{issue_number}/timeline"
    headers = {"Accept": "application/vnd.github+json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    params = {"per_page": 100}
    events = []

    while url:
        response = requests.get(url, headers=headers, params=params, timeout=30)
        response.raise_for_status()

        for item in response.json():
            # Not every event type has the same shape, so fall back gracefully:
            # commits have a sha instead of an id, reviews use submitted_at,
            # and some events name the person under "user" or "author".
            # event_id and event_type are always present, on every event type.
            person = item.get("actor") or item.get("user") or item.get("author") or {}
            events.append({
                "event_id": item["id"] if "id" in item else item["sha"],
                "created_at": (
                    item.get("created_at")
                    or item.get("submitted_at")
                    or (item.get("committer") or {}).get("date")
                ),
                "event_type": item["event"],
                "actor": person.get("login") or person.get("name"),
            })

        url = response.links.get("next", {}).get("url")
        params = None

    return events

