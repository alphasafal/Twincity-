#!/usr/bin/env bash
# Bind Eco-Loop live demo to twinpilot.webyaar.in via a named Cloudflare Tunnel.
# Prerequisites:
#   1) cloudflared tunnel login  (authorize the webyaar.in zone)
#   2) local proxy on :8080, API :8000, Next :3000
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
HOSTNAME="${LIVE_DEMO_HOSTNAME:-twinpilot.webyaar.in}"
TUNNEL_NAME="${LIVE_DEMO_TUNNEL_NAME:-twinpilot-live}"
CONFIG="${CLOUDFLARED_CONFIG:-$ROOT/infrastructure/cloudflare/twinpilot-live.yml}"
CERT="${TUNNEL_ORIGIN_CERT:-$HOME/.cloudflared/cert.pem}"
CRED_DIR="${HOME}/.cloudflared"
PROXY_URL="${PROXY_URL:-http://127.0.0.1:8080}"

if [[ ! -f "$CERT" ]]; then
  echo "ERROR: missing $CERT"
  echo "Run: cloudflared tunnel login"
  echo "Authorize the Cloudflare account that owns webyaar.in, then re-run this script."
  exit 1
fi

mkdir -p "$CRED_DIR" "$(dirname "$CONFIG")"

# Create tunnel if needed
if ! cloudflared tunnel list 2>/dev/null | grep -q "$TUNNEL_NAME"; then
  echo "==> Creating tunnel $TUNNEL_NAME"
  cloudflared tunnel create "$TUNNEL_NAME"
else
  echo "==> Tunnel $TUNNEL_NAME already exists"
fi

# Resolve credentials JSON (UUID-named file)
CRED_JSON="$(ls "$CRED_DIR"/*.json 2>/dev/null | head -1 || true)"
if [[ -z "$CRED_JSON" ]]; then
  echo "ERROR: no tunnel credentials JSON under $CRED_DIR"
  exit 1
fi
# Prefer exact name symlink/copy
if [[ ! -f "$CRED_DIR/${TUNNEL_NAME}.json" ]]; then
  # cloudflared creates <uuid>.json — copy/symlink for config convenience
  cp -f "$CRED_JSON" "$CRED_DIR/${TUNNEL_NAME}.json"
fi

# Write config with absolute credentials path
cat > "$CONFIG" <<EOF
tunnel: ${TUNNEL_NAME}
credentials-file: ${CRED_DIR}/${TUNNEL_NAME}.json

ingress:
  - hostname: ${HOSTNAME}
    service: ${PROXY_URL}
    originRequest:
      noTLSVerify: true
      disableChunkedEncoding: true
  - service: http_status:404
EOF

echo "==> Routing DNS ${HOSTNAME} → tunnel ${TUNNEL_NAME}"
cloudflared tunnel route dns "$TUNNEL_NAME" "$HOSTNAME" || true

echo "==> Updating apps/web/.env.local"
printf 'NEXT_PUBLIC_API_URL=https://%s\n' "$HOSTNAME" > "$ROOT/apps/web/.env.local"

echo "==> Restarting named tunnel (tmux session cf-named)"
tmux -f /exec-daemon/tmux.portal.conf kill-session -t cf-named 2>/dev/null || true
# stop quick tunnels so they don't confuse demos
pkill -f 'cloudflared tunnel --url' 2>/dev/null || true
SESSION_NAME="cf-named"
tmux -f /exec-daemon/tmux.portal.conf new-session -d -s "$SESSION_NAME" -c "$ROOT" -- bash -l
tmux -f /exec-daemon/tmux.portal.conf send-keys -t "$SESSION_NAME:0.0" \
  "cloudflared tunnel --config '$CONFIG' run '$TUNNEL_NAME' 2>&1 | tee /tmp/cf-named.log" C-m

# Restart Next so NEXT_PUBLIC_API_URL is picked up
if tmux -f /exec-daemon/tmux.portal.conf has-session -t "=tp-web" 2>/dev/null; then
  tmux -f /exec-daemon/tmux.portal.conf send-keys -t "tp-web:0.0" C-c
  sleep 1
  tmux -f /exec-daemon/tmux.portal.conf send-keys -t "tp-web:0.0" \
    "cd '$ROOT/apps/web' && pnpm exec next dev --hostname 0.0.0.0 --port 3000" C-m
fi

echo
echo "Live demo target: https://${HOSTNAME}"
echo "Waiting for DNS/tunnel (may take 1–2 minutes)…"
for i in $(seq 1 30); do
  code=$(curl -s -o /dev/null -m 8 -w '%{http_code}' "https://${HOSTNAME}/" || true)
  if [[ "$code" == "200" ]]; then
    echo "OK https://${HOSTNAME}/ → $code"
    exit 0
  fi
  echo "  try $i: HTTP $code"
  sleep 5
done
echo "Tunnel started but public HTTPS not 200 yet. Check /tmp/cf-named.log and Cloudflare DNS."
exit 0
