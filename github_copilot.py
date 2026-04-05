"""
GitHub Copilot Integration — Creates GitHub issues and assigns them to the
Copilot coding agent, which autonomously creates pull requests.

Also provides helpers to read repo context and track PR status.
"""

import os
import logging
from typing import Any, Optional

import requests

logger = logging.getLogger(__name__)

# --- Configuration ---
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")
GITHUB_REPO = os.environ.get("GITHUB_REPO", "")  # format: "owner/repo"

GITHUB_API_BASE = "https://api.github.com"


def _headers() -> dict[str, str]:
    """Return GitHub API headers with authentication."""
    return {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }


def _repo_parts() -> tuple[str, str]:
    """Split GITHUB_REPO into owner and repo name."""
    if "/" not in GITHUB_REPO:
        raise RuntimeError(
            "GITHUB_REPO must be in 'owner/repo' format "
            f"(got: {GITHUB_REPO!r})"
        )
    owner, repo = GITHUB_REPO.split("/", 1)
    return owner, repo


def get_repo_file_list() -> list[str]:
    """
    Get the list of files in the repository's default branch via the GitHub API.

    Returns:
        List of file paths in the repo.
    """
    if not GITHUB_TOKEN or not GITHUB_REPO:
        raise RuntimeError("GITHUB_TOKEN and GITHUB_REPO must be set")

    owner, repo = _repo_parts()
    url = f"{GITHUB_API_BASE}/repos/{owner}/{repo}/git/trees/HEAD?recursive=1"

    resp = requests.get(url, headers=_headers(), timeout=15)
    resp.raise_for_status()

    tree = resp.json().get("tree", [])
    return [item["path"] for item in tree if item["type"] == "blob"]


def get_file_contents(file_path: str) -> Optional[str]:
    """
    Read a single file's contents from the repo via the GitHub API.

    Returns:
        The file content as a string, or None if not found.
    """
    if not GITHUB_TOKEN or not GITHUB_REPO:
        return None

    owner, repo = _repo_parts()
    url = f"{GITHUB_API_BASE}/repos/{owner}/{repo}/contents/{file_path}"

    resp = requests.get(url, headers=_headers(), timeout=15)
    if resp.status_code != 200:
        return None

    data = resp.json()
    if data.get("encoding") == "base64":
        import base64
        return base64.b64decode(data["content"]).decode("utf-8", errors="replace")
    return data.get("content")


def create_issue_and_assign_copilot(title: str, body: str) -> dict[str, Any]:
    """
    Create a GitHub issue and assign it to the Copilot coding agent.

    The Copilot agent is triggered by assigning the issue to 'copilot'.
    Once assigned, Copilot will autonomously analyze the issue, implement
    the changes, and open a pull request.

    Returns:
        dict with 'issue_number', 'issue_url', and 'html_url' keys.

    Raises:
        RuntimeError: If the API calls fail.
    """
    if not GITHUB_TOKEN or not GITHUB_REPO:
        raise RuntimeError("GITHUB_TOKEN and GITHUB_REPO must be set")

    owner, repo = _repo_parts()

    # Step 1: Create the issue
    create_url = f"{GITHUB_API_BASE}/repos/{owner}/{repo}/issues"
    issue_payload = {
        "title": title,
        "body": body,
        "labels": ["copilot"],
    }

    logger.info("[GitHub] Creating issue: %s", title[:80])
    resp = requests.post(create_url, json=issue_payload, headers=_headers(), timeout=15)
    resp.raise_for_status()
    issue_data = resp.json()

    issue_number = issue_data["number"]
    issue_url = issue_data["url"]
    html_url = issue_data["html_url"]

    # Step 2: Assign the issue to Copilot
    assign_url = f"{GITHUB_API_BASE}/repos/{owner}/{repo}/issues/{issue_number}"
    assign_payload = {"assignees": ["copilot"]}

    logger.info("[GitHub] Assigning issue #%d to Copilot", issue_number)
    assign_resp = requests.patch(
        assign_url, json=assign_payload, headers=_headers(), timeout=15
    )

    if assign_resp.status_code not in (200, 201):
        logger.warning(
            "[GitHub] Could not assign to 'copilot' (status %d). "
            "The issue was created but Copilot may need to be assigned manually.",
            assign_resp.status_code,
        )

    return {
        "issue_number": issue_number,
        "issue_url": issue_url,
        "html_url": html_url,
    }


def get_issue_linked_prs(issue_number: int) -> list[dict[str, Any]]:
    """
    Check if there are any pull requests linked to a GitHub issue.

    Uses the timeline events API to find PRs that reference the issue.

    Returns:
        List of PR dicts with 'number', 'title', 'html_url', 'state' keys.
    """
    if not GITHUB_TOKEN or not GITHUB_REPO:
        return []

    owner, repo = _repo_parts()
    url = f"{GITHUB_API_BASE}/repos/{owner}/{repo}/issues/{issue_number}/timeline"
    headers = {**_headers(), "Accept": "application/vnd.github.mockingbird-preview+json"}

    resp = requests.get(url, headers=headers, timeout=15)
    if resp.status_code != 200:
        return []

    prs: list[dict[str, Any]] = []
    for event in resp.json():
        if event.get("event") == "cross-referenced":
            source = event.get("source", {}).get("issue", {})
            if source.get("pull_request"):
                prs.append({
                    "number": source["number"],
                    "title": source.get("title", ""),
                    "html_url": source.get("html_url", ""),
                    "state": source.get("state", ""),
                })
    return prs
