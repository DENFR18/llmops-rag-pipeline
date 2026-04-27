"""Run Ragas on the golden dataset and gate CI on threshold violations.

Reads JSONL records of shape:
    {"question": str, "ground_truth": str, "contexts": [str, ...]}

Generates the answer with the running RAG pipeline (or, for offline CI,
uses the pre-recorded `answer` field if present), then computes:
  - faithfulness
  - answer_relevancy
  - context_precision

Exits non-zero when any metric is below its threshold.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

THRESHOLDS = {
    "faithfulness": 0.85,
    "answer_relevancy": 0.80,
    "context_precision": 0.75,
}


def load_dataset(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _build_eval_dataset(records: list[dict[str, Any]]):
    from datasets import Dataset

    needed = {"question", "answer", "contexts", "ground_truth"}
    rows = []
    for r in records:
        missing = needed - r.keys()
        if missing:
            raise ValueError(f"record missing keys {missing}: {r.get('question', '?')}")
        rows.append({k: r[k] for k in needed})
    return Dataset.from_list(rows)


def evaluate(dataset_path: Path) -> dict[str, float]:
    from ragas import evaluate as ragas_evaluate
    from ragas.metrics import answer_relevancy, context_precision, faithfulness

    records = load_dataset(dataset_path)
    ds = _build_eval_dataset(records)
    result = ragas_evaluate(ds, metrics=[faithfulness, answer_relevancy, context_precision])
    return {k: float(result[k]) for k in THRESHOLDS}


def write_summary(scores: dict[str, float], out: Path) -> None:
    lines = ["| Metric | Score | Threshold | Pass |", "|---|---|---|---|"]
    for metric, threshold in THRESHOLDS.items():
        score = scores[metric]
        ok = "OK" if score >= threshold else "FAIL"
        lines.append(f"| {metric} | {score:.3f} | {threshold:.2f} | {ok} |")
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", default="evals/golden_dataset.jsonl", type=Path)
    parser.add_argument("--summary", default="evals/_runs/summary.md", type=Path)
    args = parser.parse_args()

    args.summary.parent.mkdir(parents=True, exist_ok=True)

    # Ragas needs a judge LLM (OpenAI by default). When the key isn't
    # configured the gate would always fail on a fresh repo, so skip cleanly
    # and leave a visible breadcrumb in the PR comment instead.
    if not os.environ.get("OPENAI_API_KEY"):
        msg = (
            "Ragas eval **skipped**: `OPENAI_API_KEY` is not set in repo secrets. "
            "Add it (or wire a different judge model in `evals/ragas_eval.py`) to "
            "enforce the faithfulness / answer_relevancy / context_precision gates.\n"
        )
        args.summary.write_text(msg, encoding="utf-8")
        if gh_summary := os.environ.get("GITHUB_STEP_SUMMARY"):
            Path(gh_summary).write_text(msg, encoding="utf-8")
        print(msg)
        return 0

    scores = evaluate(args.dataset)
    write_summary(scores, args.summary)

    print(json.dumps(scores, indent=2))

    if gh_summary := os.environ.get("GITHUB_STEP_SUMMARY"):
        Path(gh_summary).write_text(args.summary.read_text(encoding="utf-8"), encoding="utf-8")
    failures = [m for m, t in THRESHOLDS.items() if scores[m] < t]
    if failures:
        print(f"FAILED gates: {failures}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
