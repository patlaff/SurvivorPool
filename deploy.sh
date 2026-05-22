#!/bin/bash
set -euo pipefail

KEY=${1:?Usage: ./deploy.sh path/to/key.pem}

IP=$(cd "$(dirname "$0")/infra" && terraform output -raw instance_public_ip)

echo "Deploying to $IP ..."

SSH_OPTS="-i $KEY -o StrictHostKeyChecking=accept-new"
DEST="ubuntu@$IP:/opt/survivorpool/"

scp $SSH_OPTS \
  .env \
  docker-compose.yml \
  scoring_config.json \
  "$DEST"

ssh $SSH_OPTS "ubuntu@$IP" \
  'cd /opt/survivorpool && docker compose up --build -d'

echo "Deploy complete. App running at http://$IP"
