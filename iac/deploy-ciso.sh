#!/bin/bash
# ==============================================================================
# Script: deploy-ciso.sh
# Purpose: Automated installation of Docker and CISO Assistant on Ubuntu VPS.
# This script represents the "Community Version" bootstrap.
# ==============================================================================

set -e

echo "=== [1/4] Systemaktualisierung & Installation von Voraussetzungen ==="
sudo apt-get update
sudo apt-get upgrade -y
sudo apt-get install -y docker.io docker-compose-v2 git curl

echo "=== [2/4] Docker-Berechtigungen einrichten ==="
sudo systemctl enable docker
sudo systemctl start docker
sudo usermod -aG docker $USER

echo "=== [3/4] CISO Assistant herunterladen ==="
if [ ! -d "$HOME/ciso-assistant" ]; then
    git clone https://github.com/intuitem/ciso-assistant-community.git "$HOME/ciso-assistant"
else
    echo "CISO Assistant Verzeichnis existiert bereits. Überspringe Klonen."
fi

echo "=== [4/4] Installation abgeschlossen ==="
echo "Bitte logge dich einmal aus und wieder ein, um die Docker-Rechte zu aktivieren."
echo "Danach kannst du die GRC-Plattform mit folgenden Befehlen starten:"
echo "  cd ~/ciso-assistant"
echo "  ./docker-compose.sh"
echo "======================================================================"
