#!/usr/bin/env bash
# start.sh — Launches the GroupMe bot and a Cloudflare Tunnel together.
#
# The tunnel exposes port 8000 to the internet so GroupMe and GitHub
# webhooks can reach the bot from anywhere (server, Codespace, etc.).
#
# Usage:
#   ./start.sh                   # uses TUNNEL_NAME env var or a quick tunnel
#   TUNNEL_NAME=my-tunnel ./start.sh   # uses a named tunnel
#
# Prerequisites:
#   - Python 3.10+ with pip
#   - cloudflared installed (see README.md)
#   - Environment variables set (GOOGLE_API_KEY, GROUPME_BOT_ID, etc.)
#
set -euo pipefail

# ---------------------------------------------------------------------------
# Colours for output
# ---------------------------------------------------------------------------
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Colour

info()  { echo -e "${GREEN}[start]${NC} $*"; }
warn()  { echo -e "${YELLOW}[start]${NC} $*"; }
error() { echo -e "${RED}[start]${NC} $*" >&2; }

# ---------------------------------------------------------------------------
# Pre-flight checks
# ---------------------------------------------------------------------------
if ! command -v python3 &>/dev/null; then
    error "python3 not found. Please install Python 3.10+."
    exit 1
fi

if ! command -v cloudflared &>/dev/null; then
    warn "cloudflared not found — installing..."
    # Detect architecture and install
    if [[ "$(uname -s)" == "Linux" ]]; then
        ARCH=$(dpkg --print-architecture 2>/dev/null || echo "amd64")
        if ! command -v dpkg &>/dev/null; then
            warn "dpkg not found — defaulting to amd64 architecture for cloudflared download."
        fi
        curl -fsSL "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-${ARCH}.deb" -o /tmp/cloudflared.deb
        sudo dpkg -i /tmp/cloudflared.deb
        rm -f /tmp/cloudflared.deb
    elif [[ "$(uname -s)" == "Darwin" ]]; then
        brew install cloudflare/cloudflare/cloudflared
    else
        error "Unsupported OS. Install cloudflared manually: https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/downloads/"
        exit 1
    fi
fi

# ---------------------------------------------------------------------------
# Install Python dependencies
# ---------------------------------------------------------------------------
info "Installing Python dependencies..."
pip install -q -r requirements.txt

# ---------------------------------------------------------------------------
# Check required env vars
# ---------------------------------------------------------------------------
MISSING=()
[[ -z "${GOOGLE_API_KEY:-}" ]]  && MISSING+=("GOOGLE_API_KEY")
[[ -z "${GROUPME_BOT_ID:-}" ]] && MISSING+=("GROUPME_BOT_ID")

if [[ ${#MISSING[@]} -gt 0 ]]; then
    error "Missing required environment variables: ${MISSING[*]}"
    error "Set them before running:  export GOOGLE_API_KEY=... GROUPME_BOT_ID=..."
    exit 1
fi

# Optional vars — just warn
[[ -z "${GITHUB_TOKEN:-}" ]] && warn "GITHUB_TOKEN not set — 'task:' commands will not work."
[[ -z "${GITHUB_REPO:-}" ]] && warn "GITHUB_REPO not set — 'task:' commands will not work."

# ---------------------------------------------------------------------------
# Trap: clean up background processes on exit
# ---------------------------------------------------------------------------
TUNNEL_PID=""
BOT_PID=""

cleanup() {
    info "Shutting down..."
    [[ -n "$TUNNEL_PID" ]] && kill "$TUNNEL_PID" 2>/dev/null && info "Tunnel stopped."
    [[ -n "$BOT_PID" ]]    && kill "$BOT_PID"    2>/dev/null && info "Bot stopped."
    exit 0
}
trap cleanup EXIT INT TERM

# ---------------------------------------------------------------------------
# Start the Flask bot
# ---------------------------------------------------------------------------
info "Starting GroupMe bot on port 8000..."
python3 groupme_bot.py &
BOT_PID=$!
sleep 2

if ! kill -0 "$BOT_PID" 2>/dev/null; then
    error "Bot failed to start."
    exit 1
fi

# ---------------------------------------------------------------------------
# Start the Cloudflare Tunnel
# ---------------------------------------------------------------------------
TUNNEL_NAME="${TUNNEL_NAME:-}"

if [[ -n "$TUNNEL_NAME" ]]; then
    # Named tunnel (requires prior `cloudflared tunnel login` and `cloudflared tunnel create`)
    info "Starting named Cloudflare Tunnel: $TUNNEL_NAME"
    cloudflared tunnel run --url http://localhost:8000 "$TUNNEL_NAME" &
    TUNNEL_PID=$!
else
    # Quick tunnel — no login needed, gives a temporary *.trycloudflare.com URL
    info "Starting quick Cloudflare Tunnel (temporary URL)..."
    cloudflared tunnel --url http://localhost:8000 &
    TUNNEL_PID=$!
fi

info ""
info "=============================================="
info "  Bot is running on http://localhost:8000"
info "  Cloudflare Tunnel is starting..."
info "  Watch the output above for your public URL"
info "  (look for *.trycloudflare.com)"
info ""
info "  Set your GroupMe callback URL to:"
info "    https://<your-tunnel-url>/callback"
info ""
info "  Set your GitHub webhook URL to:"
info "    https://<your-tunnel-url>/github-webhook"
info "=============================================="
info ""

# Keep running until interrupted
wait "$BOT_PID"
