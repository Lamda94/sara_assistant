#!/bin/bash
# ── SARA — Script de inicio completo ──────────────

SARA_DIR="$(cd "$(dirname "$0")" && pwd)"
GREEN='\033[0;32m'
DIM='\033[2m'
NC='\033[0m'

log() { echo -e "${GREEN}✓${NC} $1"; }
dim() { echo -e "${DIM}  $1${NC}"; }

echo ""
echo "  S A R A — Iniciando stack..."
echo ""

# 1. Docker (Qdrant)
log "Levantando Qdrant..."
cd "$SARA_DIR" && docker compose up -d --quiet-pull 2>/dev/null
dim "Qdrant en localhost:6333"

# 2. Backend
log "Iniciando backend..."
cd "$SARA_DIR/backend"
source venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8000 > /tmp/sara_backend.log 2>&1 &
sleep 3
dim "Backend en localhost:8000"

# 3. Túnel Cloudflare
log "Iniciando túnel Cloudflare..."
cloudflared tunnel run sara-api > /tmp/sara_tunnel.log 2>&1 &
sleep 3
dim "API pública en https://api.luismendezdev.online"

# 4. App Web
log "Iniciando app web..."
cd "$SARA_DIR/clients/web"
npm run dev > /tmp/sara_web.log 2>&1 &
sleep 3
dim "Web en localhost:3000"

echo ""
echo "  Stack completo ✓"
echo ""
echo "  Backend local:  http://localhost:8000"
echo "  Backend público: https://api.luismendezdev.online"
echo "  Web:            http://localhost:3000"
echo "  Docs API:       http://localhost:8000/docs"
echo ""
