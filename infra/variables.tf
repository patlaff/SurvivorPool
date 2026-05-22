variable "aws_region" {
  type        = string
  default     = "us-east-1"
  description = "AWS region to deploy into"
}

variable "app_name" {
  type        = string
  default     = "survivorpool"
  description = "Prefix for all resource names and tags"
}

variable "instance_type" {
  type        = string
  default     = "t3.small"
  description = "EC2 instance type"
}

variable "key_name" {
  type        = string
  description = "Name of an existing EC2 key pair for SSH access"
}

variable "admin_cidr" {
  type        = string
  description = "Your public IP in CIDR form (e.g. 1.2.3.4/32) — restricts SSH access"
}

variable "data_volume_size" {
  type        = number
  default     = 20
  description = "PostgreSQL data EBS volume size in GB"
}

variable "backup_retention_days" {
  type        = number
  default     = 30
  description = "S3 lifecycle rule: delete backup objects older than this many days"
}
