"""
Gemini Prompt Architect — Uses Google Gemini to craft detailed, context-rich
prompts for the GitHub Copilot coding agent.

Gemini analyzes the user's task description along with repository context
and produces a structured GitHub issue body that Copilot can act on.
"""

import os
import logging
from typing import Optional

import google.generativeai as genai

logger = logging.getLogger(__name__)

# --- Configuration ---
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY", "")
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.0-flash")

# Configure the Gemini client
if GOOGLE_API_KEY:
    genai.configure(api_key=GOOGLE_API_KEY)


SYSTEM_PROMPT = """\
You are the **Prompt Architect** for a dual-AI coding system. Your job is to take
a user's task description and produce a detailed, well-structured GitHub issue body
that the GitHub Copilot coding agent (powered by Claude) will use to implement
code changes and create a pull request.

You will be given:
1. The user's task description (from a GroupMe chat message)
2. The repository file listing
3. Contents of key files for context

Your output must be a **GitHub issue body in Markdown** that includes:
- A clear **summary** of what needs to be done
- **Acceptance criteria** as a checklist
- **Technical context** (relevant files, existing patterns, constraints)
- **Implementation hints** if the task is complex
- Any **edge cases** to consider

Write the issue body so that an AI coding agent can autonomously implement it
without further clarification. Be specific about file paths, function names,
and expected behavior.

Do NOT include a title — just the issue body. The title will be set separately.
"""


def _get_repo_context(repo_files: list[str], file_contents: Optional[dict[str, str]] = None) -> str:
    """Format repository context for the prompt."""
    context = "## Repository Structure\n```\n"
    context += "\n".join(repo_files)
    context += "\n```\n"

    if file_contents:
        context += "\n## Key File Contents\n"
        for path, content in file_contents.items():
            context += f"\n### `{path}`\n```python\n{content}\n```\n"

    return context


def craft_issue_prompt(
    task_description: str,
    repo_files: list[str],
    file_contents: Optional[dict[str, str]] = None,
) -> dict[str, str]:
    """
    Use Gemini to craft a detailed GitHub issue body from a task description.

    Returns:
        dict with 'title' and 'body' keys for the GitHub issue.

    Raises:
        RuntimeError: If Gemini API call fails or API key is not configured.
    """
    if not GOOGLE_API_KEY:
        raise RuntimeError("GOOGLE_API_KEY environment variable is not set")

    repo_context = _get_repo_context(repo_files, file_contents)

    user_prompt = f"""\
## Task from User
{task_description}

{repo_context}

---

Now write the GitHub issue body. Also suggest a concise issue title (on the first
line, prefixed with "TITLE: "). Then write the full issue body below it.
"""

    try:
        model = genai.GenerativeModel(
            model_name=GEMINI_MODEL,
            system_instruction=SYSTEM_PROMPT,
        )
        response = model.generate_content(user_prompt)
        raw_text = response.text.strip()

        # Parse title and body
        title = f"AI Task: {task_description[:80]}"
        body = raw_text

        lines = raw_text.split("\n", 1)
        if lines[0].upper().startswith("TITLE:"):
            title = lines[0].split(":", 1)[1].strip()
            body = lines[1].strip() if len(lines) > 1 else ""

        logger.info("[Gemini] Crafted issue — title: %s", title[:80])
        return {"title": title, "body": body}

    except Exception as e:
        logger.error("[Gemini] Error crafting prompt: %s", e)
        raise RuntimeError(f"Gemini API error: {e}") from e
