#!/usr/bin/env bash
# setup_vps.sh — Prepara la VPS de SARA desde cero (Ubuntu 24/25)
set -e

REPO="https://github.com/Lamda94/sara_assistant.git"
APP_DIR="/opt/sara"

echo "==> Actualizando sistema..."
apt-get update -qq && apt-get upgrade -y -qq

echo "==> Instalando Docker..."
apt-get install -y -qq ca-certificates curl
install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
chmod a+r /etc/apt/keyrings/docker.asc
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] \
  https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" \
  > /etc/apt/sources.list.d/docker.list
apt-get update -qq
apt-get install -y -qq docker-ce docker-ce-cli containerd.io docker-compose-plugin
usermod -aG docker ubuntu || true

echo "==> Clonando repositorio..."
mkdir -p "$APP_DIR"
if [ -d "$APP_DIR/.git" ]; then
  git -C "$APP_DIR" pull
else
  git clone "$REPO" "$APP_DIR"
fi

echo "==> Creando carpeta de secrets..."
mkdir -p "$APP_DIR/secrets"
chmod 700 "$APP_DIR/secrets"

echo ""
echo "=================================================="
echo " Setup base listo."
echo ""
echo " Pasos manuales que quedan:"
echo "  1. Copia tu .env.prod a $APP_DIR/.env.prod"
echo "  2. Copia firebase-credentials.json a $APP_DIR/secrets/"
echo "  3. Copia google-credentials.json a $APP_DIR/secrets/ (si usas Calendar/Gmail)"
echo "  4. cd $APP_DIR && bash deploy/start.sh"
echo "=================================================="
