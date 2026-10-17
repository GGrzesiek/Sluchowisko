locals {
  backend_image_repository = "${var.region}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.backend.repository_id}"
  api_db_user              = trimsuffix(google_service_account.api.email, ".gserviceaccount.com")
  backend_secrets = {
    SECRET_KEY = "django-secret-key"
  }
}

resource "google_artifact_registry_repository" "backend" {
  repository_id = "backend"
  location      = var.region
  format        = "DOCKER"

  cleanup_policies {
    id     = "keep-recent"
    action = "KEEP"

    most_recent_versions {
      keep_count = 10
    }
  }

  cleanup_policies {
    id     = "delete-old"
    action = "DELETE"

    condition {
      tag_state  = "ANY"
      older_than = "604800s"
    }
  }
}

resource "google_service_account" "api" {
  account_id   = "backend-api"
  display_name = "Backend on Cloud Run"
}

resource "google_project_iam_member" "api" {
  for_each = toset(["roles/cloudsql.client", "roles/cloudsql.instanceUser"])
  project  = var.project_id
  role     = each.value
  member   = google_service_account.api.member
}

resource "google_sql_user" "api" {
  name     = local.api_db_user
  instance = google_sql_database_instance.main.name
  type     = "CLOUD_IAM_SERVICE_ACCOUNT"
}

resource "google_secret_manager_secret_iam_member" "api" {
  for_each  = local.backend_secrets
  secret_id = each.value
  role      = "roles/secretmanager.secretAccessor"
  member    = google_service_account.api.member
}

resource "google_cloud_run_v2_service" "backend" {
  name     = "backend"
  location = var.region
  ingress  = "INGRESS_TRAFFIC_ALL"

  template {
    service_account = google_service_account.api.email

    scaling {
      max_instance_count = 2
    }

    containers {
      name       = "app"
      image      = "us-docker.pkg.dev/cloudrun/container/hello"
      depends_on = ["cloud-sql-proxy"]

      ports {
        container_port = 8080
      }

      env {
        name  = "DEBUG"
        value = "0"
      }

      env {
        name  = "ALLOWED_HOSTS"
        value = ".run.app"
      }

      env {
        name  = "CITY_API_LIVE"
        value = "0"
      }

      env {
        name  = "DATABASE_URL"
        value = "postgres://${urlencode(local.api_db_user)}@127.0.0.1:5432/${google_sql_database.main.name}"
      }

      dynamic "env" {
        for_each = local.backend_secrets
        content {
          name = env.key
          value_source {
            secret_key_ref {
              secret  = env.value
              version = "latest"
            }
          }
        }
      }
    }

    containers {
      name  = "cloud-sql-proxy"
      image = "gcr.io/cloud-sql-connectors/cloud-sql-proxy:2.26.0"
      args = [
        "--auto-iam-authn",
        "--port=5432",
        "--health-check",
        "--http-address=0.0.0.0",
        "--http-port=9090",
        google_sql_database_instance.main.connection_name,
      ]

      startup_probe {
        period_seconds    = 2
        failure_threshold = 30
        http_get {
          path = "/startup"
          port = 9090
        }
      }
    }
  }

  lifecycle {
    ignore_changes = [template[0].containers[0].image, client, client_version]
  }

  depends_on = [google_secret_manager_secret_iam_member.api, google_project_iam_member.api]
}

resource "google_cloud_run_v2_service_iam_member" "public" {
  name     = google_cloud_run_v2_service.backend.name
  location = var.region
  role     = "roles/run.invoker"
  member   = "allUsers"
}
