#!/usr/bin/env bash
# Start the full public live demo stack for https://twinpilot.webyaar.in
# Requires: cloudflared installed + ~/.cloudflared/cert.pem (from `cloudflared tunnel login`)
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
if [[ -f /exec-daemon/tmux.portal.conf ]]; then
  TMUX=(tmux -f /exec-daemon/tmux.portal.conf)
else
  TMUX=(tmux)
fi
CFG="$ROOT/infrastructure/cloudflare/twinpilot-live.yml"
HOSTNAME="${LIVE_DEMO_HOSTNAME:-twinpilot.webyaar.in}"

ensure_session() {
  local name="$1" cmd="$2"
  if "${TMUX[@]}" has-session -t "=$name" 2>/dev/null; then
    echo "tmux session $name already exists"
  else
    "${TMUX[@]}" new-session -d -s "$name" -c "$ROOT" -- bash -l
    "${TMUX[@]}" send-keys -t "$name:0.0" "$cmd" C-m
    echo "started $name"
  fi
}

restart_session() {
  local name="$1" cmd="$2"
  "${TMUX[@]}" kill-session -t "$name" 2>/dev/null || true
  ensure_session "$name" "$cmd"
}

# API
if ! curl -sf --max-time 5 http://127.0.0.1:8000/health >/dev/null 2>&1; then
  restart_session "tp-api" "set -a; source '$ROOT/.env'; set +a; source '$ROOT/.venv/bin/activate' && cd '$ROOT/services/api' && uvicorn app.main:app --host 0.0.0.0 --port 8000"
fi

# Web — public API URL for browser calls through the tunnel hostname
printf 'NEXT_PUBLIC_API_URL=https://%s\n' "$HOSTNAME" > "$ROOT/apps/web/.env.local"
if ! curl -sf --max-time 5 http://127.0.0.1:3000/login >/dev/null 2>&1; then
  restart_session "tp-web" "cd '$ROOT' && pnpm --filter @twinpilot/web exec next dev --hostname 0.0.0.0 --port 3000"
else
  echo "web already up"
fi

# Reverse proxy :8080
if ! curl -sf --max-time 5 http://127.0.0.1:8080/login >/dev/null 2>&1; then
  pkill -f 'live_demo_proxy.py' 2>/dev/null || true
  restart_session "tp-proxy" "python3 '$ROOT/scripts/live_demo_proxy.py' 2>&1 | tee /tmp/tp-proxy.log"
fi

# Named Cloudflare tunnel
if [[ ! -f "$HOME/.cloudflared/cert.pem" ]]; then
  echo "ERROR: missing ~/.cloudflared/cert.pem"
  echo "Run: cloudflared tunnel login"
  echo "Authorize the account that owns webyaar.in, then re-run this script."
  exit 1
fi

mkdir -p "$HOME/.cloudflared" "$(dirname "$CFG")"
if ! cloudflared tunnel list 2>/dev/null | grep -q 'twinpilot-live'; then
  cloudflared tunnel create twinpilot-live || true
fi
CRED_JSON="$(ls "$HOME"/.cloudflared/*.json 2>/dev/null | head -1 || true)"
if [[ -z "$CRED_JSON" ]]; then
  echo "ERROR: no tunnel credentials JSON in ~/.cloudflared"
  exit 1
fi
cp -f "$CRED_JSON" "$HOME/.cloudflared/twinpilot-live.json"
TUNNEL_ID="$(basename "$CRED_JSON" .json)"
if [[ "$TUNNEL_ID" =~ ^[0-9a-f-]{36}$ ]]; then
  TUNNEL_REF="$TUNNEL_ID"
else
  TUNNEL_REF="twinpilot-live"
fi

cat > "$CFG" <<EOF
tunnel: ${TUNNEL_REF}
credentials-file: ${HOME}/.cloudflared/twinpilot-live.json

ingress:
  - hostname: ${HOSTNAME}
    service: http://127.0.0.1:8080
    originRequest:
      noTLSVerify: true
      disableChunkedEncoding: true
  - service: http_status:404
EOF

cloudflared tunnel route dns --overwrite-dns "$TUNNEL_REF" "$HOSTNAME" 2>/dev/null || \
  cloudflared tunnel route dns --overwrite-dns twinpilot-live "$HOSTNAME" 2>/dev/null || true

pkill -f 'cloudflared tunnel --url' 2>/dev/null || true
if ! pgrep -f 'cloudflared tunnel --config' >/dev/null 2>&1; then
  "${TMUX[@]}" kill-session -t cf-named 2>/dev/null || true
  restart_session "cf-named" "cloudflared tunnel --config '$CFG' run 2>&1 | tee /tmp/cf-named.log"
else
  echo "tunnel already running"
fi

echo "Waiting for https://${HOSTNAME}/login …"
for i in $(seq 1 36); do
  code=$(curl -s -o /dev/null -m 10 -w '%{http_code}' "https://${HOSTNAME}/login" || true)
  if [[ "$code" == "200" || "$code" == "307" || "$code" == "308" || "$code" == "302" ]]; then
    echo "OK https://${HOSTNAME}/login → $code"
    exit 0
  fi
  echo "  try $i: HTTP $code"
  sleep 5
done
echo "Started stack but public HTTPS not ready yet. Check /tmp/cf-named.log"
exit 1
