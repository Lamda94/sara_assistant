#!/usr/bin/env bash
# start.sh — Arranca SARA en producción
set -e
cd /opt/sara

echo "==> Construyendo imagen del backend..."
docker compose -f docker-compose.prod.yml build backend

echo "==> Levantando servicios (postgres, qdrant, ollama, nginx)..."
docker compose -f docker-compose.prod.yml up -d postgres qdrant ollama nginx

echo "==> Esperando que postgres esté listo..."
until docker compose -f docker-compose.prod.yml exec postgres pg_isready -U sara -d sara_db 2>/dev/null; do
  echo "   postgres no está listo aún, reintentando..."; sleep 3
done

echo "==> Descargando modelo de embeddings en Ollama..."
docker compose -f docker-compose.prod.yml exec ollama ollama pull nomic-embed-text

echo "==> Levantando backend..."
docker compose -f docker-compose.prod.yml up -d backend

echo "==> Esperando que el backend arranque..."
sleep 8
curl -sf http://localhost/health && echo "" && echo "✓ SARA desplegada correctamente." \
  || echo "⚠ El backend tardó más de lo esperado. Revisa: docker compose -f docker-compose.prod.yml logs backend"
