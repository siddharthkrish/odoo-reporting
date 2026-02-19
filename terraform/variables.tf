variable "project_id" {
  description = "GCP project ID"
  type        = string
}

variable "region" {
  description = "GCP region for all resources"
  type        = string
  default     = "asia-southeast1"
}

variable "image_tag" {
  description = "Docker image tag to deploy on Cloud Run"
  type        = string
  default     = "latest"
}

variable "odoo_url" {
  description = "Odoo instance URL"
  type        = string
  sensitive   = true
}

variable "odoo_db" {
  description = "Odoo database name"
  type        = string
  sensitive   = true
}

variable "odoo_username" {
  description = "Odoo username"
  type        = string
  sensitive   = true
}

variable "odoo_api_key" {
  description = "Odoo API key"
  type        = string
  sensitive   = true
}
