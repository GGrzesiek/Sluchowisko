output "audio_bucket" {
  value = google_storage_bucket.audio.name
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
