# Team AI Stack — Unraid Deployment

A self-hosted, team-ready AI platform built on Open WebUI, LiteLLM, and PostgreSQL. Designed for Unraid but works on any Docker host. Provides a single unified interface for your team to access OpenAI and Anthropic models, with per-user spend tracking, knowledge bases, custom tools, and a fully internal web search engine.

---

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                     ai-net (bridge)                 │
│                                                     │
│  Open WebUI ──► LiteLLM ──► OpenAI / Anthropic     │
│       │              │                              │
│       └──► Postgres ◄┘                              │
│       │    (pgvector)                               │
│       ├──► Redis (cache)                            │
│       ├──► Apache Tika (doc extraction)             │
│       └──► SearXNG (web search)                     │
└─────────────────────────────────────────────────────┘
         │
         └── Exposed to LAN on port 8089
```

### Services

| Container | Image | Role |
|---|---|---|
| `ai-open-webui` | `ghcr.io/open-webui/open-webui:main` | Team chat frontend |
| `ai-litellm` | `ghcr.io/berriai/litellm:main-latest` | Unified LLM proxy (OpenAI-compatible) |
| `ai-postgres` | `pgvector/pgvector:pg16` | App database + vector store |
| `ai-redis` | `redis:7-alpine` | LiteLLM response caching |
| `ai-tika` | `apache/tika:latest-full` | PDF/Word/PowerPoint text extraction |
| `ai-searxng` | `searxng/searxng:latest` | Self-hosted meta search engine |

All services communicate on the internal `ai-net` bridge network (`172.30.0.0/24`). Only Open WebUI's port is exposed to your LAN.

---

## Prerequisites

- Unraid (or any Linux Docker host) with Docker Compose v2
- API key(s) from OpenAI and/or Anthropic
- ~2 GB free RAM for a comfortable idle footprint

---

## First-Time Deployment

### 1. Place files on your host

Copy the repository to a persistent location. On Unraid the recommended path is:

```bash
/mnt/user/appdata/ai-stack-config/
```

### 2. Configure your environment

```bash
cd /mnt/user/appdata/ai-stack-config
cp .env.example .env
nano .env
```

Fill in every `CHANGE_ME` placeholder. Key values:

| Variable | How to generate |
|---|---|
| `POSTGRES_PASSWORD` | `openssl rand -hex 32` |
| `LITELLM_MASTER_KEY` | `openssl rand -hex 32` (prefix with `sk-`) |
| `WEBUI_SECRET_KEY` | `openssl rand -hex 32` |
| `SEARXNG_SECRET_KEY` | `openssl rand -hex 32` |
| `OPENAI_API_KEY` | From platform.openai.com |
| `ANTHROPIC_API_KEY` | From console.anthropic.com |

> API keys can alternatively be added later through the LiteLLM UI — see [Managing Models](#managing-models).

### 3. Run the setup script

```bash
chmod +x setup.sh
bash setup.sh
```

This will:
- Create `/mnt/user/appdata/ai-stack/` persistent data directories
- Create the `ai-net` Docker network
- Pull all images
- Start the stack

### 4. Create your admin account

Navigate to `http://<your-unraid-ip>:8089`

The **first account registered becomes the admin automatically**. All subsequent signups have `pending` status and require admin approval in **Admin Panel → Users**.

---

## Directory Structure

```
/mnt/user/appdata/
├── ai-stack/                    # Persistent data (auto-created by setup.sh)
│   ├── postgres/                # Database files
│   ├── redis/                   # Redis append-only log
│   ├── searxng/                 # SearXNG runtime data
│   └── open-webui/              # Uploads, configs, tool data
│
└── ai-stack-config/             # Config files (this repo)
    ├── docker-compose.yml
    ├── litellm-config.yaml
    ├── init-db.sql
    ├── setup.sh
    ├── .env                     # Your secrets (gitignored)
    ├── .env.example
    ├── searxng/
    │   └── settings.yml         # SearXNG configuration
    ├── patches/
    │   └── middleware.py        # Open WebUI middleware patch (see below)
    └── Skills/                  # Custom Open WebUI tool scripts
```

---

## Managing Models

Models are configured through the **LiteLLM UI**, not in `litellm-config.yaml` directly (the config file provides commented examples as a reference). The LiteLLM management UI is accessible at:

```
http://<unraid-ip>:4002/ui
```

Login with your `LITELLM_MASTER_KEY`. From here you can add API keys, activate models, create per-user virtual keys, and view spend tracking dashboards.

Alternatively, uncomment and edit entries in `litellm-config.yaml`, then restart LiteLLM to pick up changes:

```bash
docker compose restart litellm
```

### Supported provider examples (litellm-config.yaml)

```yaml
# OpenAI
- model_name: gpt-4o
  litellm_params:
    model: openai/gpt-4o
    api_key: os.environ/OPENAI_API_KEY

# Anthropic
- model_name: claude-sonnet-4
  litellm_params:
    model: anthropic/claude-sonnet-4-5
    api_key: os.environ/ANTHROPIC_API_KEY

# Local Ollama (if running directly on the Unraid host)
- model_name: llama3.2
  litellm_params:
    model: ollama/llama3.2
    api_base: http://host.docker.internal:11434
```

---

## Caching

LiteLLM uses Redis for response caching with semantic similarity matching via pgvector. Identical (or near-identical) queries are served from cache within the TTL window.

Key cache settings in `litellm-config.yaml`:

| Setting | Default | Description |
|---|---|---|
| `ttl` | `600` | Cache lifetime in seconds |
| `similarity_threshold` | `0.8` | How similar two queries must be to share a cache hit (0.0–1.0) |
| `embedding_model` | `openai/text-embedding-3-large` | Model used to embed queries for semantic search |

---

## Per-User Spend Tracking

Open WebUI forwards the signed-in user's email address to LiteLLM via the `X-OpenWebUI-User-Email` header (controlled by `ENABLE_FORWARD_USER_INFO_HEADERS=true`). LiteLLM attributes all costs to that identity. View usage breakdowns in the LiteLLM UI at `http://<unraid-ip>:4002/ui`.

---

## Custom Tools (Skills)

Custom Python tools live in the `Skills/` directory. They are loaded into Open WebUI via **Admin Panel → Tools**. Tools are designed to produce downloadable files (Word docs, Excel spreadsheets, PDFs) rather than inline output, which suits practical business use.

Dependencies are pre-installed on container start via the `command` override in `docker-compose.yml`:

```yaml
command: >
  bash -c "pip install python-docx reportlab --quiet && bash start.sh"
```

Add new tool dependencies to this line before restarting the container.

---

## Middleware Patch

The `patches/middleware.py` file is a patched version of Open WebUI's internal middleware that enables model-level tool assignment (like `skillIds`). It is bind-mounted read-only into the container.

**After every Open WebUI upgrade**, refresh the patch:

```bash
docker cp ai-open-webui:/app/backend/open_webui/utils/middleware.py patches/middleware.py
# Re-apply your changes, then restart:
docker compose restart open-webui
```

---

## Team Auth

### Current: Built-in auth (default)

New signups require admin approval (`DEFAULT_USER_ROLE=pending`). Manage users at **Admin Panel → Users**.

To disable new signups entirely (invite-only):

```bash
# In .env
ENABLE_SIGNUP=false
```

### Future: OAuth / SSO

Uncomment and fill in the OAuth block in `docker-compose.yml` and `.env`:

```yaml
# docker-compose.yml — open-webui environment
ENABLE_OAUTH_SIGNUP: "true"
OAUTH_PROVIDER_NAME: "Google"
GOOGLE_CLIENT_ID: ${GOOGLE_CLIENT_ID}
GOOGLE_CLIENT_SECRET: ${GOOGLE_CLIENT_SECRET}
```

Supports Google, Microsoft (Azure AD), and any OIDC-compatible provider.

---

## Useful Commands

```bash
# View live logs for all services
docker compose logs -f

# View logs for a specific service
docker compose logs -f litellm

# Restart a single service
docker compose restart open-webui

# Pull latest images and redeploy (data is preserved)
docker compose pull && docker compose up -d

# Stop the stack (data preserved)
docker compose down

# ⚠️  Nuclear reset — DESTROYS all volume data
docker compose down -v
```

---

## Upgrading

```bash
docker compose pull
docker compose up -d
```

Postgres and Open WebUI data live in persistent bind-mount volumes and survive upgrades. After upgrading Open WebUI, check whether the middleware patch still applies correctly (see [Middleware Patch](#middleware-patch)).

---

## Troubleshooting

**Open WebUI can't reach LiteLLM**
- Confirm both containers are on `ai-net`: `docker network inspect ai-net`
- Check LiteLLM logs: `docker compose logs litellm`
- Verify `OPENAI_API_BASE_URL=http://litellm:4000/v1` in the Open WebUI environment

**Postgres not ready / health check failures**
- Give Postgres a moment to initialize on first boot — `depends_on: condition: service_healthy` should handle this automatically
- Check logs: `docker compose logs postgres`

**Document extraction not working**
- Tika health check may have failed: `docker compose logs tika`
- Verify `TIKA_SERVER_URL=http://tika:9998` is set in the Open WebUI environment

**SearXNG not returning results**
- Check that `searxng/settings.yml` is present and mounted correctly
- Restart SearXNG: `docker compose restart searxng`

---

## Security Notes

- `.env` is gitignored — never commit secrets
- LiteLLM UI (port 4002) is exposed to the LAN in this config. If you don't need it externally, remove the `ports` entry from the `litellm` service
- Redis has no password by default (internal network only). To add auth, append `--requirepass yourpassword` to the Redis command in `docker-compose.yml`
- Community sharing is disabled (`ENABLE_COMMUNITY_SHARING=false`) to keep team data internal

---

## Roadmap

- [ ] Data analysis tooling (code interpreter or custom analysis tools)
- [ ] Open Terminal integration for AI-assisted system administration
- [ ] Iterative document editing (MCP-OPENAPI-DOCX or equivalent)
- [ ] OAuth / SSO for team onboarding
- [ ] Ollama integration for local model hosting