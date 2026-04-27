variable "project_name" {
  type    = string
  default = "llmops-rag-pipeline"
}

variable "environment" {
  type    = string
  default = "prod"
}

variable "image_tag" {
  type    = string
  default = "latest"
}

# Scaleway
variable "scw_access_key" {
  type      = string
  sensitive = true
}
variable "scw_secret_key" {
  type      = string
  sensitive = true
}
variable "scw_project_id" { type = string }
variable "scw_organization_id" { type = string }
variable "scw_region" {
  type    = string
  default = "fr-par"
}
variable "scw_zone" {
  type    = string
  default = "fr-par-1"
}

# Neon
variable "neon_api_key" {
  type      = string
  sensitive = true
}
variable "neon_region" {
  type    = string
  default = "aws-eu-central-1"
}

# Runtime config injected into the container as secrets
variable "anthropic_api_key" {
  type      = string
  sensitive = true
}
variable "voyage_api_key" {
  type      = string
  sensitive = true
  default   = ""
}
variable "openai_api_key" {
  type      = string
  sensitive = true
  default   = ""
}
variable "embeddings_provider" {
  type    = string
  default = "voyage"
}
variable "neon_database_url" {
  type      = string
  sensitive = true
}
variable "langfuse_public_key" {
  type      = string
  sensitive = true
  default   = ""
}
variable "langfuse_secret_key" {
  type      = string
  sensitive = true
  default   = ""
}
variable "langfuse_host" {
  type    = string
  default = "https://cloud.langfuse.com"
}
