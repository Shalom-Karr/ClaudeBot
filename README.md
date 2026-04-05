# 🤖 ClaudeBot

A **GroupMe AI chatbot** powered by [Claude](https://www.anthropic.com/) (Anthropic). ClaudeBot listens for messages in your GroupMe group chat via webhooks and responds intelligently using the Claude AI model — with per-group conversation memory.

---

## ✨ Features

- 🧠 **Claude AI responses** — Uses `claude-sonnet-4-5-20250929` for smart, conversational replies
- 💬 **GroupMe integration** — Receives messages via webhook callback and replies through the GroupMe Bot API
- 🗂️ **Per-group conversation history** — Maintains context (last 20 messages) per group chat
- 🔁 **Loop prevention** — Automatically ignores messages from other bots
- ❤️ **Health check endpoint** — `/health` route for monitoring
- 🚀 **Ready to deploy** — Listens on `0.0.0.0:8000` out of the box

---

## 📁 Project Structure

```
ClaudeBot/
├── .github/
│   └── copilot-instructions.md   # Instructions for GitHub Copilot agent
├── groupme_bot.py                # Main application (Flask server + Claude AI + GroupMe integration)
├── ideas.md                      # Project roadmap, architecture & development plans
└── README.md                     # You are here
```

---

## 🔧 Environment Variables

You **must** set these environment variables before running or deploying:

| Variable | Required | Description |
|---|---|---|
| `ANTHROPIC_API_KEY` | ✅ Yes | Your Anthropic API key ([get one here](https://console.anthropic.com/)) |
| `GROUPME_BOT_ID` | ✅ Yes | Your GroupMe bot ID ([create a bot here](https://dev.groupme.com/bots)) |
| `BOT_NAME` | ❌ Optional | Display name for the bot (default: `AI Assistant`) |

---

## 🏃 Run Locally

### 1. Clone the repo

```bash
git clone https://github.com/JMTDI/ClaudeBot.git
cd ClaudeBot
```

### 2. Install dependencies

```bash
pip install flask anthropic requests
```

### 3. Set environment variables

```bash
export ANTHROPIC_API_KEY="your_anthropic_api_key_here"
export GROUPME_BOT_ID="your_groupme_bot_id_here"
export BOT_NAME="My Bot"  # optional
```

### 4. Start the server

```bash
python groupme_bot.py
```

The bot will start listening on `http://0.0.0.0:8000`.

### 5. Expose publicly (for local dev)

Use [ngrok](https://ngrok.com/) or a similar tool to expose port 8000:

```bash
ngrok http 8000
```

Then set your GroupMe bot's **Callback URL** to:

```
https://your-ngrok-url/callback
```

---

## 🚀 Deploy to DevPu.sh

[DevPu.sh](https://app.devpu.sh/) is the easiest way to get ClaudeBot running in the cloud. Follow these steps:

### Step 1 — Go to DevPu.sh

Head to **[https://app.devpu.sh/](https://app.devpu.sh/)** and log in (or create an account).

### Step 2 — Connect your repository

Connect your GitHub account and select this forked repo.

### Step 3 — Configure Build & Deploy settings

Use the following configuration:

| Setting | Value |
|---|---|
| **Framework Preset** | Python |
| **Image** | `Python 3.12` |
| **Root Directory** | `/` (root of the repo) |
| **Build Command** | `pip install flask anthropic requests` |
| **Pre-deploy Command** | *(leave empty)* |
| **Start Command** | `python groupme_bot.py` |

> ⚠️ The app **must listen on `0.0.0.0:8000`** — ClaudeBot already does this by default.

### Step 4 — Set environment variables

In the DevPu.sh dashboard, add your environment variables:

```
ANTHROPIC_API_KEY = your_anthropic_api_key_here
GROUPME_BOT_ID   = your_groupme_bot_id_here
BOT_NAME         = My Bot   (optional)
```

### Step 5 — Deploy 🚀

Click **Deploy**. DevPu.sh will:

1. Pull your code from GitHub
2. Use the **Python 3.12** image
3. Run the build command: `pip install flask anthropic requests`
4. Start your app with: `python groupme_bot.py`

Once deployed, you'll get a public URL like:

```
https://your-app-name.devpu.sh
```

### Step 6 — Update GroupMe callback URL

Go to [https://dev.groupme.com/bots](https://dev.groupme.com/bots), find your bot, and set the **Callback URL** to:

```
https://your-app-name.devpu.sh/callback
```

---

## 🔗 API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/` | Homepage — confirms bot is running |
| `POST` | `/callback` | GroupMe webhook — receives messages and sends AI replies |

---

## 🛠️ How It Works

1. A user sends a message in your **GroupMe group chat**
2. GroupMe sends a **POST webhook** to `/callback` with the message data
3. ClaudeBot checks if the message is from a human (ignores bot messages to avoid loops)
4. The message is sent to **Claude AI** along with the last 20 messages for context
5. Claude's response is posted back to the **GroupMe group** via the Bot API

---

## 📝 License

This project is open source. Feel free to fork and customize!

---

**Built with ❤️ using [Flask](https://flask.palletsprojects.com/), [Anthropic Claude](https://www.anthropic.com/), and [GroupMe](https://dev.groupme.com/)**
