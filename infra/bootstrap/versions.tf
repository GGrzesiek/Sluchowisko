terraform {
  required_version = ">= 1.9"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 7.0"
    }
  }

  backend "gcs" {
    bucket = "muzeum-w-autobusie-2026-tfstate"
    prefix = "bootstrap"
  }
}

provider "google" {
  project = var.project_id
}
