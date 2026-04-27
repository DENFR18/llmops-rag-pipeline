# llmops-rag-pipeline

[![ci](https://github.com/DENFR18/llmops-rag-pipeline/actions/workflows/ci.yml/badge.svg)](https://github.com/DENFR18/llmops-rag-pipeline/actions/workflows/ci.yml)
[![eval](https://github.com/DENFR18/llmops-rag-pipeline/actions/workflows/eval.yml/badge.svg)](https://github.com/DENFR18/llmops-rag-pipeline/actions/workflows/eval.yml)
[![Quality Gate](https://sonarcloud.io/api/project_badges/measure?project=DENFR18_llmops-rag-pipeline&metric=alert_status)](https://sonarcloud.io/summary/new_code?id=DENFR18_llmops-rag-pipeline)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

> The LLM-shaped sequel to [`mlops-pipeline`](https://github.com/DENFR18/mlops-pipeline):
> same DevSecOps gates (Sonar / Trivy / Checkov), same Scaleway target — applied to a
> production-grade RAG service over Claude Sonnet 4.6 with prompt caching, pgvector, and
> eval-as-code.

## Architecture

```
┌────────────┐   POST /query (SSE)   ┌──────────────────────┐
│  Client    │ ────────────────────► │  FastAPI + Uvicorn   │
└────────────┘                       │  src/api.py          │
                                     └─────┬────────────────┘
                                           │
                ┌──────────────────────────┼──────────────────────────────┐
                ▼                          ▼                              ▼
       ┌──────────────────┐     ┌─────────────────────┐         ┌──────────────────┐
       │  LLM Guard       │     │  LlamaIndex         │         │  Anthropic API   │
       │  (injection +    │     │  retriever          │         │  Sonnet 4.6      │
       │   PII redact)    │     │  ↓                  │         │  prompt caching  │
       └──────────────────┘     │  pgvector / Neon    │         └────────┬─────────┘
                                └─────────────────────┘                  │
                                                                          ▼
                                                                 ┌──────────────────┐
                                                                 │     Langfuse     │
                                                                 │  cost / latency  │
                                                                 │  cache hit ratio │
                                                                 └──────────────────┘
```

Full diagram: [`docs/architecture.md`](docs/architecture.md).

## Stack

| Layer | Choice |
|---|---|
| LLM | Claude Sonnet 4.6 (`claude-sonnet-4-6`) — prompt caching enabled |
| Embeddings | Voyage `voyage-3` (default) or OpenAI `text-embedding-3-small` |
| Vector store | `pgvector` on Neon Postgres |
| RAG framework | LlamaIndex |
| API | FastAPI + Uvicorn, SSE streaming via `sse-starlette` |
| Prompt safety | LLM Guard (`PromptInjection`, `Anonymize`) |
| Observability | Langfuse (self-hosted via compose, cloud in prod) |
| Eval | Ragas (semantic) + Promptfoo (behavioral) |
| Container | Docker, multi-stage, non-root, `HEALTHCHECK` |
| Runtime | Scaleway Serverless Containers |
| Registry | GHCR + Scaleway Container Registry |
| IaC | Terraform (Neon + Scaleway) |
| CI/CD | GitHub Actions — lint, test, sonar, build, trivy, checkov, push, eval, deploy |

## MLOps vs LLMOps — what changes

This repo deliberately ports the `mlops-pipeline` discipline to LLM serving. The full
write-up lives in [`docs/llmops-vs-mlops.md`](docs/llmops-vs-mlops.md); the short version:

- **The artifact is a prompt, not a model.** Weights are SaaS — what you own and version
  is the system instruction, the retrieval recipe, the chunker config. So those are
  treated as first-class artifacts, gated by Ragas in CI on every PR.
- **Tests aren't enough — you need evals as a CI gate.** A unit test can't decide whether
  an answer is "faithful enough." `eval.yml` fails the build when faithfulness < 0.85,
  answer_relevancy < 0.80, or context_precision < 0.75 — same shape as the Trivy CVE
  gate, semantic thresholds instead of CVE counts.
- **Threat model gains new top entries.** OWASP LLM01 (prompt injection) and LLM06
  (PII leak) are blocked by `src/guards.py` with LLM Guard scanners, with ≥ 10 known
  jailbreaks in the unit-test suite.
- **Cost is a SLI.** Prompt caching (`cache_control: ephemeral`) is wired on both the
  system block and the retrieved-context block — cache reads bill at 0.1x. Langfuse logs
  `cache_read_input_tokens` per call so the hit ratio is observable next to latency.

In one sentence: **the playbook (lint → test → scan → gate → deploy) is the same; the
failure modes are new.**

## Quickstart (local)

```bash
git clone https://github.com/DENFR18/llmops-rag-pipeline.git
cd llmops-rag-pipeline
cp .env.example .env   # fill in ANTHROPIC_API_KEY, VOYAGE_API_KEY at minimum

docker compose up --build -d
docker compose exec api python -m src.ingest data/sample_docs

curl -N -X POST http://localhost:8000/query \
  -H 'Content-Type: application/json' \
  -d '{"question": "What model id should I use to call Sonnet 4.6?"}'
```

Langfuse UI: <http://localhost:3000> (create an org/project on first run, paste the keys
into `.env`, restart `api`).

## CI/CD

| Job | Tool | Gate | `needs:` |
|---|---|---|---|
| `lint` | ruff + flake8 | non-zero exit fails | — |
| `test` | pytest + coverage.xml | tests must pass | `lint` |
| `sonarcloud` | SonarCloud action | `continue-on-error: true` (advisory) | `test` |
| `checkov` | Checkov SARIF (Dockerfile + Terraform) | `soft_fail: true` (advisory) | `lint` |
| `build` | docker buildx + smoke `/health` | health probe must succeed | `test` |
| `trivy` | Trivy SARIF (CRITICAL,HIGH) | `exit-code: 0` (advisory) | `build` |
| `push-ghcr` | docker push to GHCR | runs only on `main` push | `trivy, sonar, checkov` |
| `ragas` | Ragas thresholds | **hard fail** below 0.85 / 0.80 / 0.75 | (eval.yml) |
| `promptfoo` | Promptfoo behavioral assertions | hard fail | `ragas` |

The advisory scans (Sonar, Trivy, Checkov) all upload SARIF to GitHub Security so issues
are visible in the Security tab without blocking PRs — same trade-off as `mlops-pipeline`.

## Eval-as-code

Ragas runs on `evals/golden_dataset.jsonl` (30 Q/A/context records covering the Anthropic
docs in `data/sample_docs/`). Three metrics, three thresholds:

| Metric | Threshold | What it catches |
|---|---|---|
| `faithfulness` | ≥ 0.85 | Answers must be grounded in retrieved context (no hallucinations) |
| `answer_relevancy` | ≥ 0.80 | Answers must actually address the question asked |
| `context_precision` | ≥ 0.75 | Retrieved chunks must be on-topic (chunker / top-K sanity) |

Promptfoo (`evals/promptfooconfig.yaml`) adds behavioral assertions: out-of-scope abstention,
no system-prompt exfiltration, latency budget. Promptfoo is gated on a repo variable
`RUN_PROMPTFOO=true` so it only runs when a staging API URL is configured.

A summary table is posted as a sticky comment on the PR.

## Deploy to Scaleway

```bash
# 1. Provision (one-time)
cd terraform
terraform init
terraform apply \
  -var "scw_access_key=..." -var "scw_secret_key=..." \
  -var "scw_project_id=..." -var "scw_organization_id=..." \
  -var "neon_api_key=..." -var "anthropic_api_key=..." \
  -var "neon_database_url=..."

# 2. Subsequent deploys are triggered automatically by the deploy-scaleway.yml
#    workflow on every successful main-branch CI run, or manually:
#    Actions → deploy-scaleway → Run workflow → image_tag=<sha>
```

Teardown: trigger the `destroy-scaleway` workflow with `confirm=destroy` (the input check
prevents accidental teardown).

## Required secrets / env

Documented in [`.env.example`](.env.example) — never commit values.

| Secret | Used by |
|---|---|
| `ANTHROPIC_API_KEY` | runtime, eval |
| `VOYAGE_API_KEY` *or* `OPENAI_API_KEY` | runtime (embeddings), eval |
| `NEON_DATABASE_URL` | runtime |
| `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`, `LANGFUSE_HOST` | runtime |
| `SCW_ACCESS_KEY`, `SCW_SECRET_KEY`, `SCW_DEFAULT_PROJECT_ID`, `SCW_DEFAULT_ORGANIZATION_ID` | deploy |
| `SONAR_TOKEN` | CI |
| `NEON_API_KEY` | Terraform |

## Limits assumed (honest list)

- **No fine-tuning, no LoRA.** Out of scope on purpose — the entire point is that you
  can ship a useful, well-operated RAG without owning weights.
- **No multi-tenant isolation.** Single project, single index. Per-tenant namespacing in
  pgvector is straightforward but deliberately not done here to keep the scaffold sharp.
- **No agentic loops.** No tool-use chaining, no CrewAI / AutoGen. RAG-only — one retrieve,
  one generate. A multi-step agent is a different scaffold and a different threat model.
- **No reranker.** Top-K from cosine similarity is the baseline; Voyage rerank-2 or
  Cohere rerank can be dropped in at `src/rag.py:Retriever.retrieve` when the eval gate
  starts complaining about `context_precision`.
- **No request-level cost gate.** Langfuse records the per-call cost; turning it into a
  CI gate (à la "fail PR if median cost rises >20%") is a v2 item.
- **Local Langfuse stack is dev-only.** Production uses Langfuse Cloud — the
  self-hosted compose setup skips Clickhouse/Redis and is fine for tracing but not for
  load.

## License

MIT. See [`LICENSE`](LICENSE).
