# ── Artifact Registry ────────────────────────────────────────────────────────

resource "google_artifact_registry_repository" "odoo_reporting" {
  repository_id = "odoo-reporting"
  format        = "DOCKER"
  location      = var.region
  description   = "Docker images for the odoo-sales reporting service"

  lifecycle {
    prevent_destroy = true
  }
}

# ── Service Account ───────────────────────────────────────────────────────────

resource "google_service_account" "odoo_sales_runner" {
  account_id   = "odoo-sales-runner"
  display_name = "Odoo Sales Cloud Run Runner"
}

# ── Secret Manager: secrets ───────────────────────────────────────────────────

resource "google_secret_manager_secret" "odoo_url" {
  secret_id = "odoo-url"
  replication {
    auto {}
  }
}

resource "google_secret_manager_secret" "odoo_db" {
  secret_id = "odoo-db"
  replication {
    auto {}
  }
}

resource "google_secret_manager_secret" "odoo_username" {
  secret_id = "odoo-username"
  replication {
    auto {}
  }
}

resource "google_secret_manager_secret" "odoo_api_key" {
  secret_id = "odoo-api-key"
  replication {
    auto {}
  }
}

# ── Secret Manager: versions (actual values) ──────────────────────────────────

resource "google_secret_manager_secret_version" "odoo_url" {
  secret      = google_secret_manager_secret.odoo_url.id
  secret_data = var.odoo_url
}

resource "google_secret_manager_secret_version" "odoo_db" {
  secret      = google_secret_manager_secret.odoo_db.id
  secret_data = var.odoo_db
}

resource "google_secret_manager_secret_version" "odoo_username" {
  secret      = google_secret_manager_secret.odoo_username.id
  secret_data = var.odoo_username
}

resource "google_secret_manager_secret_version" "odoo_api_key" {
  secret      = google_secret_manager_secret.odoo_api_key.id
  secret_data = var.odoo_api_key
}

# ── Secret Manager: IAM (SA access to each individual secret) ─────────────────

resource "google_secret_manager_secret_iam_member" "odoo_sales_url" {
  secret_id = google_secret_manager_secret.odoo_url.secret_id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.odoo_sales_runner.email}"
}

resource "google_secret_manager_secret_iam_member" "odoo_sales_db" {
  secret_id = google_secret_manager_secret.odoo_db.secret_id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.odoo_sales_runner.email}"
}

resource "google_secret_manager_secret_iam_member" "odoo_sales_username" {
  secret_id = google_secret_manager_secret.odoo_username.secret_id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.odoo_sales_runner.email}"
}

resource "google_secret_manager_secret_iam_member" "odoo_sales_api_key" {
  secret_id = google_secret_manager_secret.odoo_api_key.secret_id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.odoo_sales_runner.email}"
}

# ── Cloud Run v2 Service ──────────────────────────────────────────────────────

locals {
  image_uri = "${var.region}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.odoo_reporting.repository_id}/odoo-sales:${var.image_tag}"
}

resource "google_cloud_run_v2_service" "odoo_sales" {
  name     = "odoo-sales"
  location = var.region

  template {
    service_account = google_service_account.odoo_sales_runner.email

    containers {
      image = local.image_uri

      env {
        name = "ODOO_URL"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.odoo_url.secret_id
            version = "latest"
          }
        }
      }

      env {
        name = "ODOO_DB"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.odoo_db.secret_id
            version = "latest"
          }
        }
      }

      env {
        name = "ODOO_USERNAME"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.odoo_username.secret_id
            version = "latest"
          }
        }
      }

      env {
        name = "ODOO_API_KEY"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.odoo_api_key.secret_id
            version = "latest"
          }
        }
      }
    }
  }

  depends_on = [
    google_secret_manager_secret_iam_member.odoo_sales_url,
    google_secret_manager_secret_iam_member.odoo_sales_db,
    google_secret_manager_secret_iam_member.odoo_sales_username,
    google_secret_manager_secret_iam_member.odoo_sales_api_key,
  ]
}

# ── Cloud Run IAM: public access ──────────────────────────────────────────────

resource "google_cloud_run_v2_service_iam_member" "public_access" {
  name     = google_cloud_run_v2_service.odoo_sales.name
  location = var.region
  role     = "roles/run.invoker"
  member   = "allUsers"
}
