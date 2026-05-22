#!/bin/bash
set -euo pipefail
exec > /var/log/user_data.log 2>&1

# ── System update ─────────────────────────────────────────────────────────────
apt-get update -y
apt-get upgrade -y

# ── Docker install (official apt repo) ────────────────────────────────────────
apt-get install -y ca-certificates curl gnupg

install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg \
  | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
chmod a+r /etc/apt/keyrings/docker.gpg

echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
  https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo "$VERSION_CODENAME") stable" \
  > /etc/apt/sources.list.d/docker.list

apt-get update -y
apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

systemctl enable docker
systemctl start docker
usermod -aG docker ubuntu

# ── AWS CLI v2 ────────────────────────────────────────────────────────────────
apt-get install -y unzip
curl -fsSL "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o /tmp/awscli.zip
unzip -q /tmp/awscli.zip -d /tmp/awscli-install
/tmp/awscli-install/aws/install
rm -rf /tmp/awscli.zip /tmp/awscli-install

# ── Data volume (EBS → /data/postgres) ───────────────────────────────────────
# Nitro instances expose EBS attachments as NVMe; check both device names.
DATA_DEV=""
for candidate in /dev/nvme1n1 /dev/xvdf; do
  if [ -b "$candidate" ]; then
    DATA_DEV="$candidate"
    break
  fi
done

if [ -z "$DATA_DEV" ]; then
  echo "ERROR: data EBS volume not found at /dev/nvme1n1 or /dev/xvdf" >&2
  exit 1
fi

# Format only if the device has no existing filesystem.
if ! blkid "$DATA_DEV" > /dev/null 2>&1; then
  mkfs.ext4 "$DATA_DEV"
fi

mkdir -p /data/postgres
mount "$DATA_DEV" /data/postgres

# Idempotent fstab entry.
if ! grep -q "$DATA_DEV" /etc/fstab; then
  echo "$DATA_DEV /data/postgres ext4 defaults,nofail 0 2" >> /etc/fstab
fi

# PostgreSQL container runs as UID 999.
chown -R 999:999 /data/postgres

# ── App directory ─────────────────────────────────────────────────────────────
mkdir -p /opt/survivorpool

cat > /opt/survivorpool/README <<'EOF'
SurvivorPool deployment directory
----------------------------------
First deploy:
  1. Copy files from your local machine:
       ./deploy.sh /path/to/your-key.pem
  2. Or manually:
       scp -i key.pem .env docker-compose.yml scoring_config.json ubuntu@<ip>:/opt/survivorpool/
       ssh ubuntu@<ip> 'cd /opt/survivorpool && docker compose up --build -d'

Subsequent deploys:
  ./deploy.sh /path/to/your-key.pem
EOF

chown -R ubuntu:ubuntu /opt/survivorpool

# ── Daily PostgreSQL backup to S3 ────────────────────────────────────────────
cat > /usr/local/bin/pg_backup.sh <<'SCRIPT'
#!/bin/bash
set -euo pipefail
DATE=$(date +%Y-%m-%d)
BUCKET="${backup_bucket}"
docker exec db pg_dump -U survivorpool survivorpool \
  | gzip \
  | aws s3 cp - "s3://$BUCKET/pg_backup_$DATE.sql.gz"
echo "Backup completed: pg_backup_$DATE.sql.gz"
SCRIPT

chmod +x /usr/local/bin/pg_backup.sh

# Run at 03:00 UTC daily — well after the 21:05 Pacific scoring cron.
cat > /etc/cron.d/survivorpool-backup <<'EOF'
0 3 * * * root /usr/local/bin/pg_backup.sh >> /var/log/pg_backup.log 2>&1
EOF

echo "user_data.sh completed successfully"
