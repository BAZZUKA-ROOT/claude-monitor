#!/usr/bin/env bash
set -e

echo "=== Claude Monitor — Setup ==="

if ! command -v docker &>/dev/null; then
  echo "[1/3] Instalando Docker..."
  curl -fsSL https://get.docker.com | sh
  systemctl enable --now docker
else
  echo "[1/3] Docker já instalado."
fi

if ! command -v docker compose &>/dev/null && ! docker compose version &>/dev/null 2>&1; then
  echo "[2/3] Instalando Docker Compose plugin..."
  apt-get update -qq && apt-get install -y docker-compose-plugin
else
  echo "[2/3] Docker Compose já instalado."
fi

if [ ! -f .env ]; then
  echo "[3/3] Criando .env a partir do .env.example..."
  cp .env.example .env
  echo ""
  echo "⚠️  Edite o arquivo .env com suas credenciais antes de continuar:"
  echo "    nano .env"
  echo ""
  echo "Depois rode:  docker compose up -d"
else
  echo "[3/3] .env já existe — verificando..."
  docker compose up -d --build
  echo ""
  echo "✅ Claude Monitor rodando em http://localhost:${PORT:-5000}"
fi
