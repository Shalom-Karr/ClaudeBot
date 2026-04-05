# 🤖 ClaudeBot

A **GroupMe AI chatbot** powered by [Gemini](https://ai.google.dev/) with an integrated **AI coding pipeline** — send a message in GroupMe, and Gemini crafts a prompt for [GitHub Copilot](https://github.com/features/copilot) which creates a pull request automatically.

---

## ✨ Features

- 🧠 **Gemini AI conversations** — Chat with Gemini in your GroupMe group (per-group memory)
- 🔧 **AI coding pipeline** — Send `task: <description>` and Gemini crafts a GitHub issue → Copilot implements it → PR created
- 💬 **GroupMe integration** — Receives messages via webhook, replies through GroupMe Bot API
- 🌐 **Cloudflare Tunnel** — Expose your local server to the internet (no ngrok needed)
- 🐧 **Linux / Codespaces ready** — Runs on any Linux server or GitHub Codespace out of the box
- 🔁 **Loop prevention** — Ignores bot messages to prevent infinite loops
- ❤️ **Health check** — `/health` endpoint for monitoring

---

## 🏗️ Architecture

```
GroupMe Chat
    │
    ▼
┌──────────────────────────────────┐
│  groupme_bot.py (Flask :8000)    │
│                                  │
│  "hello" ──► Gemini Chat         │
│  "task: ..." ──► Pipeline:       │
│    1. Gemini crafts issue prompt │
│    2. GitHub Issue created       │
│    3. Copilot assigned           │
│    4. Copilot creates PR         │
└──────────┬───────────────────────┘
           │
    Cloudflare Tunnel
           │
    Public URL (*.trycloudflare.com
     or your custom domain)
```

---

## 📁 Project Structure

```
ClaudeBot/
├── .devcontainer/
│   └── devcontainer.json        # GitHub Codespaces / VS Code dev container
├── .github/
│   └── copilot-instructions.md  # Instructions for GitHub Copilot agent
├── groupme_bot.py               # Main Flask app — webhooks, commands, chat
├── gemini_architect.py          # Gemini AI — conversation + prompt architect
├── github_copilot.py            # GitHub API — issues, Copilot assignment, PRs
├── task_manager.py              # In-memory task state tracking
├── start.sh                     # Launch script (bot + Cloudflare Tunnel)
├── requirements.txt             # Python dependencies
├── ideas.md                     # Project roadmap & architecture plans
└── README.md                    # You are here
```

---

## 🔧 Environment Variables

| Variable | Required | Description |
|---|---|---|
| `GOOGLE_API_KEY` | ✅ Yes | Google AI API key for Gemini ([get one here](https://aistudio.google.com/apikey)) |
| `GROUPME_BOT_ID` | ✅ Yes | Your GroupMe bot ID ([create a bot here](https://dev.groupme.com/bots)) |
| `GITHUB_TOKEN` | For tasks | GitHub personal access token with `repo` scope |
| `GITHUB_REPO` | For tasks | Repository in `owner/repo` format (e.g., `Shalom-Karr/ClaudeBot`) |
| `BOT_NAME` | ❌ Optional | Display name for the bot (default: `AI Assistant`) |
| `GEMINI_MODEL` | ❌ Optional | Gemini model to use (default: `gemini-2.0-flash`) |
| `TUNNEL_NAME` | ❌ Optional | Named Cloudflare Tunnel (omit for quick tunnel) |

---

## 🚀 Quick Start (Linux / Codespaces)

### Option 1: GitHub Codespaces (easiest)

1. Click **Code → Codespaces → Create codespace** on this repo
2. The devcontainer auto-installs Python, dependencies, and `cloudflared`
3. Set your environment variables in the Codespace terminal:
   ```bash
   export GOOGLE_API_KEY="your_google_api_key"
   export GROUPME_BOT_ID="your_groupme_bot_id"
   export GITHUB_TOKEN="your_github_token"        # optional, for task: commands
   export GITHUB_REPO="owner/repo"                 # optional, for task: commands
   ```
4. Start the bot with Cloudflare Tunnel:
   ```bash
   ./start.sh
   ```
5. Copy the `*.trycloudflare.com` URL from the output and set it as your GroupMe bot's **Callback URL**:
   ```
   https://<your-tunnel-url>/callback
   ```

### Option 2: Any Linux Server

```bash
# 1. Clone the repo
git clone https://github.com/Shalom-Karr/ClaudeBot.git
cd ClaudeBot

# 2. Install Python dependencies
pip install -r requirements.txt

# 3. Install cloudflared (auto-installed by start.sh if missing)
# Or manually: https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/downloads/

# 4. Set environment variables
export GOOGLE_API_KEY="your_google_api_key"
export GROUPME_BOT_ID="your_groupme_bot_id"
export GITHUB_TOKEN="your_github_token"        # optional
export GITHUB_REPO="owner/repo"                 # optional

# 5. Start everything
./start.sh
```

### Option 3: Run Without Tunnel (manual port exposure)

```bash
# Just run the bot — expose port 8000 yourself (e.g., port forwarding, reverse proxy)
python groupme_bot.py
```

---

## 💬 GroupMe Commands

| Command | What It Does |
|---|---|
| `task: <description>` | Start an AI coding task — Gemini crafts a prompt → Copilot creates a PR |
| `status` | Check the current task's progress |
| `tasks` | Show recent task history |
| `help` | Show available commands |
| *(anything else)* | Chat with Gemini AI |

### Example Workflow

1. Send in GroupMe: `task: add a /stats endpoint that shows uptime`
2. Bot replies: *"🧠 Gemini is analyzing your task..."*
3. Bot replies: *"📝 Creating GitHub issue..."*
4. Bot replies: *"✅ Task submitted to GitHub Copilot! Issue #42"*
5. Copilot works on it autonomously and creates a PR
6. Bot notifies: *"🎉 Copilot created PR #43!"*

---

## 🔗 API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/` | Homepage — confirms bot is running |
| `GET` | `/health` | Health check with configuration status |
| `POST` | `/callback` | GroupMe webhook — receives messages |
| `POST` | `/github-webhook` | GitHub webhook — receives PR notifications from Copilot |

---

## 🌐 Cloudflare Tunnel Setup

The `start.sh` script handles the tunnel automatically. Two modes:

### Quick Tunnel (no account needed)
Just run `./start.sh` — it creates a temporary `*.trycloudflare.com` URL. The URL changes each time you restart.

### Named Tunnel (permanent URL)
1. Sign up at [Cloudflare Zero Trust](https://one.dash.cloudflare.com/)
2. Authenticate: `cloudflared tunnel login`
3. Create a tunnel: `cloudflared tunnel create my-bot`
4. Set the env var: `export TUNNEL_NAME=my-bot`
5. Run: `./start.sh`

---

## 🛠️ How It Works

1. **Chat mode**: User sends a message → GroupMe webhook hits `/callback` → Gemini generates a reply → posted back to GroupMe
2. **Task mode**: User sends `task: ...` → Gemini (Prompt Architect) crafts a detailed GitHub issue body → issue created via GitHub API → assigned to Copilot → Copilot implements and creates a PR → bot notifies GroupMe

---

## 📝 License

This project is open source. Feel free to fork and customize!

---

**Built with ❤️ using [Flask](https://flask.palletsprojects.com/), [Google Gemini](https://ai.google.dev/), [GitHub Copilot](https://github.com/features/copilot), [Cloudflare Tunnel](https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/), and [GroupMe](https://dev.groupme.com/)**
