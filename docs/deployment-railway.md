# Railway Deployment Guide

Deploy the full Unreal Objects Inc stack on Railway so that the dashboard, APIs, admin UI, and MCP server are publicly accessible. The autonomous bot agent runs locally (e.g., on a Raspberry Pi).

## Architecture

```
                              PUBLIC INTERNET
                                    |
       +----------+----------+------+------+----------+
       |          |          |             |           |
 company.*  rule-engine.*  decision-center.*   mcp.*   ui.*
 Company API  Rule Engine  Decision Center  MCP Server  Admin UI
 + Dashboard  (loads rule   (evaluates       (AI agent   (React/Vite)
              pack on       decisions)        access)
              startup)
       |          |          |             |
       +---------- RAILWAY PRIVATE NETWORK ----------+
          (services talk to each other via .railway.internal)

 LOCAL (Raspberry Pi)
 ┌──────────────────────────────────────────────────────┐
 │  worker/unreal_worker.py                              │
 │  Connects to company + decision-center public URLs    │
 └──────────────────────────────────────────────────────┘
```

| Service | Dockerfile | Port | What it exposes |
|---------|-----------|------|-----------------|
| **rule-engine** | `Dockerfile.rule-engine` | 8001 | Rule Engine API (public + internal) |
| **decision-center** | `Dockerfile.decision-center` | 8002 | Decision Center API (public + internal) |
| **company** | `Dockerfile.company` | 8010 | Company API + compiled dashboard SPA |
| **mcp** | `Dockerfile.mcp` | 8000 | MCP protocol endpoint |
| **ui** | `Dockerfile.ui` | 5173 | Unreal Objects admin UI |

**Why are Rule Engine and Decision Center separate services?** Railway only exposes one port per service. The admin UI issues browser-side requests to both, so each needs its own public domain.

## Prerequisites

- [Railway CLI](https://docs.railway.com/guides/cli) installed (`npm i -g @railway/cli`)
- Railway account with a project created
- Git repo pushed to GitHub (Railway deploys from your repo)

## Step 1: Generate Secrets

```bash
python3 -c "import secrets; [print(f'{n}={secrets.token_urlsafe(32)}') for n in ['INTERNAL_API_KEY', 'MCP_ADMIN_API_KEY']]"
```

Save the output — you'll paste these into Railway.

## Step 2: Link Your Repo

```bash
cd unreal_objects_inc
railway login
railway link
```

Select your Railway project when prompted.

## Step 3: Create Services

Create five services in the Railway dashboard. For each, set **Root Directory** to `/` and **Dockerfile Path** to the corresponding file:

| Service Name | Dockerfile Path |
|-------------|-----------------|
| `rule-engine` | `Dockerfile.rule-engine` |
| `decision-center` | `Dockerfile.decision-center` |
| `company` | `Dockerfile.company` |
| `mcp` | `Dockerfile.mcp` |
| `ui` | `Dockerfile.ui` |

Note: No "Include submodules" setting is needed — all Dockerfiles install `unreal_objects` directly from GitHub via pip.

## Step 4: Generate Public Domains

Before setting env vars, generate a public domain for **each** service in Railway's dashboard:
**Settings → Networking → Public Networking → Generate Domain**

You'll need the `rule-engine` and `decision-center` public URLs for the `ui` build-time env vars.

## Step 5: Set Environment Variables

### rule-engine

| Variable | Value |
|----------|-------|
| `INTERNAL_API_KEY` | _(from Step 1)_ |
| `ENVIRONMENT` | `production` |

### decision-center

| Variable | Value |
|----------|-------|
| `RULE_ENGINE_URL` | `http://rule-engine.railway.internal:8001` |
| `INTERNAL_API_KEY` | _(same value from Step 1)_ |
| `ENVIRONMENT` | `production` |

### company

| Variable | Value |
|----------|-------|
| `DEPLOYMENT_MODE` | `hosted` |
| `GENERATOR_MODE` | `template` |
| `ACCELERATION` | `10` |
| `RULE_ENGINE_URL` | `http://rule-engine.railway.internal:8001` |
| `DECISION_CENTER_URL` | `http://decision-center.railway.internal:8002` |
| `INTERNAL_API_KEY` | _(same value from Step 1)_ |
| `ENVIRONMENT` | `production` |

### mcp

| Variable | Value |
|----------|-------|
| `RULE_ENGINE_URL` | `http://rule-engine.railway.internal:8001` |
| `DECISION_CENTER_URL` | `http://decision-center.railway.internal:8002` |
| `INTERNAL_API_KEY` | _(same value from Step 1)_ |
| `MCP_ADMIN_API_KEY` | _(from Step 1)_ |
| `ENVIRONMENT` | `production` |
| `ALLOWED_ORIGINS` | `https://<your-company-domain>.up.railway.app` |

### ui (build-time variables — set BEFORE first deploy)

| Variable | Value |
|----------|-------|
| `VITE_RULE_ENGINE_BASE_URL` | `https://<rule-engine-domain>.up.railway.app` |
| `VITE_DECISION_CENTER_BASE_URL` | `https://<decision-center-domain>.up.railway.app` |
| `VITE_TOOL_AGENT_BASE_URL` | `https://<mcp-domain>.up.railway.app` _(optional)_ |

These are Vite build-time `ARG`s baked into the static bundle. If they are missing or wrong, the UI will compile but fail at runtime. **You must trigger a redeploy after changing them** (Railway will not auto-rebuild on env-var changes for build ARGs by default — force a redeploy).

## Step 6: Configure Health Checks

| Service | Health Check Path |
|---------|------------------|
| rule-engine | `/docs` |
| decision-center | `/v1/health` |
| company | `/v1/health` |
| mcp | TCP check on port |
| ui | TCP check on port |

## Step 7: Deploy

Push to your main branch. Railway auto-deploys on push.

```bash
git push origin main
```

## Step 8: Verify

```bash
# Rule Engine
curl https://<rule-engine-domain>.up.railway.app/docs

# Decision Center
curl https://<decision-center-domain>.up.railway.app/v1/health

# Company API
curl https://<company-domain>.up.railway.app/v1/health

# Dashboard — open in browser
open https://<company-domain>.up.railway.app

# Admin UI — open in browser
open https://<ui-domain>.up.railway.app
```

## Step 9: Run the Bot on Your Raspberry Pi

The worker is pure Python (stdlib only) — no native dependencies, runs on ARM.

```bash
# On the Pi
export COMPANY_API_URL=https://<company-domain>.up.railway.app
export DECISION_CENTER_URL=https://<decision-center-domain>.up.railway.app
export BOT_ID=deborahbot3000
export POLL_INTERVAL=5

python3 worker/unreal_worker.py
```

## Step 10: Register an MCP Agent (Optional)

If you want an AI agent to connect via MCP with authentication:

```bash
# Install the CLI (needs the unreal_objects package)
pip install git+https://github.com/BigSlikTobi/unreal_objects.git

# Register an agent
uo-agent-admin --mcp-url https://<mcp-domain>.up.railway.app \
    --admin-key <your-MCP_ADMIN_API_KEY> \
    create-agent --name "pi-bot"
```

Follow the enrollment flow to get credentials for your agent.

## Notes

### Ephemeral Storage
Railway containers reset on redeploy. Rule Engine rules and Decision Center logs are lost. The rule-engine service reloads the rule pack on startup automatically. For persistent state, consider Railway's PostgreSQL add-on in a future iteration.

### Startup Order
Railway does not guarantee service start order. The company and mcp services retry connections on their maintenance loops. If you need strict ordering, use Railway's [service dependencies](https://docs.railway.com/guides/services#service-dependencies) feature.

### Legacy Combined Backend
`Dockerfile.backend` and `entrypoint-backend.sh` describe the old 3-service architecture where Rule Engine and Decision Center ran in the same container. These files are kept as a reference but are **not used** in the current 5-service deployment.

### Cost
Railway's free tier may not cover 5 services running 24/7. Check [Railway pricing](https://railway.com/pricing) for current limits.
