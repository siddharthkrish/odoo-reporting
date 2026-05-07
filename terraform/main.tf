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

# ── Secret Manager: secrets (sensitive values only) ───────────────────────────

resource "google_secret_manager_secret" "odoo_api_key" {
  secret_id = "odoo-api-key"
  replication {
    user_managed {
      replicas {
        location = var.region
      }
    }
  }
}

resource "google_secret_manager_secret" "google_client_secret" {
  secret_id = "google-client-secret"
  replication {
    user_managed {
      replicas {
        location = var.region
      }
    }
  }
}

resource "google_secret_manager_secret" "session_secret" {
  secret_id = "session-secret"
  replication {
    user_managed {
      replicas {
        location = var.region
      }
    }
  }
}

# ── Secret Manager: versions (actual values) ──────────────────────────────────

resource "google_secret_manager_secret_version" "odoo_api_key" {
  secret      = google_secret_manager_secret.odoo_api_key.id
  secret_data = var.odoo_api_key
}

resource "google_secret_manager_secret_version" "google_client_secret" {
  secret      = google_secret_manager_secret.google_client_secret.id
  secret_data = var.google_client_secret
}

resource "google_secret_manager_secret_version" "session_secret" {
  secret      = google_secret_manager_secret.session_secret.id
  secret_data = var.session_secret
}

# ── Secret Manager: IAM (SA access to each individual secret) ─────────────────

resource "google_secret_manager_secret_iam_member" "odoo_sales_api_key" {
  secret_id = google_secret_manager_secret.odoo_api_key.secret_id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.odoo_sales_runner.email}"
}

resource "google_secret_manager_secret_iam_member" "odoo_sales_google_client_secret" {
  secret_id = google_secret_manager_secret.google_client_secret.secret_id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.odoo_sales_runner.email}"
}

resource "google_secret_manager_secret_iam_member" "odoo_sales_session_secret" {
  secret_id = google_secret_manager_secret.session_secret.secret_id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.odoo_sales_runner.email}"
}

# ── Firestore IAM: allow the runner SA to read allowed_users ─────────────────

resource "google_project_iam_member" "odoo_sales_firestore" {
  project = var.project_id
  role    = "roles/datastore.user"
  member  = "serviceAccount:${google_service_account.odoo_sales_runner.email}"
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
        name  = "ODOO_URL"
        value = var.odoo_url
      }

      env {
        name  = "ODOO_DB"
        value = var.odoo_db
      }

      env {
        name  = "ODOO_USERNAME"
        value = var.odoo_username
      }

      env {
        name  = "GOOGLE_CLIENT_ID"
        value = var.google_client_id
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

      env {
        name = "GOOGLE_CLIENT_SECRET"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.google_client_secret.secret_id
            version = "latest"
          }
        }
      }

      env {
        name = "SESSION_SECRET"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.session_secret.secret_id
            version = "latest"
          }
        }
      }
    }
  }

  depends_on = [
    google_secret_manager_secret_iam_member.odoo_sales_api_key,
    google_secret_manager_secret_iam_member.odoo_sales_google_client_secret,
    google_secret_manager_secret_iam_member.odoo_sales_session_secret,
    google_project_iam_member.odoo_sales_firestore,
  ]
}

# ── Cloud Run IAM: public access ──────────────────────────────────────────────

resource "google_cloud_run_v2_service_iam_member" "public_access" {
  name     = google_cloud_run_v2_service.odoo_sales.name
  location = var.region
  role     = "roles/run.invoker"
  member   = "allUsers"
}
