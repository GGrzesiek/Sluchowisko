variable "project_id" {
  type    = string
  default = "muzeum-w-autobusie-2026"
}

variable "region" {
  type    = string
  default = "europe-central2"
}

variable "ci_service_account" {
  type    = string
  default = "tf-apply@muzeum-w-autobusie-2026.iam.gserviceaccount.com"
}

variable "members" {
  type = list(string)
}
