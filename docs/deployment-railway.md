# Railway Deployment Guide

Deploy the full Unreal Objects Inc stack on Railway so that the dashboard, APIs, and MCP server are publicly accessible. The autonomous bot agent runs locally (e.g., on a Raspberry Pi).

## Architecture

```
                         PUBLIC INTERNET
                              |
         +--------------------+--------------------+
         |                    |                    |
 company.railway.app  backend.railway.app  mcp.railway.app
 Company API+Dashboard  Decision Center      MCP Server
         |                    |                    |
         +-------- RAILWAY PRIVATE NETWORK --------+
                backend.railway.internal:8001
                    (Rule Engine, internal)

 LOCAL (Raspberry Pi)
 ┌──────────────────────────────────────────────┐
 │  worker/unreal_worker.py                      │
 │  Connects to company + backend public URLs    │
 └──────────────────────────────────────────────┘
```

| Service | Dockerfile | Public? | What it exposes |
|---------|-----------|---------|-----------------|
| **backend** | `Dockerfile.backend` | Yes (port 8002) | Decision Center API |
| **company** | `Dockerfile.company` | Yes (port 8010) | Company API + Dashboard |
| **mcp** | `Dockerfile.mcp` | Yes (port 8000) | MCP protocol endpoint |

Rule Engine runs on port 8001 inside the backend container but is only reachable via Railway's private network — other services call it at `http://backend.railway.internal:8001`.

## Prerequisites

- [Railway CLI](https://docs.railway.com/guides/cli) installed (`npm i -g @railway/cli`)
- Railway account with a project created
- Git repo pushed to GitHub (Railway deploys from your repo)

## Step 1: Generate Secrets

Run locally to generate the shared secrets:

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

Create three services in the Railway dashboard (or via CLI). For each, set the **Root Directory** to `/` and the **Dockerfile Path** to the corresponding file:

| Service Name | Dockerfile Path |
|-------------|-----------------|
| `backend` | `Dockerfile.backend` |
| `company` | `Dockerfile.company` |
| `mcp` | `Dockerfile.mcp` |

**Important:** Enable "Include submodules" in the service's source settings so that `unreal_objects/` is cloned.

## Step 4: Set Environment Variables

### backend

| Variable | Value |
|----------|-------|
| `PORT` | `8002` |
| `INTERNAL_API_KEY` | _(from Step 1)_ |
| `ENVIRONMENT` | `production` |

### company

| Variable | Value |
|----------|-------|
| `PORT` | `8010` |
| `DEPLOYMENT_MODE` | `hosted` |
| `GENERATOR_MODE` | `template` |
| `ACCELERATION` | `10` |
| `RULE_ENGINE_URL` | `http://backend.railway.internal:8001` |
| `DECISION_CENTER_URL` | `http://backend.railway.internal:8002` |
| `INTERNAL_API_KEY` | _(same value from Step 1)_ |
| `ENVIRONMENT` | `production` |

### mcp

| Variable | Value |
|----------|-------|
| `PORT` | `8000` |
| `RULE_ENGINE_URL` | `http://backend.railway.internal:8001` |
| `DECISION_CENTER_URL` | `http://backend.railway.internal:8002` |
| `INTERNAL_API_KEY` | _(same value from Step 1)_ |
| `MCP_ADMIN_API_KEY` | _(from Step 1)_ |
| `ENVIRONMENT` | `production` |
| `ALLOWED_ORIGINS` | `https://<your-company-domain>.up.railway.app` |

Replace `backend` in the internal URLs with whatever you named the backend service in Railway.

## Step 5: Generate Public Domains

In the Railway dashboard, go to each service's **Settings → Networking → Public Networking** and generate a domain. You'll get URLs like:

- `https://backend-production-XXXX.up.railway.app` (Decision Center)
- `https://company-production-XXXX.up.railway.app` (Company API + Dashboard)
- `https://mcp-production-XXXX.up.railway.app` (MCP Server)

## Step 6: Configure Health Checks

| Service | Health Check Path |
|---------|------------------|
| backend | `/v1/health` |
| company | `/v1/health` |
| mcp | TCP check on port |

## Step 7: Deploy

Push to your main branch. Railway auto-deploys on push.

```bash
git push origin main
```

## Step 8: Verify

```bash
# Decision Center
curl https://backend-production-XXXX.up.railway.app/v1/health

# Company API
curl https://company-production-XXXX.up.railway.app/v1/health

# Dashboard — open in browser
open https://company-production-XXXX.up.railway.app
```

## Step 9: Run the Bot on Your Raspberry Pi

The worker is pure Python (stdlib only) — no native dependencies, runs on ARM.

```bash
# On the Pi
export COMPANY_API_URL=https://company-production-XXXX.up.railway.app
export DECISION_CENTER_URL=https://backend-production-XXXX.up.railway.app
export BOT_ID=deborahbot3000
export POLL_INTERVAL=5

python3 worker/unreal_worker.py
```

## Step 10: Register an MCP Agent (Optional)

If you want an AI agent to connect via MCP with authentication:

```bash
# Install the CLI (needs the unreal_objects package)
pip install -e ./unreal_objects

# Register an agent
uo-agent-admin --mcp-url https://mcp-production-XXXX.up.railway.app \
    --admin-key <your-MCP_ADMIN_API_KEY> \
    create-agent --name "pi-bot"
```

Follow the enrollment flow to get credentials for your agent.

## Notes

### Ephemeral Storage
Railway containers reset on redeploy. Rule Engine rules and Decision Center logs are lost. The company server reloads the rule pack on startup, so rules are restored automatically. For persistent state, consider Railway's PostgreSQL add-on in a future iteration.

### Startup Order
The backend service should start before company and mcp. Railway doesn't guarantee ordering, but:
- The company server retries rule loading on its maintenance loop
- The MCP server returns errors if backends are unreachable (agents can retry)

If you need strict ordering, use Railway's [service dependencies](https://docs.railway.com/guides/services#service-dependencies) feature.

### Cost
Railway's free tier may not cover 3 services running 24/7. Check [Railway pricing](https://railway.com/pricing) for current limits.
