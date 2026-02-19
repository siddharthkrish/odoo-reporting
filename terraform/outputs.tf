output "cloud_run_url" {
  description = "Public URL of the Cloud Run service"
  value       = google_cloud_run_v2_service.odoo_sales.uri
}

output "service_account_email" {
  description = "Email of the service account used by Cloud Run"
  value       = google_service_account.odoo_sales_runner.email
}

output "artifact_registry_url" {
  description = "Base repository URL for pushing Docker images"
  value       = "${var.region}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.odoo_reporting.repository_id}"
}
