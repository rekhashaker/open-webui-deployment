#!/bin/bash
###############################################################################
# AI Stack - Unraid Setup & Deploy Script
# Run from the directory containing docker-compose.yml
# Usage: bash setup.sh
###############################################################################

set -e

STACK_DIR="/mnt/user/appdata/ai-stack"
COMPOSE_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "============================================="
echo "  AI Stack Setup"
echo "============================================="

# --- Step 1: Create Unraid appdata directories ---
echo ""
echo "[1/4] Creating appdata directories..."
mkdir -p "$STACK_DIR/postgres"
mkdir -p "$STACK_DIR/open-webui"
mkdir -p "$STACK_DIR/litellm"
mkdir -p "$STACK_DIR/redis"
mkdir -p "$STACK_DIR/searxng"
echo "      Created: $STACK_DIR"

# --- Step 2: Check .env exists ---
echo ""
echo "[2/4] Checking configuration..."
if [ ! -f "$COMPOSE_DIR/.env" ]; then
  echo ""
  echo "  ERROR: .env file not found."
  echo "  Please copy .env.example to .env and fill in your values:"
  echo ""
  echo "    cp $COMPOSE_DIR/.env.example $COMPOSE_DIR/.env"
  echo "    nano $COMPOSE_DIR/.env"
  echo ""
  exit 1
fi

# Check for placeholder values
if grep -q "CHANGE_ME" "$COMPOSE_DIR/.env"; then
  echo ""
  echo "  WARNING: Your .env still contains CHANGE_ME placeholder values."
  echo "  Please edit .env before deploying:"
  echo "    nano $COMPOSE_DIR/.env"
  echo ""
  read -p "  Continue anyway? (not recommended for production) [y/N]: " confirm
  [[ "$confirm" =~ ^[Yy]$ ]] || exit 1
fi

echo "      .env found."

# --- Step 3: Network is managed by Docker Compose ---
echo ""
echo "[3/4] Network (ai-net) will be created by Docker Compose..."
echo "      Skipping manual creation to avoid label conflicts."
# If a stale ai-net exists from a previous manual run, remove it first
if docker network inspect ai-net >/dev/null 2>&1; then
  echo "      Found existing ai-net - removing so Compose can recreate it with correct labels..."
  docker network rm ai-net 2>/dev/null || echo "      Could not remove (may be in use - continuing anyway)"
fi

# --- Step 4: Pull images and start the stack ---
echo ""
echo "[4/4] Pulling latest images and starting stack..."
docker compose -f "$COMPOSE_DIR/docker-compose.yml" pull
docker compose -f "$COMPOSE_DIR/docker-compose.yml" up -d

echo ""
echo "============================================="
echo "  Stack started!"
echo "============================================="
echo ""
echo "  Open WebUI:    http://$(hostname -I | awk '{print $1}'):${WEBUI_PORT:-8089}"
echo "  LiteLLM UI:    http://$(hostname -I | awk '{print $1}'):4002/ui  (internal only)"
echo ""
echo "  First-time setup:"
echo "    1. Open WebUI in your browser"
echo "    2. Create the first account - it will automatically become Admin"
echo "    3. Additional signups will be 'pending' until you approve them"
echo ""
echo "  Useful commands:"
echo "    View logs:     docker compose logs -f"
echo "    Stop stack:    docker compose down"
echo "    Restart svc:   docker compose restart <service>"
echo "    Update images: docker compose pull && docker compose up -d"
echo ""