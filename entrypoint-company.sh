#!/usr/bin/env bash
set -euo pipefail

# Start the company API server
# CLI options are controlled via environment variables
exec uo-company-server \
    --host 0.0.0.0 \
    --port "${PORT:-8010}" \
    --deployment-mode "${DEPLOYMENT_MODE:-hosted}" \
    --generator-mode "${GENERATOR_MODE:-template}" \
    --acceleration "${ACCELERATION:-10}" \
    --order-interval "${ORDER_INTERVAL:-60}" \
    --decision-center-url "${DECISION_CENTER_URL:-http://127.0.0.1:8002}" \
    ${CASES:+--cases "$CASES"} \
    ${PUBLIC_VOTING:+--public-voting} \
    ${OPERATOR_AUTH:+--operator-auth} \
    ${OPERATOR_TOKEN:+--operator-token "$OPERATOR_TOKEN"} \
    ${PERSISTENCE_PATH:+--persistence-path "$PERSISTENCE_PATH"} \
    ${INTERNAL_API_KEY:+--internal-api-key "$INTERNAL_API_KEY"}
