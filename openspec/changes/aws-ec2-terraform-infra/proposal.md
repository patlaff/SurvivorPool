# Proposal: AWS EC2 + Docker Compose Infrastructure (Terraform)

## What

Terraform configuration in a new `infra/` root folder that provisions all AWS resources needed to run SurvivorPool on a single EC2 instance using the existing Docker Compose setup.

Resources provisioned:
1. **EC2 t3.small** — runs all six containers (PostgreSQL, Redis, Django, Celery, Celery Beat, Nginx/React)
2. **EBS gp3 data volume** (20 GB, separate from the OS disk) — mounted for PostgreSQL data persistence; survives OS reinstalls and is easy to snapshot
3. **Elastic IP** — stable public IP so DNS doesn't change across stop/start cycles
4. **Security group** — port 80 open to the world, port 22 restricted to a configurable admin CIDR
5. **S3 bucket** — receives nightly `pg_dump` backups via a cron job on the instance
6. **IAM instance profile** — lets the EC2 instance write to the backup bucket without embedding AWS credentials in the environment

The cloud-init user data script bootstraps Docker, formats/mounts the data volume, and sets up a daily `pg_dump → S3` cron.

## Why

- The app has < 50 users and bursty traffic (once-weekly Survivor episodes); a single VM running Docker Compose is the cheapest possible architecture that matches the existing workflow
- Keeping PostgreSQL in a container on the same VM eliminates managed-DB costs (RDS minimum ~$30/month vs ~$0 in-container)
- A separate data EBS volume means a DB snapshot is one AWS console click; the OS volume can be replaced without touching data
- Elastic IP ensures a DNS `A` record never needs updating after instance maintenance
- S3 backups at < 1 GB/dump cost < $0.03/month and protect against accidental `docker volume rm`

## Estimated monthly cost

| Resource | Type | $/month (on-demand) |
|---|---|---|
| EC2 t3.small | 2 vCPU / 2 GB | ~$16.80 |
| EBS gp3 20 GB (data) | SSD | ~$1.60 |
| EBS gp3 8 GB (OS) | SSD | ~$0.64 |
| Elastic IP | attached | $0.00 |
| S3 backups | < 5 GB | ~$0.12 |
| **Total** | | **~$19/month** |

With a 1-year reserved instance (no upfront): ~$12/month total.

## Out of scope

- HTTPS / TLS termination (add ACM + ALB or Caddy later once a domain is ready)
- CI/CD pipeline (a separate `deploy.sh` helper script is included; GitHub Actions wiring is not)
- Multi-AZ or auto-scaling (not warranted at this scale)
- ECR container registry (images are built on the instance from source; avoids registry costs and push complexity for now)
