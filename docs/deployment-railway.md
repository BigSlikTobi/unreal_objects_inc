# Railway Deployment Guide

The Unreal Objects Inc stack splits across two Railway projects:

- **`unreal_objects` project** — Rule Engine, Decision Center, MCP, UI. Deployed directly from the [unreal_objects](https://github.com/BigSlikTobi/unreal_objects) repo. See its own deployment guide.
- **`unreal_objects_inc` project** — Company API + Dashboard. This guide covers that service.

## Architecture

```
  unreal_objects project (separate Railway project)
  ┌────────────────────────────────────────────────┐
  │  rule-engine.*          decision-center.*       │
  │  ruleengine-production-d6fe.up.railway.app      │
  │  decisioncenter-production-1c81.up.railway.app  │
  └────────────────────────────────────────────────┘
                        ↑ HTTPS
  unreal_objects_inc project
  ┌────────────────────────────────────────────────┐
  │  company.*                                      │
  │  unrealobjectsinc-production.up.railway.app     │
  │  Company API + Dashboard (Dockerfile.company)   │
  └────────────────────────────────────────────────┘

  LOCAL (Raspberry Pi)
  ┌──────────────────────────────────────────────────────┐
  │  worker/unreal_worker.py                              │
  │  Connects to company + decision-center public URLs    │
  └──────────────────────────────────────────────────────┘
```

## Prerequisites

- [Railway CLI](https://docs.railway.com/guides/cli) installed (`npm i -g @railway/cli`)
- Railway account with the `athletic-spirit` project
- Git repo pushed to GitHub

## Step 1: Create the company service

In the Railway dashboard, create one service:

| Service Name | Dockerfile | Port |
|-------------|------------|------|
| `company` | `Dockerfile.company` | 8010 |

## Step 2: Set Environment Variables

| Variable | Value |
|----------|-------|
| `DEPLOYMENT_MODE` | `hosted` |
| `GENERATOR_MODE` | `template` |
| `ACCELERATION` | `10` |
| `RULE_ENGINE_URL` | `https://ruleengine-production-d6fe.up.railway.app` |
| `DECISION_CENTER_URL` | `https://decisioncenter-production-1c81.up.railway.app` |
| `INTERNAL_API_KEY` | _(same shared secret used in the unreal_objects project)_ |
| `ENVIRONMENT` | `production` |

> `INTERNAL_API_KEY` must match the value set on the Rule Engine and Decision Center in the unreal_objects project — it's used for service-to-service auth on mutating requests.

## Step 3: Deploy

```bash
git push origin main
```

Railway auto-deploys on push.

## Step 4: Verify

```bash
# Company API health
curl https://unrealobjectsinc-production.up.railway.app/health

# Dashboard — open in browser
open https://unrealobjectsinc-production.up.railway.app
```

## Step 5: Run the Bot on Your Raspberry Pi

```bash
export COMPANY_API_URL=https://unrealobjectsinc-production.up.railway.app
export DECISION_CENTER_URL=https://decisioncenter-production-1c81.up.railway.app
export BOT_ID=deborahbot3000
export POLL_INTERVAL=5

python3 worker/unreal_worker.py
```

## Notes

### Rule Engine and Decision Center URLs

If the unreal_objects services are redeployed with new domains, update `RULE_ENGINE_URL` and `DECISION_CENTER_URL` on the company service and trigger a redeploy.

### Cost

A single Railway service is well within the free tier limits.
