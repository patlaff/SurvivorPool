# Infrastructure

Terraform configuration for deploying SurvivorPool to a single AWS EC2 instance with encrypted EBS storage and automated PostgreSQL backups to S3.

## Overview

| Resource | Details |
|----------|---------|
| Compute | EC2 `t3.small` (Ubuntu 24.04 LTS) |
| Storage | 8 GB gp3 root EBS + 20 GB gp3 data EBS (PostgreSQL volume) |
| Network | Elastic IP, security group (HTTP public, SSH restricted) |
| Backups | Nightly `pg_dump` to S3, 30-day retention |
| IAM | EC2 instance role with S3 write permissions |

The entire stack runs on one instance using Docker Compose (Nginx → React frontend, Gunicorn → Django backend, PostgreSQL, Redis, Celery). This keeps costs around ~$10–15/month for a hobby-scale league app.

## Prerequisites

- [Terraform](https://developer.hashicorp.com/terraform/install) 1.5+
- AWS CLI configured with credentials that have EC2, S3, and IAM permissions
- An EC2 key pair already created in the target region (for SSH access)

## File Reference

| File | Purpose |
|------|---------|
| `main.tf` | Provider config (AWS 5.0+, random 3.0+), fetches default VPC and latest Ubuntu 24.04 AMI |
| `compute.tf` | Security group, EC2 instance, EBS data volume, Elastic IP |
| `iam.tf` | IAM role + instance profile granting S3 PutObject and ListBucket |
| `backup.tf` | S3 bucket for database backups, lifecycle rule for 30-day expiration |
| `variables.tf` | All input variables with descriptions and defaults |
| `outputs.tf` | Outputs: instance public IP, DNS, and security group ID |
| `user_data.sh` | Bootstrap script that runs on first boot to install Docker and mount the data volume |
| `terraform.tfvars.example` | Template — copy to `terraform.tfvars` and fill in your values |

## Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `aws_region` | No | `us-east-1` | AWS region to deploy into |
| `instance_type` | No | `t3.small` | EC2 instance type |
| `key_name` | **Yes** | — | Name of an existing EC2 key pair for SSH access |
| `admin_cidr` | **Yes** | — | CIDR block allowed to SSH (e.g. `1.2.3.4/32`) |
| `data_volume_size` | No | `20` | Size in GB for the PostgreSQL EBS volume |
| `backup_retention_days` | No | `30` | Days before S3 backup objects are deleted |

## Deployment

### 1. Configure Variables

```bash
cd infra
cp terraform.tfvars.example terraform.tfvars
```

Edit `terraform.tfvars`:

```hcl
aws_region        = "us-east-1"
key_name          = "my-keypair"
admin_cidr        = "203.0.113.5/32"
data_volume_size  = 20
```

### 2. Initialize Terraform

```bash
terraform init
```

### 3. Review the Plan

```bash
terraform plan
```

### 4. Apply

```bash
terraform apply
```

Terraform will output the instance's public IP and DNS name when complete.

### 5. Verify Bootstrap

The `user_data.sh` script runs automatically on first boot. It takes 2–3 minutes to complete. You can watch its progress:

```bash
ssh -i ~/.ssh/my-keypair.pem ubuntu@<public-ip> "tail -f /var/log/cloud-init-output.log"
```

When complete, Docker will be installed and the data volume will be mounted at `/data/postgres`.

---

## Application Deployment

After Terraform creates the infrastructure, deploy the application manually:

### 1. Copy Application Files

```bash
scp -i ~/.ssh/my-keypair.pem \
  ../.env \
  ../docker-compose.yml \
  ../scoring_config.json \
  ubuntu@<public-ip>:/opt/survivorpool/
```

### 2. Start the Stack

```bash
ssh -i ~/.ssh/my-keypair.pem ubuntu@<public-ip>
cd /opt/survivorpool
docker compose up --build -d
```

Docker Compose starts six services:

| Service | Image | Port | Description |
|---------|-------|------|-------------|
| `db` | postgres:16 | 5432 | PostgreSQL, data stored at `/data/postgres` |
| `redis` | redis:7 | 6379 | Celery broker and result cache |
| `backend` | (built) | 8000 | Django/Gunicorn API (4 workers) |
| `celery` | (built) | — | Celery task worker |
| `celerybeat` | (built) | — | Celery Beat scheduler |
| `frontend` | (built) | 80 | Nginx serving React build, proxies `/api` to backend |

### 3. Verify the Stack

```bash
docker compose ps
docker compose logs backend --tail 50
```

The app is accessible at `http://<elastic-ip>/` once all containers report healthy.

---

## Infrastructure Details

### Security Group Rules

| Direction | Protocol | Port | Source | Purpose |
|-----------|----------|------|--------|---------|
| Inbound | TCP | 80 | `0.0.0.0/0` | HTTP (Nginx) |
| Inbound | TCP | 22 | `admin_cidr` | SSH admin access |
| Outbound | All | All | `0.0.0.0/0` | Egress (Docker pulls, survivoR data) |

Port 443 (HTTPS) is not opened by default. To add TLS, provision a certificate (e.g. with Certbot) and extend the security group rule in `compute.tf`.

### EBS Volumes

Two EBS volumes are attached to the instance:

| Volume | Size | Type | Encrypted | Mount Point |
|--------|------|------|-----------|-------------|
| Root | 8 GB | gp3 | Yes | `/` |
| Data | 20 GB (configurable) | gp3 | Yes | `/data/postgres` |

The data volume is separate from the root volume so that PostgreSQL data survives an OS rebuild. The mount is persisted in `/etc/fstab` by the bootstrap script.

### IAM Role

The EC2 instance is assigned an IAM instance profile with a single policy granting:

```json
{
  "Effect": "Allow",
  "Action": ["s3:PutObject", "s3:ListBucket"],
  "Resource": [
    "arn:aws:s3:::survivorpool-backups-<random>",
    "arn:aws:s3:::survivorpool-backups-<random>/*"
  ]
}
```

This allows the backup script to upload dumps to S3 without storing AWS credentials on the instance (uses IMDSv2 instance metadata instead).

IMDSv2 is enforced on the instance (`http_tokens = "required"`) to prevent SSRF-based credential theft.

### S3 Backup Bucket

- Bucket name is randomly suffixed to avoid global conflicts
- A lifecycle rule deletes objects older than `backup_retention_days` (default 30)
- Versioning is not enabled — each day's backup overwrites the path prefix

---

## Database Backups

A cron job installed by `user_data.sh` runs nightly at **3:00 AM UTC**:

```bash
# /opt/survivorpool/backup.sh (installed by user_data.sh)
DATE=$(date +%Y-%m-%d)
docker exec db pg_dump -U postgres survivorpool | gzip \
  | aws s3 cp - s3://survivorpool-backups-<id>/postgres/${DATE}.sql.gz
```

To restore from a backup:

```bash
# Download the backup
aws s3 cp s3://survivorpool-backups-<id>/postgres/2025-01-15.sql.gz ./restore.sql.gz

# Restore into the running container
gunzip -c restore.sql.gz | docker exec -i db psql -U postgres survivorpool
```

---

## Outputs

After `terraform apply`, the following values are printed:

| Output | Description |
|--------|-------------|
| `instance_public_ip` | Elastic IP address of the instance |
| `instance_public_dns` | AWS-provided public DNS hostname |
| `security_group_id` | ID of the application security group |

Retrieve them at any time with:

```bash
terraform output
```

---

## Tearing Down

```bash
terraform destroy
```

This deletes the EC2 instance, EBS volumes, Elastic IP, IAM role, and S3 bucket. **All data will be lost.** Ensure you have downloaded any needed backups before destroying.

---

## Scaling Considerations

The current single-instance design is intentional for cost at hobby scale. If the app needs to grow:

- **Database**: Migrate PostgreSQL to RDS (requires updating `DATABASE_URL`, removing the `db` container)
- **Cache/Queue**: Migrate Redis to ElastiCache (requires updating `REDIS_URL`, removing the `redis` container)
- **Compute**: Move to an ECS Fargate service or Elastic Beanstalk behind an ALB for horizontal scaling
- **TLS**: Add an ACM certificate and ALB, or run Certbot on the instance for a simpler upgrade path
- **Instance size**: Upgrade from `t3.small` to `t3.medium` (costs ~$30/mo) for more headroom with large leagues
