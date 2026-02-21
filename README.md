# AI Stack — Unraid Deployment

## Stack Overview

| Service | Image | Purpose |
|---|---|---|
| `open-webui` | `ghcr.io/open-webui/open-webui:main` | Team chat frontend |
| `litellm` | `ghcr.io/berriai/litellm:main-latest` | LLM proxy (OpenAI-compatible) |
| `postgres` | `pgvector/pgvector:pg16` | App DB + vector store |

All services communicate on the `ai-net` bridge network. Only Open WebUI's port is exposed to your LAN.

---

## First-Time Deployment

### 1. Place files on Unraid

Copy the entire `ai-stack` folder to your Unraid box. A good location:

```bash
/mnt/user/appdata/ai-stack-config/
```

### 2. Configure your environment

```bash
cd /mnt/user/appdata/ai-stack-config
cp .env.example .env
nano .env
```

Required values to fill in:
- `POSTGRES_PASSWORD` — strong random password
- `LITELLM_MASTER_KEY` — generate with `openssl rand -hex 32`
- `WEBUI_SECRET_KEY` — generate with `openssl rand -hex 32`
- `OPENAI_API_KEY` — your OpenAI API key
- `ANTHROPIC_API_KEY` — your Anthropic API key

### 3. Run the setup script

```bash
chmod +x setup.sh
bash setup.sh
```

This will:
- Create `/mnt/user/appdata/ai-stack/` directories
- Create the `ai-net` Docker network
- Pull all images
- Start the stack

### 4. Access Open WebUI

Navigate to `http://<your-unraid-ip>:8089`

The **first account created becomes Admin** automatically. Subsequent signups will have `pending` status until you approve them in Admin > Users.

---

## Directory Structure

```
/mnt/user/appdata/
└── ai-stack/              # Persistent data (auto-created by setup.sh)
    ├── postgres/           # Database files
    └── open-webui/         # Uploads, configs, tool data

/mnt/user/appdata/ai-stack-config/   # (suggested) Config files live here
    ├── docker-compose.yml
    ├── litellm-config.yaml
    ├── init-db.sql
    ├── .env                # Your secrets (gitignored)
    ├── .env.example
    └── setup.sh
```

---

## Adding LLM Models

Edit `litellm-config.yaml` and add entries under `model_list`. Then restart LiteLLM:

```bash
docker compose restart litellm
```

### Adding Local Ollama (future)
If you later add Ollama running directly on Unraid (not in Docker), use `host.docker.internal` as the address:

```yaml
- model_name: llama3.2
  litellm_params:
    model: ollama/llama3.2
    api_base: http://host.docker.internal:11434
```

---

## Team Auth Options

### Current: Built-in (default)
- First user = Admin
- `DEFAULT_USER_ROLE=pending` means new signups need admin approval
- Manage users at: Admin Panel > Users

### Future: OAuth / SSO
Uncomment the OAuth block in `docker-compose.yml` and `.env`:

```yaml
# In docker-compose.yml environment section:
ENABLE_OAUTH_SIGNUP: "true"
OAUTH_PROVIDER_NAME: "Google"
GOOGLE_CLIENT_ID: ${GOOGLE_CLIENT_ID}
GOOGLE_CLIENT_SECRET: ${GOOGLE_CLIENT_SECRET}
```

Supports Google, Microsoft (Azure AD), OIDC-compatible providers.

---

## Agentic Features & Tools

Open WebUI ships with these enabled in this config:
- **Tools** (`ENABLE_TOOLS=true`) — custom Python tools callable by models
- **Code Execution** (`ENABLE_CODE_EXECUTION=true`) — sandboxed code runner
- **Function calling** — works via LiteLLM for any model that supports it

To add a custom tool: Admin Panel > Tools > + New Tool

---

## Useful Commands

```bash
# View live logs for all services
docker compose logs -f

# View logs for a specific service
docker compose logs -f litellm

# Restart a single service
docker compose restart open-webui

# Pull latest images and redeploy
docker compose pull && docker compose up -d

# Stop the stack (data preserved)
docker compose down

# Nuclear reset (DESTROYS all data)
docker compose down -v
```

---

## Monitoring LiteLLM

LiteLLM has a built-in UI for managing virtual keys, viewing spend, and checking model health. It's accessible internally at:

```
http://<unraid-ip>:4002/ui
```

Login with your `LITELLM_MASTER_KEY`. You can create per-user virtual keys here so team members have individual spend tracking without sharing the master key.

> Note: Port 4002 is NOT exposed to your LAN in this config (internal only). To expose it, add `ports: - "4002:4000"` to the litellm service.

---

## Upgrading

```bash
docker compose pull
docker compose up -d
```

Postgres data and Open WebUI data are in persistent volumes and survive upgrades.