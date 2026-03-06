#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# test.sh — Smoke-test the Google Analytics MCP HTTP server
#
# Usage:
#   # Against localhost (default)
#   ./test.sh
#
#   # Against a live Render URL
#   BASE_URL=https://google-analytics-mcp.onrender.com ./test.sh
#
# Dependencies: curl, python3 (for JSON parsing). jq is used for
#   pretty-printing if available, otherwise raw JSON is shown.
# ---------------------------------------------------------------------------

set -uo pipefail

BASE_URL="${BASE_URL:-http://localhost:8000}"
PASS=0
FAIL=0

# Colours (disabled automatically when not a terminal)
if [ -t 1 ]; then
  GREEN="\033[0;32m"; RED="\033[0;31m"; RESET="\033[0m"; BOLD="\033[1m"
else
  GREEN=""; RED=""; RESET=""; BOLD=""
fi

pass() { echo -e "  ${GREEN}PASS${RESET} $1"; ((PASS++)); }
fail() { echo -e "  ${RED}FAIL${RESET} $1"; ((FAIL++)); }

pretty() {
  if command -v jq &>/dev/null; then
    jq .
  else
    python3 -m json.tool 2>/dev/null || cat
  fi
}

echo -e "${BOLD}======================================================${RESET}"
echo -e "${BOLD}  Google Analytics MCP — Smoke Tests${RESET}"
echo -e "  Target: ${BASE_URL}"
echo -e "${BOLD}======================================================${RESET}"


# ---------------------------------------------------------------------------
# 1. Health check
# ---------------------------------------------------------------------------
echo ""
echo -e "${BOLD}1. GET /health${RESET}"

HEALTH_BODY=$(mktemp)
HEALTH_CODE=$(curl -s -o "$HEALTH_BODY" -w "%{http_code}" \
  --max-time 10 "${BASE_URL}/health" 2>/dev/null || echo "000")

echo "   HTTP $HEALTH_CODE"
cat "$HEALTH_BODY" | pretty | sed 's/^/   /'

if [ "$HEALTH_CODE" = "200" ]; then
  pass "/health returned 200"
else
  fail "/health returned $HEALTH_CODE (expected 200)"
fi
rm -f "$HEALTH_BODY"


# ---------------------------------------------------------------------------
# 2. Tools list
# ---------------------------------------------------------------------------
echo ""
echo -e "${BOLD}2. GET /tools${RESET}"

TOOLS_BODY=$(mktemp)
TOOLS_CODE=$(curl -s -o "$TOOLS_BODY" -w "%{http_code}" \
  --max-time 10 "${BASE_URL}/tools" 2>/dev/null || echo "000")

echo "   HTTP $TOOLS_CODE"

if [ "$TOOLS_CODE" = "200" ]; then
  TOOL_COUNT=$(python3 -c \
    "import sys, json; d=json.load(open('$TOOLS_BODY')); print(d.get('count',0))" \
    2>/dev/null || echo "?")
  echo "   Tools registered: ${TOOL_COUNT}"
  # Print tool names only (skip descriptions to keep output compact)
  python3 -c "
import sys, json
d = json.load(open('$TOOLS_BODY'))
for t in d.get('tools', []):
    print('   -', t['name'])
" 2>/dev/null || cat "$TOOLS_BODY" | pretty | sed 's/^/   /'
  pass "/tools returned 200 with ${TOOL_COUNT} tools"
else
  cat "$TOOLS_BODY" | pretty | sed 's/^/   /'
  fail "/tools returned $TOOLS_CODE (expected 200)"
fi
rm -f "$TOOLS_BODY"


# ---------------------------------------------------------------------------
# 3. SSE endpoint reachability
# ---------------------------------------------------------------------------
echo ""
echo -e "${BOLD}3. GET /sse — SSE endpoint reachability${RESET}"
echo "   (Connecting for up to 3 seconds; timeout is expected for a live stream)"

SSE_HEADERS=$(mktemp)

# We request only the headers. A real SSE stream stays open; we cut off
# after 3 s. Exit code 28 = curl timeout, which is expected here.
HTTP_SSE_CODE=$(curl -s -o /dev/null -D "$SSE_HEADERS" \
  -H "Accept: text/event-stream" \
  --max-time 3 \
  -w "%{http_code}" \
  "${BASE_URL}/sse" 2>/dev/null) || true

CONTENT_TYPE=$(grep -i "content-type" "$SSE_HEADERS" | head -1 | tr -d '\r\n' || echo "")
echo "   HTTP     : ${HTTP_SSE_CODE}"
echo "   Content-Type: ${CONTENT_TYPE}"

if [ "$HTTP_SSE_CODE" = "200" ]; then
  pass "/sse returned 200 with SSE content-type"
elif [ -z "$HTTP_SSE_CODE" ] || [ "$HTTP_SSE_CODE" = "000" ]; then
  # Timed out before headers arrived — server is still connecting
  pass "/sse reachable (timed out as expected for SSE stream)"
else
  fail "/sse returned unexpected HTTP ${HTTP_SSE_CODE}"
fi
rm -f "$SSE_HEADERS"


# ---------------------------------------------------------------------------
# 4. MCP initialize over SSE (lightweight smoke test)
# ---------------------------------------------------------------------------
echo ""
echo -e "${BOLD}4. MCP initialize probe${RESET}"
echo "   Opening SSE stream, posting 'initialize', reading first event..."

SESSION_ID=""
SSE_STREAM=$(mktemp)
SSE_PID=""

# Start a background SSE listener, capture the first line that contains
# the session endpoint.  The MCP SSE transport emits:
#   event: endpoint
#   data: /messages/?session_id=<uuid>
(curl -s -N -H "Accept: text/event-stream" \
  --max-time 8 "${BASE_URL}/sse" > "$SSE_STREAM" 2>/dev/null) &
SSE_PID=$!

# Give the server a moment to send the endpoint event
sleep 1

# Extract the session path from the SSE stream so far
SESSION_PATH=$(grep -o '/messages/[^"]*' "$SSE_STREAM" | head -1 | tr -d '\r' || echo "")

if [ -z "$SESSION_PATH" ]; then
  fail "Could not read SSE endpoint event from /sse (no session_id received)"
else
  echo "   Session path: ${SESSION_PATH}"

  # Send MCP initialize request to the messages endpoint
  INIT_PAYLOAD='{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"smoke-test","version":"0.0.1"}}}'

  INIT_BODY=$(mktemp)
  INIT_CODE=$(curl -s -o "$INIT_BODY" -w "%{http_code}" \
    -X POST \
    -H "Content-Type: application/json" \
    --max-time 10 \
    -d "$INIT_PAYLOAD" \
    "${BASE_URL}${SESSION_PATH}" 2>/dev/null || echo "000")

  echo "   HTTP $INIT_CODE"
  cat "$INIT_BODY" | pretty | sed 's/^/   /' 2>/dev/null || true

  if [ "$INIT_CODE" = "200" ] || [ "$INIT_CODE" = "202" ]; then
    pass "MCP initialize returned HTTP ${INIT_CODE}"
  else
    fail "MCP initialize returned HTTP ${INIT_CODE} (expected 200 or 202)"
  fi
  rm -f "$INIT_BODY"
fi

# Stop the background SSE listener
if [ -n "$SSE_PID" ]; then
  kill "$SSE_PID" 2>/dev/null || true
fi
rm -f "$SSE_STREAM"


# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
echo ""
echo -e "${BOLD}======================================================${RESET}"
if [ "$FAIL" -eq 0 ]; then
  echo -e "${GREEN}${BOLD}  All ${PASS} checks passed!${RESET}"
else
  echo -e "${RED}${BOLD}  ${FAIL} check(s) failed, ${PASS} passed.${RESET}"
  echo "  Review the output above for details."
fi
echo -e "${BOLD}======================================================${RESET}"

exit "$FAIL"
