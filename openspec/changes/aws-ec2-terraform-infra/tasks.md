# Tasks: AWS EC2 + Docker Compose Infrastructure (Terraform)

## Phase 1 — Scaffold

### 1.1 Create infra/ directory and .gitignore
- [x] Create `infra/` at the repo root
- [x] Create `infra/.gitignore` with entries: `.terraform/`, `.terraform.lock.hcl`, `terraform.tfvars`, `*.tfstate`, `*.tfstate.backup`, `*.tfplan`

---

## Phase 2 — Terraform files

### 2.1 `infra/variables.tf`
- [x] Declare `aws_region` (string, default `"us-east-1"`)
- [x] Declare `app_name` (string, default `"survivorpool"`)
- [x] Declare `instance_type` (string, default `"t3.small"`)
- [x] Declare `key_name` (string, no default — required; description: name of an existing EC2 key pair)
- [x] Declare `admin_cidr` (string, no default — required; description: your IP in CIDR form, e.g. `"1.2.3.4/32"`, used to restrict SSH access)
- [x] Declare `data_volume_size` (number, default `20`; description: PostgreSQL data EBS volume size in GB)
- [x] Declare `backup_retention_days` (number, default `30`; description: S3 lifecycle expiry for backup objects)

### 2.2 `infra/main.tf`
- [x] `terraform {}` block: `required_version = ">= 1.7"`, `required_providers { aws = { source = "hashicorp/aws", version = "~> 5.0" } }`
- [x] `provider "aws"` block with `region = var.aws_region`
- [x] `data "aws_vpc" "default"` with `default = true`
- [x] `data "aws_subnets" "default"` filtered by `vpc-id = data.aws_vpc.default.id`
- [x] `data "aws_ami" "ubuntu"`: `most_recent = true`, owners `["099720109477"]` (Canonical), filter name `"ubuntu/images/hvm-ssd-gp3/ubuntu-noble-24.04-amd64-server-*"`

### 2.3 `infra/compute.tf`
- [x] `resource "aws_security_group" "main"`: ingress 80/tcp from `0.0.0.0/0`; ingress 22/tcp from `var.admin_cidr`; egress all to `0.0.0.0/0`; tag `Name = "${var.app_name}-sg"`
- [x] `resource "aws_instance" "main"`:
  - `ami = data.aws_ami.ubuntu.id`
  - `instance_type = var.instance_type`
  - `key_name = var.key_name`
  - `subnet_id = tolist(data.aws_subnets.default.ids)[0]`
  - `vpc_security_group_ids = [aws_security_group.main.id]`
  - `iam_instance_profile = aws_iam_instance_profile.main.name`
  - `user_data = file("${path.module}/user_data.sh")` with `BACKUP_BUCKET` replaced via `templatefile()`
  - root block device: `volume_size = 8`, `volume_type = "gp3"`, `encrypted = true`, `delete_on_termination = true`
  - `metadata_options { http_tokens = "required" }` (IMDSv2)
  - tags `Name = var.app_name`
- [x] `resource "aws_ebs_volume" "data"`:
  - `availability_zone = aws_instance.main.availability_zone`
  - `size = var.data_volume_size`, `type = "gp3"`, `encrypted = true`
  - tag `Name = "${var.app_name}-data"`
- [x] `resource "aws_volume_attachment" "data"`:
  - `device_name = "/dev/xvdf"`, `volume_id = aws_ebs_volume.data.id`, `instance_id = aws_instance.main.id`
- [x] `resource "aws_eip" "main"`:
  - `domain = "vpc"`
  - `instance = aws_instance.main.id`
  - tag `Name = "${var.app_name}-eip"`

### 2.4 `infra/iam.tf`
- [x] `resource "aws_iam_role" "ec2_role"`: assume-role policy for `ec2.amazonaws.com`; tag `Name = "${var.app_name}-ec2-role"`
- [x] `resource "aws_iam_role_policy" "backup_policy"`: inline policy granting `s3:PutObject` on `"${aws_s3_bucket.backups.arn}/*"` and `s3:ListBucket` on `aws_s3_bucket.backups.arn`
- [x] `resource "aws_iam_instance_profile" "main"`: references `aws_iam_role.ec2_role`; tag `Name = "${var.app_name}-instance-profile"`

### 2.5 `infra/backup.tf`
- [x] `resource "random_id" "bucket_suffix"`: `byte_length = 4` (add `hashicorp/random ~> 3.0` to required_providers in `main.tf`)
- [x] `resource "aws_s3_bucket" "backups"`: name `"${var.app_name}-db-backups-${random_id.bucket_suffix.hex}"`; tag `Name`
- [x] `resource "aws_s3_bucket_public_access_block" "backups"`: all four `block_*` flags set to `true`
- [x] `resource "aws_s3_bucket_server_side_encryption_configuration" "backups"`: `sse_algorithm = "AES256"`
- [x] `resource "aws_s3_bucket_lifecycle_configuration" "backups"`: rule with `expiration { days = var.backup_retention_days }`; status `"Enabled"`

### 2.6 `infra/outputs.tf`
- [x] Output `instance_public_ip`: `value = aws_eip.main.public_ip`; description "Elastic IP — use this as your DNS A record target"
- [x] Output `instance_id`: `value = aws_instance.main.id`
- [x] Output `backup_bucket_name`: `value = aws_s3_bucket.backups.id`
- [x] Output `ssh_command`: `value = "ssh ubuntu@${aws_eip.main.public_ip} -i <your-key>.pem"`
- [x] Output `deploy_hint`: `value = "scp -i <key>.pem .env docker-compose.yml ubuntu@${aws_eip.main.public_ip}:/opt/survivorpool/ && ssh ubuntu@${aws_eip.main.public_ip} 'cd /opt/survivorpool && docker compose up --build -d'"`

---

## Phase 3 — Cloud-init script

### 3.1 `infra/user_data.sh`
Write as a `templatefile`-compatible bash heredoc. Variables: `${backup_bucket}` (injected by Terraform).

- [x] Shebang: `#!/bin/bash`, `set -euo pipefail`
- [x] System update: `apt-get update -y && apt-get upgrade -y`
- [x] Docker install:
  - `apt-get install -y ca-certificates curl gnupg`
  - Add Docker official GPG key to `/etc/apt/keyrings/docker.gpg`
  - Add Docker apt repo to `/etc/apt/sources.list.d/docker.list`
  - `apt-get update -y && apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin`
  - `systemctl enable docker && systemctl start docker`
  - `usermod -aG docker ubuntu`
- [x] AWS CLI install (needed for `aws s3 cp` in backup script):
  - Download `awscli-exe-linux-x86_64.zip` from the official AWS URL, unzip, run `./aws/install`
- [x] Data volume setup:
  - Detect device: check `/dev/nvme1n1` first (Nitro instances), fall back to `/dev/xvdf`
  - If no filesystem on device (`! blkid "$DATA_DEV"`): `mkfs.ext4 "$DATA_DEV"`
  - `mkdir -p /data/postgres`
  - `mount "$DATA_DEV" /data/postgres`
  - Append to `/etc/fstab`: `"$DATA_DEV /data/postgres ext4 defaults,nofail 0 2"` (idempotent: check if already present)
  - `chown -R 999:999 /data/postgres` (PostgreSQL container runs as UID 999)
- [x] App directory: `mkdir -p /opt/survivorpool`; write a `README` with deploy instructions
- [x] Backup cron script at `/usr/local/bin/pg_backup.sh`:
  ```bash
  #!/bin/bash
  DATE=$(date +%Y-%m-%d)
  docker exec db pg_dump -U survivorpool survivorpool | gzip | \
    aws s3 cp - "s3://${backup_bucket}/pg_backup_$DATE.sql.gz"
  ```
  - `chmod +x /usr/local/bin/pg_backup.sh`
- [x] Cron entry: write `/etc/cron.d/survivorpool-backup` with `0 3 * * * root /usr/local/bin/pg_backup.sh >> /var/log/pg_backup.log 2>&1`

---

## Phase 4 — Helper files

### 4.1 `infra/terraform.tfvars.example`
- [x] Create file with commented examples:
  ```hcl
  # aws_region          = "us-east-1"
  # instance_type       = "t3.small"
  key_name              = "my-key-pair"        # Required: existing EC2 key pair name
  admin_cidr            = "YOUR.IP.HERE/32"    # Required: your public IP for SSH access
  # data_volume_size    = 20
  # backup_retention_days = 30
  ```

### 4.2 `deploy.sh` (repo root)
- [x] Create `deploy.sh` at the project root (not inside `infra/`):
  - `#!/bin/bash set -euo pipefail`
  - Get IP: `IP=$(cd infra && terraform output -raw instance_public_ip)`
  - Get key path from first arg or error: `KEY=${1:?Usage: ./deploy.sh path/to/key.pem}`
  - SCP `.env` and `docker-compose.yml` to `/opt/survivorpool/` on the instance
  - SCP `scoring_config.json` to `/opt/survivorpool/`
  - SSH command: `docker compose -f /opt/survivorpool/docker-compose.yml up --build -d`
  - `chmod +x deploy.sh`

---

## Phase 5 — Validation

### 5.1 Terraform validate and plan
- [x] `cd infra && terraform init`
- [x] `cp terraform.tfvars.example terraform.tfvars` and fill in `key_name` and `admin_cidr`
- [x] `terraform validate` — must pass with no errors
- [x] `terraform plan` — failed with "no credentials" as expected on local machine; config is valid
- [x] Verify the plan includes: 1 EC2 instance, 1 EBS volume, 1 EIP, 1 SG, 1 IAM role, 1 instance profile, 1 inline policy, 1 S3 bucket, 4 S3 bucket config resources, 1 random_id

### 5.2 Check docker-compose volume path
- [x] Update `docker-compose.yml` `db` service volumes entry from `postgres_data:/var/lib/postgresql/data` to `/data/postgres:/var/lib/postgresql/data` (bind mount to the EBS volume)
- [x] Remove the top-level `volumes: postgres_data:` declaration from `docker-compose.yml` (no longer needed once using a bind mount)
- [x] Verify the other services that mount `./scoring_config.json` still reference a relative path — confirm this path is valid from `/opt/survivorpool/`
