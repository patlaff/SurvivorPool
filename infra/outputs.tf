output "instance_public_ip" {
  description = "Elastic IP — use this as your DNS A record target"
  value       = aws_eip.main.public_ip
}

output "instance_id" {
  description = "EC2 instance ID"
  value       = aws_instance.main.id
}

output "backup_bucket_name" {
  description = "S3 bucket name for daily PostgreSQL backups"
  value       = aws_s3_bucket.backups.id
}

output "ssh_command" {
  description = "Ready-to-paste SSH command"
  value       = "ssh ubuntu@${aws_eip.main.public_ip} -i <your-key>.pem"
}

output "deploy_hint" {
  description = "One-liner to deploy the app after first SSH in"
  value       = "scp -i <key>.pem .env docker-compose.yml scoring_config.json ubuntu@${aws_eip.main.public_ip}:/opt/survivorpool/ && ssh ubuntu@${aws_eip.main.public_ip} 'cd /opt/survivorpool && docker compose up --build -d'"
}
