# Copilot Instructions for ClaudeBot

## Project Overview

ClaudeBot is a GroupMe AI chatbot powered by Claude (Anthropic). It listens for messages in GroupMe group chats via webhooks and responds using the Claude AI model, with per-group conversation memory.

## Project Roadmap & Architecture

The file `ideas.md` in the repository root contains the full project roadmap, architecture plans, and MVP milestones. **Always read `ideas.md` before working on tasks** to understand:

- The **Dual-AI Agent System** design (Claude + Gemini working together)
- The **GroupMe approval workflow** where users approve/reject AI-proposed changes
- The **system architecture** including orchestrator, agent relay, and git integration
- The **technical implementation plan** with planned modules (`orchestrator.py`, `git_manager.py`, `agent_relay.py`, `config.yaml`)
- The **MVP milestones** and phased rollout plan

## Codebase

- **`groupme_bot.py`** — Main Flask application handling GroupMe webhooks and Claude AI responses
- **`ideas.md`** — Project roadmap, architecture, and development plans
- **`README.md`** — Setup and deployment documentation

## Coding Conventions

- Python with type hints
- Flask for the web server
- Environment variables for configuration (never hardcode secrets)
- Concise, well-documented functions with docstrings
- Bot loop prevention (ignore messages from bots)
- Per-group conversation history with configurable limits

## Key Design Principles

- All AI-proposed code changes must go through the GroupMe approval workflow before being applied
- One AI writes prompts for the other (Prompt Architect ↔ Executor pattern)
- Git integration with feature branches per task
- Risk assessment on proposed changes
- Mobile-first approval via GroupMe
