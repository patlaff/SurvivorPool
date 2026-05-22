# Design: AWS EC2 + Docker Compose Infrastructure (Terraform)

## Directory layout

```
infra/
├── main.tf                    # Provider config, data sources
├── variables.tf               # All input variables
├── outputs.tf                 # Useful outputs (IP, SSH command, etc.)
├── compute.tf                 # EC2, EBS volumes, Elastic IP, security group
├── iam.tf                     # IAM role + instance profile for S3 access
├── backup.tf                  # S3 backup bucket
├── user_data.sh               # Cloud-init: Docker install, volume mount, backup cron
├── terraform.tfvars.example   # Copy to terraform.tfvars and fill in
└── .gitignore                 # Exclude state files and secrets
```

---

## 1. Provider and data sources (`main.tf`)

```hcl
terraform {
  required_version = ">= 1.7"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

# Use the default VPC to avoid VPC provisioning complexity
data "aws_vpc" "default" {
  default = true
}

# Pick the first available subnet in the default VPC
data "aws_subnets" "default" {
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.default.id]
  }
}

# Latest Ubuntu 24.04 LTS AMI
data "aws_ami" "ubuntu" {
  most_recent = true
  owners      = ["099720109477"] # Canonical
  filter {
    name   = "name"
    values = ["ubuntu/images/hvm-ssd-gp3/ubuntu-noble-24.04-amd64-server-*"]
  }
}
```

---

## 2. Variables (`variables.tf`)

| Variable | Default | Description |
|---|---|---|
| `aws_region` | `us-east-1` | AWS region to deploy into |
| `app_name` | `survivorpool` | Prefix for all resource names and tags |
| `instance_type` | `t3.small` | EC2 instance type |
| `key_name` | — | **Required.** Name of an existing EC2 key pair for SSH |
| `admin_cidr` | — | **Required.** Your IP in CIDR form for SSH access, e.g. `1.2.3.4/32` |
| `data_volume_size` | `20` | Size of the PostgreSQL data EBS volume in GB |
| `backup_retention_days` | `30` | S3 lifecycle rule: delete backups older than N days |

---

## 3. Compute resources (`compute.tf`)

### Security group
```
Ingress:
  - 80/tcp  from 0.0.0.0/0        (HTTP — app traffic)
  - 22/tcp  from var.admin_cidr   (SSH — admin only)
Egress:
  - all     to 0.0.0.0/0          (outbound: Docker pulls, survivoR2py data fetches, etc.)
```

### EC2 instance
- AMI: Ubuntu 24.04 LTS (data source above)
- Type: `var.instance_type` (default `t3.small`)
- Root volume: 8 GB gp3, encrypted, `delete_on_termination = true`
- `user_data`: rendered from `user_data.sh` template
- IAM instance profile: attached (for S3 backup writes)
- Metadata options: `http_tokens = "required"` (IMDSv2 enforced)

### EBS data volume
- 20 GB gp3, encrypted, in the same AZ as the instance
- Attached as `/dev/xvdf` (Nitro instances expose this as `/dev/nvme1n1`)
- `force_detach = false` — prevents accidental detach

### Elastic IP
- Allocated and associated with the instance
- `depends_on` the Internet Gateway to avoid allocation race

---

## 4. IAM (`iam.tf`)

Minimal policy: `s3:PutObject` and `s3:ListBucket` on the backup bucket only. No broader permissions.

```
aws_iam_role "ec2_role"
  → assume-role policy: ec2.amazonaws.com

aws_iam_role_policy "backup_policy"
  → s3:PutObject on arn:aws:s3:::${bucket_name}/*
  → s3:ListBucket on arn:aws:s3:::${bucket_name}

aws_iam_instance_profile "main"
  → role: ec2_role
```

---

## 5. S3 backup bucket (`backup.tf`)

- Bucket name: `${var.app_name}-db-backups-${random_id}` (random suffix to avoid global name collision)
- `block_public_acls = true`, `block_public_policy = true` (fully private)
- Versioning: disabled (backups are named by date; no need for object versions)
- Lifecycle rule: expire objects after `var.backup_retention_days` days
- Server-side encryption: `AES256`

---

## 6. Cloud-init user data (`user_data.sh`)

Runs once on first boot as root. Steps:

1. **System update** — `apt-get update && apt-get upgrade -y`
2. **Docker install** — official Docker apt repo; installs `docker-ce` and `docker-compose-plugin`
3. **Add ubuntu to docker group** — `usermod -aG docker ubuntu`
4. **Detect and format the data volume** — checks for `/dev/nvme1n1` first (Nitro), falls back to `/dev/xvdf`; formats with ext4 only if the device has no filesystem signature; mounts at `/data/postgres`; adds to `/etc/fstab` with `nofail`
5. **Create app directory** — `mkdir -p /opt/survivorpool`; creates a `README` pointing to the deploy script
6. **Daily backup cron** — installs `/usr/local/bin/pg_backup.sh` that runs `docker exec db pg_dump ... | gzip | aws s3 cp - s3://${BUCKET}/...`; registers in `/etc/cron.d/survivorpool-backup` to run at 03:00 UTC daily (well after the 21:05 Pacific scoring run)

The script is idempotent: re-running it on an already-configured instance is safe.

---

## 7. Outputs (`outputs.tf`)

| Output | Value |
|---|---|
| `instance_public_ip` | Elastic IP address |
| `instance_id` | EC2 instance ID |
| `backup_bucket_name` | S3 bucket name |
| `ssh_command` | Ready-to-paste SSH command: `ssh ubuntu@<ip> -i <key>.pem` |
| `deploy_hint` | One-liner reminder of how to trigger a deploy |

---

## 8. Deployment workflow (post-Terraform)

Terraform provisions infrastructure only. App deployment is a two-step manual process (until CI/CD is wired up):

1. **First deploy** — SSH in; copy `.env` and `docker-compose.yml` to `/opt/survivorpool/`; `cd /opt/survivorpool && docker compose up --build -d`
2. **Subsequent deploys** — SSH in; `cd /opt/survivorpool && git pull && docker compose up --build -d`

A helper `deploy.sh` at the repo root automates the SCP + SSH steps using `terraform output -raw instance_public_ip`.

---

## 9. `.gitignore` entries for `infra/`

```
.terraform/
.terraform.lock.hcl
terraform.tfvars
*.tfstate
*.tfstate.backup
*.tfplan
```

`terraform.tfvars` (which contains `admin_cidr` and `key_name`) must never be committed.
