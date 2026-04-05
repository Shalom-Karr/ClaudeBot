"""
GroupMe AI Bot — Callback Server with Copilot Pipeline

Listens on port 8000 for GroupMe webhook callbacks. Supports two modes:
1. **Chat mode** — Regular messages get Gemini AI responses
2. **Task mode** — Messages starting with "task:" trigger the pipeline:
   GroupMe → Gemini (prompt architect) → GitHub Copilot (coding agent) → PR

Also accepts GitHub webhook events at /github-webhook to notify GroupMe
when Copilot creates a pull request.

Setup:
1. pip install -r requirements.txt
2. Set environment variables (see README.md)
3. Run: python groupme_bot.py
   Or use: ./start.sh (launches bot + Cloudflare Tunnel)
"""

import os
import logging
import threading
from typing import Optional

import requests
from flask import Flask, request, jsonify

from task_manager import TaskManager, TaskStatus
from gemini_architect import get_chat_response, craft_issue_prompt
from github_copilot import (
    get_repo_file_list,
    get_file_contents,
    create_issue_and_assign_copilot,
    get_issue_linked_prs,
)

# --- Logging ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# --- Configuration ---
GROUPME_BOT_ID = os.environ.get("GROUPME_BOT_ID", "your_groupme_bot_id_here")
GROUPME_POST_URL = "https://api.groupme.com/v3/bots/post"
BOT_NAME = os.environ.get("BOT_NAME", "AI Assistant")

# Initialize task manager
task_mgr = TaskManager()

# Conversation history per group (keyed by group_id)
conversation_history: dict[str, list] = {}
MAX_HISTORY = 20


def send_groupme_message(text: str, bot_id: str = GROUPME_BOT_ID) -> None:
    """Send a message to GroupMe via the Bot API."""
    # GroupMe has a 1000 char limit per message; split if needed
    chunks = [text[i:i + 990] for i in range(0, len(text), 990)]
    for chunk in chunks:
        payload = {"bot_id": bot_id, "text": chunk}
        try:
            resp = requests.post(GROUPME_POST_URL, json=payload, timeout=10)
            resp.raise_for_status()
            logger.info("[GroupMe] Sent message: %s...", chunk[:80])
        except requests.RequestException as e:
            logger.error("[GroupMe] Error sending message: %s", e)


def get_gemini_response(group_id: str, user_name: str, user_message: str) -> str:
    """Get a response from Gemini, maintaining per-group conversation history."""
    if group_id not in conversation_history:
        conversation_history[group_id] = []

    history = conversation_history[group_id]

    history.append({
        "role": "user",
        "content": f"{user_name}: {user_message}"
    })

    if len(history) > MAX_HISTORY:
        conversation_history[group_id] = history[-MAX_HISTORY:]
        history = conversation_history[group_id]

    reply = get_chat_response(BOT_NAME, history)

    history.append({
        "role": "model",
        "content": reply
    })

    return reply


# ---------------------------------------------------------------------------
# Task Pipeline: GroupMe → Gemini → GitHub Copilot → PR
# ---------------------------------------------------------------------------

def _run_task_pipeline(task_id: str, description: str, group_id: str) -> None:
    """
    Execute the full task pipeline in a background thread.

    1. Ask Gemini to craft a detailed GitHub issue prompt
    2. Create a GitHub issue with that prompt
    3. Assign the issue to Copilot
    4. Notify GroupMe with the result
    """
    task = task_mgr.get_task(task_id)
    if not task:
        return

    try:
        # Step 1: Get repo context from GitHub
        send_groupme_message(f"🧠 Gemini is analyzing your task: \"{description}\"...")
        task_mgr.update_status(task_id, TaskStatus.PROMPTING)

        repo_files = get_repo_file_list()

        # Read key files for context
        key_files = ["groupme_bot.py", "ideas.md", "README.md"]
        file_contents: dict[str, str] = {}
        for f in key_files:
            if f in repo_files:
                content = get_file_contents(f)
                if content:
                    file_contents[f] = content

        # Step 2: Ask Gemini to craft the issue prompt
        result = craft_issue_prompt(description, repo_files, file_contents)
        title = result["title"]
        body = result["body"]
        task_mgr.update_status(task_id, TaskStatus.PROMPTING, gemini_prompt=body)

        # Step 3: Create GitHub issue and assign to Copilot
        send_groupme_message(f"📝 Creating GitHub issue: \"{title}\"...")
        issue = create_issue_and_assign_copilot(title, body)
        task_mgr.update_status(
            task_id,
            TaskStatus.COPILOT_ASSIGNED,
            issue_number=issue["issue_number"],
            issue_url=issue["issue_url"],
        )

        # Step 4: Notify GroupMe
        send_groupme_message(
            f"✅ Task submitted to GitHub Copilot!\n"
            f"📋 Issue #{issue['issue_number']}: {title}\n"
            f"🔗 {issue['html_url']}\n"
            f"⏳ Copilot is now working on it. I'll notify you when a PR is ready."
        )

    except Exception as e:
        logger.error("[Pipeline] Task %s failed: %s", task_id, e)
        task_mgr.update_status(task_id, TaskStatus.FAILED, error=str(e))
        send_groupme_message(f"❌ Task failed: {e}")


def handle_task_command(description: str, group_id: str, requester: str) -> str:
    """Handle a 'task: ...' command from GroupMe."""
    # Check for missing configuration
    missing = []
    if not os.environ.get("GOOGLE_API_KEY"):
        missing.append("GOOGLE_API_KEY")
    if not os.environ.get("GITHUB_TOKEN"):
        missing.append("GITHUB_TOKEN")
    if not os.environ.get("GITHUB_REPO"):
        missing.append("GITHUB_REPO")
    if missing:
        return f"⚠️ Cannot run tasks — missing env vars: {', '.join(missing)}"

    # Allow new tasks if the active one has been handed off to Copilot (assigned/PR stage),
    # since those run autonomously and don't block new work.
    active = task_mgr.get_active_task(group_id)
    if active and active.status not in (TaskStatus.COPILOT_ASSIGNED, TaskStatus.PR_CREATED):
        return f"⏳ A task is already in progress ({active.task_id}): \"{active.description[:60]}\""

    # Create the task and run the pipeline in background
    task = task_mgr.create_task(description, group_id, requester)
    thread = threading.Thread(
        target=_run_task_pipeline,
        args=(task.task_id, description, group_id),
        daemon=True,
    )
    thread.start()

    return f"🚀 Task {task.task_id} received! Starting the Gemini → Copilot pipeline..."


def handle_status_command(group_id: str) -> str:
    """Handle a 'status' command — show current task progress."""
    active = task_mgr.get_active_task(group_id)
    if not active:
        return "📭 No active tasks. Send 'task: <description>' to start one."

    status_emoji = {
        TaskStatus.RECEIVED: "📩",
        TaskStatus.PROMPTING: "🧠",
        TaskStatus.ISSUE_CREATED: "📝",
        TaskStatus.COPILOT_ASSIGNED: "🤖",
        TaskStatus.PR_CREATED: "🔀",
        TaskStatus.COMPLETED: "✅",
        TaskStatus.FAILED: "❌",
    }

    msg = (
        f"{status_emoji.get(active.status, '❓')} {active.task_id}: {active.status.value}\n"
        f"📝 \"{active.description[:80]}\"\n"
    )
    if active.issue_number:
        msg += f"📋 Issue #{active.issue_number}\n"
    if active.pr_url:
        msg += f"🔀 PR: {active.pr_url}\n"
    if active.error:
        msg += f"❌ Error: {active.error[:100]}\n"

    # If assigned to Copilot, check for linked PRs
    if active.status == TaskStatus.COPILOT_ASSIGNED and active.issue_number:
        try:
            prs = get_issue_linked_prs(active.issue_number)
            if prs:
                pr = prs[0]
                task_mgr.update_status(
                    active.task_id,
                    TaskStatus.PR_CREATED,
                    pr_number=pr["number"],
                    pr_url=pr["html_url"],
                )
                msg += f"🎉 Copilot created PR #{pr['number']}: {pr['html_url']}\n"
        except Exception:
            pass  # Silently ignore — just means no PR yet

    return msg


def handle_tasks_command(group_id: str) -> str:
    """Handle a 'tasks' command — show recent task history."""
    tasks = task_mgr.get_group_tasks(group_id, limit=5)
    if not tasks:
        return "📭 No tasks yet. Send 'task: <description>' to start one."

    lines = ["📋 Recent tasks:"]
    for t in tasks:
        status = t.status.value
        lines.append(f"  • {t.task_id} [{status}]: \"{t.description[:50]}\"")
    return "\n".join(lines)


def parse_command(text: str) -> tuple[Optional[str], Optional[str]]:
    """
    Parse a GroupMe message for bot commands.

    Returns:
        Tuple of (command, argument) or (None, None) if not a command.
    """
    lower = text.lower().strip()

    if lower.startswith("task:"):
        return "task", text[5:].strip()
    if lower.startswith("task "):
        return "task", text[5:].strip()
    if lower == "status":
        return "status", None
    if lower == "tasks":
        return "tasks", None
    if lower == "help":
        return "help", None

    return None, None


@app.route("/callback", methods=["POST"])
def callback():
    """
    GroupMe webhook callback endpoint.
    GroupMe sends a POST request here whenever a message is sent in the group.
    """
    data = request.get_json(silent=True)

    if not data:
        logger.warning("[Webhook] Received empty or non-JSON payload")
        return jsonify({"status": "ignored"}), 200

    sender_type = data.get("sender_type", "")
    sender_name = data.get("name", "Someone")
    text = data.get("text", "").strip()
    group_id = data.get("group_id", "default")

    logger.info("[Webhook] Message from '%s' (type=%s): %s", sender_name, sender_type, text[:100])

    # Ignore messages sent by bots (including ourselves) to prevent infinite loops
    if sender_type == "bot":
        return jsonify({"status": "ignored"}), 200

    # Ignore empty messages
    if not text:
        return jsonify({"status": "ignored"}), 200

    # Check if this is a bot command
    command, argument = parse_command(text)

    if command == "task" and argument:
        reply = handle_task_command(argument, group_id, sender_name)
    elif command == "status":
        reply = handle_status_command(group_id)
    elif command == "tasks":
        reply = handle_tasks_command(group_id)
    elif command == "help":
        reply = (
            "🤖 Available commands:\n"
            "• task: <description> — Start an AI coding task\n"
            "• status — Check current task progress\n"
            "• tasks — Show recent task history\n"
            "• help — Show this message\n"
            "• (anything else) — Chat with Gemini AI"
        )
    else:
        # Regular chat — send to Gemini
        reply = get_gemini_response(group_id, sender_name, text)

    send_groupme_message(reply)
    return jsonify({"status": "ok"}), 200


@app.route("/github-webhook", methods=["POST"])
def github_webhook():
    """
    GitHub webhook endpoint — receives events when Copilot creates PRs.

    Configure in GitHub repo settings:
      Payload URL: https://your-server/github-webhook
      Content type: application/json
      Events: Pull requests
    """
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"status": "ignored"}), 200

    action = data.get("action", "")
    pr = data.get("pull_request")

    if not pr:
        return jsonify({"status": "ignored"}), 200

    # We care about PR opened events
    if action != "opened":
        return jsonify({"status": "ok"}), 200

    pr_number = pr.get("number")
    pr_title = pr.get("title", "")
    pr_url = pr.get("html_url", "")
    pr_body = pr.get("body", "")

    # Check if this PR was created by a bot (Copilot)
    user = pr.get("user", {})
    user_type = user.get("type", "")
    user_login = user.get("login", "")

    if user_type != "Bot" and "copilot" not in user_login.lower():
        return jsonify({"status": "ok"}), 200

    logger.info("[GitHub Webhook] Copilot PR #%d: %s", pr_number, pr_title)

    # Try to find the linked task by scanning the PR body for issue references
    # and update task status
    notify_msg = (
        f"🎉 Copilot created a pull request!\n"
        f"🔀 PR #{pr_number}: {pr_title}\n"
        f"🔗 {pr_url}\n"
        f"Review and merge when ready."
    )
    send_groupme_message(notify_msg)

    return jsonify({"status": "ok"}), 200


@app.route("/health", methods=["GET"])
def health():
    """Health check endpoint."""
    return jsonify({
        "status": "running",
        "bot_name": BOT_NAME,
        "bot_id_set": GROUPME_BOT_ID != "your_groupme_bot_id_here",
        "google_api_key_set": bool(os.environ.get("GOOGLE_API_KEY")),
        "github_token_set": bool(os.environ.get("GITHUB_TOKEN")),
        "github_repo": os.environ.get("GITHUB_REPO", "(not set)"),
    }), 200


@app.route("/", methods=["GET"])
def index():
    return (
        "<h2>GroupMe AI Bot is running!</h2>"
        "<p>Endpoints:</p>"
        "<ul>"
        "<li><code>POST /callback</code> — GroupMe webhook</li>"
        "<li><code>POST /github-webhook</code> — GitHub webhook for PR notifications</li>"
        "<li><code>GET /health</code> — Health check</li>"
        "</ul>"
    )


if __name__ == "__main__":
    logger.info("=" * 50)
    logger.info("  GroupMe AI Bot starting on port 8000")
    logger.info("  Bot Name       : %s", BOT_NAME)
    logger.info("  Bot ID set     : %s", GROUPME_BOT_ID != "your_groupme_bot_id_here")
    logger.info("  Google API key : %s", bool(os.environ.get("GOOGLE_API_KEY")))
    logger.info("  GitHub token   : %s", bool(os.environ.get("GITHUB_TOKEN")))
    logger.info("  GitHub repo    : %s", os.environ.get("GITHUB_REPO", "(not set)"))
    logger.info("  Callback URL   : POST http://<your-host>:8000/callback")
    logger.info("  GitHub Webhook : POST http://<your-host>:8000/github-webhook")
    logger.info("=" * 50)
    app.run(host="0.0.0.0", port=8000, debug=False)
