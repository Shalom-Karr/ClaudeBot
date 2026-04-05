# Copilot Instructions for ClaudeBot

## Project Overview

ClaudeBot is a GroupMe AI chatbot powered by Google Gemini. It listens for messages in GroupMe group chats via webhooks and responds using Gemini AI, with per-group conversation memory. It also has a coding pipeline: users send `task:` commands in GroupMe → Gemini crafts a detailed prompt → a GitHub issue is created and assigned to Copilot → Copilot creates a PR.

## Project Roadmap & Architecture

The file `ideas.md` in the repository root contains the full project roadmap, architecture plans, and MVP milestones. **Always read `ideas.md` before working on tasks** to understand:

- The **Dual-AI Agent System** design (Gemini as prompt architect + Copilot/Claude as executor)
- The **GroupMe approval workflow** where users approve/reject AI-proposed changes
- The **system architecture** including orchestrator, agent relay, and git integration
- The **technical implementation plan** with planned modules
- The **MVP milestones** and phased rollout plan

## Codebase

- **`groupme_bot.py`** — Main Flask application: webhook handlers, command parsing, orchestration
- **`gemini_architect.py`** — Gemini AI: conversation chat + prompt architect for crafting GitHub issues
- **`github_copilot.py`** — GitHub API: repo file listing, issue creation, Copilot assignment, PR tracking
- **`task_manager.py`** — In-memory task state tracking (task lifecycle from received → PR created)
- **`start.sh`** — Launch script that starts the bot + Cloudflare Tunnel together
- **`ideas.md`** — Project roadmap, architecture, and development plans
- **`README.md`** — Setup and deployment documentation

## Coding Conventions

- Python 3.10+ with type hints
- Flask for the web server
- `google-genai` SDK for Gemini API (NOT the deprecated `google-generativeai`)
- Environment variables for configuration (never hardcode secrets)
- Concise, well-documented functions with docstrings
- Bot loop prevention (ignore messages from bots)
- Per-group conversation history with configurable limits
- Logging via Python `logging` module (not `print()`)

## Key Design Principles

- Gemini handles both conversation and prompt architecture
- Copilot (Claude) is triggered via GitHub Issues API — assign issue to `copilot`
- All AI-proposed code changes go through the GroupMe approval workflow
- Cloudflare Tunnel for public endpoint (replaces ngrok)
- Runs on Linux servers and GitHub Codespaces via devcontainer
- Mobile-first: control everything from GroupMe on your phone
