# 💡 Ideas: Dual-AI Agent System with GroupMe Approval Workflow

## Overview

A local development system that runs **Claude** and **Gemini** AI agents on your computer, coordinated through a **GroupMe chat** where you can review, approve, or reject their proposed actions before they touch your codebase. One AI writes the prompts for the other, creating a self-improving feedback loop.

---

## 🧠 Core Concept: AI Writing Prompts for AI

Instead of you manually prompting each model, **one AI agent acts as the "Prompt Architect"** and the other acts as the **"Executor."** They take turns depending on the task:

| Role | Description |
|---|---|
| **Prompt Architect** | Analyzes the task, writes a detailed prompt for the other AI |
| **Executor** | Receives the crafted prompt, produces the code/output |
| **Reviewer** | The Architect reviews the Executor's output and suggests refinements |

The roles can swap — Claude writes prompts for Gemini on some tasks, Gemini writes prompts for Claude on others — based on each model's strengths.

### Example Flow

1. You send a message in GroupMe: *"Add a /stats endpoint to the bot"*
2. **Claude (Prompt Architect)** analyzes the codebase and writes a detailed, context-rich prompt for Gemini
3. **Gemini (Executor)** receives that prompt and generates the code changes
4. **Claude (Reviewer)** reviews Gemini's output, suggests fixes if needed
5. The final proposed diff is sent to **GroupMe** for your approval
6. You reply **"approve"** → changes are committed and a PR is created

---

## 🏗️ System Architecture

```
┌─────────────────────────────────────────────────┐
│                  Your Computer                   │
│                                                  │
│  ┌──────────────┐       ┌──────────────┐        │
│  │  Claude API  │◄─────►│  Gemini API  │        │
│  │   (Agent)    │       │   (Agent)    │        │
│  └──────┬───────┘       └──────┬───────┘        │
│         │                      │                 │
│         ▼                      ▼                 │
│  ┌─────────────────────────────────────┐        │
│  │         Orchestrator Service         │        │
│  │  - Routes tasks between agents       │        │
│  │  - Manages prompt generation         │        │
│  │  - Tracks conversation context       │        │
│  │  - Applies code changes locally      │        │
│  └──────────────────┬──────────────────┘        │
│                     │                            │
│         ┌───────────┼───────────┐               │
│         ▼           ▼           ▼               │
│    ┌─────────┐ ┌─────────┐ ┌─────────┐        │
│    │  Git    │ │  Local  │ │ GitHub  │        │
│    │  Repo   │ │  Files  │ │  API    │        │
│    └─────────┘ └─────────┘ └─────────┘        │
│                                                  │
└──────────────────────┬──────────────────────────┘
                       │
                       ▼
              ┌────────────────┐
              │   GroupMe Bot  │
              │  (Approval Hub)│
              └────────┬───────┘
                       │
                       ▼
              ┌────────────────┐
              │  Your Phone /  │
              │  GroupMe App   │
              └────────────────┘
```

---

## 📱 GroupMe as the Approval Layer

GroupMe becomes your **mobile command center** for reviewing and approving AI actions. The existing `groupme_bot.py` is extended to support approval workflows.

### Commands You Can Send in GroupMe

| Command | What It Does |
|---|---|
| `task: <description>` | Start a new AI task (e.g., `task: add rate limiting to /callback`) |
| `approve` | Approve the latest proposed change |
| `reject` | Reject the latest proposed change with optional feedback |
| `reject: <reason>` | Reject with specific feedback — AI will retry |
| `diff` | Show the current proposed diff |
| `status` | Show what the agents are working on |
| `pr` | Create a pull request from approved changes |
| `pr: <title>` | Create a PR with a custom title |
| `switch` | Swap which AI is the Prompt Architect vs. Executor |
| `log` | Show recent agent activity |
| `cancel` | Cancel the current task |

### What Gets Sent to GroupMe for Approval

- 📝 **Summary** of what the AI wants to change (plain English)
- 📊 **Files affected** and lines changed
- ⚠️ **Risk assessment** (low / medium / high)
- 🔗 **Link to full diff** (hosted locally or on GitHub)

---

## 🔄 Dual-AI Prompt Relay System

### How One AI Writes Prompts for the Other

```
Step 1: You say "Add error logging to the bot"
                    │
                    ▼
Step 2: Claude (Architect) reads the codebase and writes:
        ┌──────────────────────────────────────────────────┐
        │ PROMPT FOR GEMINI:                                │
        │                                                   │
        │ Context: Flask app in groupme_bot.py, 162 lines.  │
        │ Current error handling: bare except with print().  │
        │                                                   │
        │ Task: Add Python logging module with:              │
        │ - File handler (bot.log)                          │
        │ - Console handler (INFO level)                    │
        │ - Log all webhook receives, API calls, errors     │
        │ - Replace all print() calls with logger calls     │
        │                                                   │
        │ Constraints:                                      │
        │ - Don't change the Flask route structure           │
        │ - Keep backward compat with env vars              │
        │ - Follow existing code style (type hints, etc.)   │
        └──────────────────────────────────────────────────┘
                    │
                    ▼
Step 3: Gemini receives this prompt and generates code changes
                    │
                    ▼
Step 4: Claude reviews the output, checks for issues
                    │
                    ▼
Step 5: Final result sent to GroupMe for your approval
```

### Why This Is Better Than Prompting One AI Directly

- **Context injection** — The Architect deeply analyzes the codebase and writes context-rich prompts the Executor wouldn't have on its own
- **Cross-model strengths** — Claude excels at reasoning and code review; Gemini excels at fast generation and refactoring
- **Built-in review** — Every output gets reviewed by a second AI before you even see it
- **Prompt quality** — AI-written prompts are more structured and complete than most human prompts

---

## 🛠️ Technical Implementation Plan

### 1. Local Orchestrator Service (`orchestrator.py`)

- Runs on your machine alongside the existing GroupMe bot
- Manages the task queue and agent coordination
- Reads/writes files in your local git repository
- Calls Claude API and Gemini API
- Generates diffs and manages git branches

### 2. Extended GroupMe Bot (`groupme_bot.py` updates)

- New command parser for `task:`, `approve`, `reject`, `pr`, etc.
- Approval queue — holds proposed changes until you approve/reject
- Sends rich summaries of proposed changes
- Handles multi-step approval for large changes

### 3. Git Integration (`git_manager.py`)

- Creates feature branches for each task
- Generates clean diffs for review
- Commits approved changes with descriptive messages
- Creates pull requests via GitHub API
- Supports squash, rebase, or merge strategies

### 4. Agent Coordination (`agent_relay.py`)

- Manages the Architect ↔ Executor prompt relay
- Injects codebase context into prompts automatically
- Tracks which model works better for which task types
- Handles retries and refinement loops

### 5. Configuration (`config.yaml`)

```yaml
agents:
  claude:
    api_key_env: ANTHROPIC_API_KEY
    model: claude-sonnet-4-5-20250929
    default_role: architect   # writes prompts for the other
  gemini:
    api_key_env: GOOGLE_API_KEY
    model: gemini-2.0-flash
    default_role: executor    # receives prompts and generates code

groupme:
  bot_id_env: GROUPME_BOT_ID
  approval_required: true     # require approval before any code change
  auto_approve_low_risk: false

git:
  auto_branch: true           # create a new branch per task
  branch_prefix: ai/
  auto_pr: false              # only create PR when you say "pr"
  repo_path: .                # path to your local repo

orchestrator:
  max_retries: 3              # max times the Architect can ask for revisions
  context_lines: 50           # lines of context to include around relevant code
  risk_threshold: medium      # auto-flag changes above this risk level
```

---

## 🚀 How to Run It (Future)

```bash
# 1. Install dependencies
pip install flask anthropic google-generativeai requests gitpython pyyaml

# 2. Set API keys
export ANTHROPIC_API_KEY="sk-ant-..."
export GOOGLE_API_KEY="AIza..."
export GROUPME_BOT_ID="your-bot-id"

# 3. Start the system
python orchestrator.py
```

This starts:
- The GroupMe webhook listener (existing bot, extended)
- The orchestrator that coordinates Claude ↔ Gemini
- The git manager that handles branches and PRs
- A local web dashboard (optional) at `http://localhost:8080`

---

## 🔮 Future Enhancements

- **Learning from approvals** — Track which changes you approve/reject to improve future prompts
- **Multi-repo support** — Manage multiple projects from the same GroupMe chat
- **Scheduled tasks** — "Every morning, have the AI review yesterday's commits"
- **Voice notes** — Send a voice message in GroupMe, transcribe it, and use it as a task
- **Team mode** — Multiple people in the GroupMe can vote to approve/reject
- **Cost tracking** — Show API costs per task in GroupMe
- **Rollback** — Send "undo" in GroupMe to revert the last approved change
- **Test generation** — AI automatically writes tests for proposed changes before sending for approval
- **CI integration** — Run tests on proposed changes and include pass/fail in the approval message

---

## 📋 MVP Milestones

1. **Phase 1** — Extend `groupme_bot.py` to parse `task:` and `approve`/`reject` commands
2. **Phase 2** — Add Claude ↔ Gemini prompt relay (one writes prompts for the other)
3. **Phase 3** — Git integration (branching, diffs, commits)
4. **Phase 4** — GitHub PR creation from GroupMe
5. **Phase 5** — Risk assessment and smart summaries
6. **Phase 6** — Learning and optimization from approval history
