variable "aws_region" {
  description = "The AWS region to deploy resources in"
  type        = string
  default     = "eu-central-1"
}

variable "project_name" {
  description = "Project name used to prefix/tag all resources"
  type        = string
  default     = "app-pipeline"
}

variable "domain_name" {
  description = "Root domain used for the backend subdomain (api.<domain_name>)"
  type        = string
  default     = "puljic.ch"
}

variable "db_password" {
  description = "Master password for the RDS database instance"
  type        = string
  sensitive   = true // no default — real value set locally in terraform.tfvars (gitignored), never committed
}
