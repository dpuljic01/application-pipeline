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

variable "cognito_user_pool_id" {
  type    = string
  default = "eu-central-1_V6q5uBZeF"
}

variable "cognito_app_client_id" {
  type    = string
  default = "2liul3p0l4fr3fs9mi3bdrdlpp"
}

variable "image_tag" {
  description = "Docker image tag to deploy — passed explicitly at apply time, e.g. -var=\"image_tag=$(git rev-parse --short HEAD)\""
  type        = string
}
