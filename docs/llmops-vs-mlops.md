# MLOps vs LLMOps — what actually changes

This project is the LLM-shaped sibling of [`mlops-pipeline`](https://github.com/DENFR18/mlops-pipeline).
Same DevSecOps discipline (Sonar / Trivy / Checkov / SARIF / Scaleway / Terraform), same CI
gating philosophy. What changes is **where the risk lives**.

## 1. The artifact you ship is a prompt, not a model

In MLOps, the output of `train.py` is a serialized model: a `.pkl`, a `.pt`, an MLflow run.
You version it, you scan it, you A/B test it. The drift you fear is **data drift** — the
input distribution moving away from what the model was fit on.

In LLMOps, the artifact is a **prompt + retrieval recipe + tool schema**. The weights are
SaaS, and you don't own them. The drift you fear is **provider drift** (the model gets
silently updated), **retrieval drift** (your index goes stale), and **prompt drift** (a
seemingly harmless template tweak tanks faithfulness). That's why this repo treats the
prompt template, the chunker config, and the system instructions as first-class versioned
artifacts — and why `eval.yml` runs Ragas on every PR that touches `src/` or `evals/`.

## 2. "Tests" are not enough — you need evals as a CI gate

A unit test asserts behavior on inputs it has seen. An LLM does not give you that luxury:
the same prompt can produce two different valid answers, and "valid" is a fuzzy notion
(faithful? relevant? non-toxic?). So we add a layer **above** pytest:

| Layer | Tool | Question it answers |
|---|---|---|
| Unit tests | pytest | "Does my chunker split correctly? Does my guard block injection X?" |
| Eval (semantic) | Ragas | "Does the system answer faithfully and relevantly on a 30-Q golden set?" |
| Eval (behavioral) | Promptfoo | "Does it abstain on out-of-scope? Does it leak its system prompt?" |

`eval.yml` **fails the build** when faithfulness < 0.85 OR answer_relevancy < 0.80 OR
context_precision < 0.75 — same gating logic as Trivy/Checkov in MLOps CI, just with
semantic thresholds instead of CVE counts.

## 3. The threat model has new top entries

In MLOps, the OWASP-flavored worries are SQLi in the API, dependency CVEs, and exposed
secrets. In LLMOps, those still matter — and on top you get:

- **Prompt injection** (OWASP LLM01) — handled by `src/guards.py` with LLM Guard's
  `PromptInjection` scanner, tested with ≥ 10 known jailbreaks.
- **Data leakage / PII** (OWASP LLM06) — handled by `Anonymize` on the output side,
  redacting emails, phone numbers, names before the response leaves the API.
- **Supply chain of weights** — pinned model ID (`claude-sonnet-4-6`) and version-pinned
  SDK (`anthropic==0.40.0`) so a silent provider change doesn't ship without a code review.

## 4. Cost is a SLI, not a footnote

A scikit-learn model has predictable inference cost: it's CPU and milliseconds. A Claude call
is **dollars per million tokens**, and a sloppy RAG implementation will multiply that by
your context size on every turn. So this repo treats cost as a first-class signal:

- **Prompt caching** is enabled on the system prompt and the retrieved context — cache reads
  are billed at 0.1x the base rate, so a hot session pays roughly a tenth of what a naive
  implementation would.
- **Langfuse** records `cache_read_input_tokens` and `cache_creation_input_tokens` per call,
  so the cache hit ratio is observable next to latency, not buried in a billing dashboard.
- The `/eval` workflow could (and should, in v2) gate on a max-cost-per-query threshold, the
  same way `trivy` gates on CVE severity.

## TL;DR — the operational shift

| Concern | MLOps | LLMOps |
|---|---|---|
| Versioned artifact | model weights | prompt + retrieval recipe |
| Drift type | data drift | provider / prompt / retrieval drift |
| Gate beyond pytest | accuracy on holdout | Ragas + behavioral evals |
| Top OWASP risks | SQLi, deps, secrets | + prompt injection, PII leak |
| Cost shape | flat (compute) | per-token, retrieval-multiplied |
| Mitigation lever | retraining cadence | prompt caching + reranking + evals |

Same playbook (lint → test → scan → gate → deploy), new failure modes. That is the whole
point of this repo: prove that you don't throw out MLOps when you switch to LLMs — you
**extend** it.
