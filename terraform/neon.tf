resource "neon_project" "rag" {
  name      = "${var.project_name}-${var.environment}"
  region_id = var.neon_region
  pg_version = 16
}

resource "neon_branch" "main" {
  project_id = neon_project.rag.id
  name       = "main"
}

resource "neon_database" "rag" {
  project_id = neon_project.rag.id
  branch_id  = neon_branch.main.id
  name       = "rag"
  owner_name = neon_role.app.name
}

resource "neon_role" "app" {
  project_id = neon_project.rag.id
  branch_id  = neon_branch.main.id
  name       = "rag_app"
}

# pgvector extension is pre-installed on Neon; the app calls
# CREATE EXTENSION IF NOT EXISTS vector at startup via LlamaIndex's PGVectorStore.

output "neon_database_url" {
  value     = "postgresql://${neon_role.app.name}:${neon_role.app.password}@${neon_project.rag.connection_uri_host}/${neon_database.rag.name}?sslmode=require"
  sensitive = true
}
