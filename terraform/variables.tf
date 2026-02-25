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

variable "google_client_id" {
  description = "Google OAuth 2.0 client ID for OIDC sign-in"
  type        = string
  sensitive   = true
}

variable "google_client_secret" {
  description = "Google OAuth 2.0 client secret for OIDC sign-in"
  type        = string
  sensitive   = true
}

variable "session_secret" {
  description = "Random 32+ character string used to sign session cookies"
  type        = string
  sensitive   = true
}
