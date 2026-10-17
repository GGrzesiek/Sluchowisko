locals {
  member_project_roles = [
    "roles/cloudsql.client",
    "roles/cloudsql.instanceUser",
    "roles/serviceusage.serviceUsageConsumer",
  ]

  member_role_pairs = {
    for pair in setproduct(var.members, local.member_project_roles) : "${pair[0]} ${pair[1]}" => {
      member = pair[0]
      role   = pair[1]
    }
  }
}

resource "google_storage_bucket" "audio" {
  name                        = "${var.project_id}-audio"
  location                    = var.region
  uniform_bucket_level_access = true
  public_access_prevention    = "enforced"

  versioning {
    enabled = true
  }
}

resource "google_sql_database_instance" "main" {
  name                = "muzeum"
  database_version    = "POSTGRES_16"
  region              = var.region
  deletion_protection = true

  settings {
    edition           = "ENTERPRISE"
    tier              = "db-f1-micro"
    availability_type = "ZONAL"
    disk_size         = 10
    disk_autoresize   = true

    backup_configuration {
      enabled = true
    }

    ip_configuration {
      ipv4_enabled = true
      ssl_mode     = "ENCRYPTED_ONLY"
    }

    database_flags {
      name  = "cloudsql.iam_authentication"
      value = "on"
    }
  }
}

resource "google_sql_database" "main" {
  name     = "muzeum"
  instance = google_sql_database_instance.main.name
}

resource "google_sql_user" "ci" {
  name           = trimsuffix(var.ci_service_account, ".gserviceaccount.com")
  instance       = google_sql_database_instance.main.name
  type           = "CLOUD_IAM_SERVICE_ACCOUNT"
  database_roles = ["cloudsqlsuperuser"]
}

resource "google_sql_user" "members" {
  for_each = toset(var.members)
  name     = each.value
  instance = google_sql_database_instance.main.name
  type     = "CLOUD_IAM_USER"
}

resource "google_sql_user" "team_group" {
  name     = var.team_group
  instance = google_sql_database_instance.main.name
  type     = "CLOUD_IAM_GROUP"
}

resource "google_project_iam_member" "team_group" {
  for_each = toset(local.member_project_roles)
  project  = var.project_id
  role     = each.value
  member   = "group:${var.team_group}"
}

resource "google_storage_bucket_iam_member" "team_group" {
  bucket = google_storage_bucket.audio.name
  role   = "roles/storage.objectAdmin"
  member = "group:${var.team_group}"
}

resource "google_project_iam_member" "members" {
  for_each = local.member_role_pairs
  project  = var.project_id
  role     = each.value.role
  member   = "user:${each.value.member}"
}

resource "google_storage_bucket_iam_member" "audio" {
  for_each = toset(var.members)
  bucket   = google_storage_bucket.audio.name
  role     = "roles/storage.objectAdmin"
  member   = "user:${each.value}"
}
