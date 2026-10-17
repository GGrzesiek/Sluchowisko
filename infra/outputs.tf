output "audio_bucket" {
  value = google_storage_bucket.audio.name
}

output "data_bucket" {
  value = google_storage_bucket.data.name
}

output "cloudsql_instance" {
  value = google_sql_database_instance.main.connection_name
}

output "database" {
  value = google_sql_database.main.name
}

output "team_group" {
  value = google_sql_user.team_group.name
}

output "api_db_user" {
  value = local.api_db_user
}

output "backend_url" {
  value = google_cloud_run_v2_service.backend.uri
}

output "backend_image_repository" {
  value = local.backend_image_repository
}
