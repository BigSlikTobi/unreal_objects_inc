#!/usr/bin/env bash
set -euo pipefail

# Start the MCP Server with streamable-http transport.
# Auth is enabled automatically when MCP_ADMIN_API_KEY is set.
exec python -m mcp_server.server \
    --transport streamable-http \
    --host 0.0.0.0 \
    --port "${PORT:-8000}" \
    ${MCP_ADMIN_API_KEY:+--auth-enabled --admin-api-key "$MCP_ADMIN_API_KEY"} \
    ${MCP_GROUP_ID:+--group-id "$MCP_GROUP_ID"}
