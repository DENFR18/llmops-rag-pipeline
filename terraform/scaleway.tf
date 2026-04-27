resource "scaleway_registry_namespace" "rag" {
  name        = "${var.project_name}-${var.environment}"
  description = "Container registry for ${var.project_name}"
  is_public   = false
  region      = var.scw_region
}

resource "scaleway_container_namespace" "rag" {
  name        = "${var.project_name}-${var.environment}"
  description = "Serverless namespace for the RAG API"
  region      = var.scw_region
}

resource "scaleway_container" "api" {
  name            = "${var.project_name}-api"
  namespace_id    = scaleway_container_namespace.rag.id
  registry_image  = "${scaleway_registry_namespace.rag.endpoint}/llmops-rag-pipeline:${var.image_tag}"
  port            = 8000
  cpu_limit       = 1000
  memory_limit    = 1024
  min_scale       = 0
  max_scale       = 3
  timeout         = 60
  privacy         = "public"
  protocol        = "http1"
  deploy          = true

  environment_variables = {
    EMBEDDINGS_PROVIDER = var.embeddings_provider
    LOG_LEVEL           = "INFO"
    LANGFUSE_HOST       = var.langfuse_host
  }

  secret_environment_variables = {
    ANTHROPIC_API_KEY    = var.anthropic_api_key
    VOYAGE_API_KEY       = var.voyage_api_key
    OPENAI_API_KEY       = var.openai_api_key
    NEON_DATABASE_URL    = var.neon_database_url
    LANGFUSE_PUBLIC_KEY  = var.langfuse_public_key
    LANGFUSE_SECRET_KEY  = var.langfuse_secret_key
  }
}

output "container_url" {
  value = scaleway_container.api.domain_name
}

output "registry_endpoint" {
  value = scaleway_registry_namespace.rag.endpoint
}
