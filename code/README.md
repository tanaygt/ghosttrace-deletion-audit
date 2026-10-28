# GhostTrace — An Evidence-First Deletion Audit Agent

A runnable, explainable deletion-audit agent for HackerRank Orchestrate October 2026. It evaluates each request from local evidence **as of its own `audit_at`**, not from a reported workflow status. It never performs real deletions: it writes an ordered remediation plan.

## Fastest way to run

1. Clone the official [participant repository](https://github.com/interviewstreet/hackerrank-orchestrate-october26), or open your existing clone. The `dataset/` folder must remain next to `code/`.
2. Copy this `code/` folder into the repository root, replacing the starter `code/main.py`.
3. Install `poppler-utils` (`pdftotext`) and `tesseract-ocr` to inspect PDFs and screenshot evidence. The core pipeline itself uses only Python 3.10+ standard library packages.
4. From the repository root run:

```bash
python code/main.py --dataset dataset --output output.csv --usage-report code/evaluation/usage_report.md
python code/validate.py --requests dataset/deletion_requests.csv --output output.csv
python -m unittest discover -s code/tests -v
python code/evaluation/run_eval.py --dataset dataset
```

The first command produces the **actual 518-case** `output.csv` if the official `dataset/` is present and complete. The validator enforces exact CSV columns, one row per case, permitted operations and states, numeric case sorting, ordered phases, consecutive steps and evidence-reference rules.

Optional cloud AI enrichment:

```bash
python -m pip install openai
# Set OPENAI_API_KEY in your environment, not in source or your submission.
python code/main.py --vision --llm-intent --dataset dataset --output output.csv \
  --usage-report code/evaluation/usage_report.md
```

`--vision` sends admin screenshot images to the configured OpenAI vision model. Use only after reviewing your organization's privacy policy; this is not required for local execution. `--llm-intent` invokes a model only for otherwise ambiguous request language after masking direct email addresses. Models may hallucinate and are treated as lower-quality evidence than structured readbacks. Default runtime uses a fully local deterministic evidence engine with no external model calls or API charges.

To calculate paid API cost in the usage report, set `MODEL_INPUT_PRICE_PER_MILLION` and `MODEL_OUTPUT_PRICE_PER_MILLION` to current USD rates; otherwise report estimates are explicitly zero-rate. Runtime token usage excludes the ChatGPT development conversation.

## Pipeline

1. **Request authorization**: distinguish deletion instructions and audits from non-deletion tasks; do not rely on `reported_status`.
2. **Identity graph**: resolve case email against `user_identities.csv` and both old/new values from `user_audit_log.csv`. Normalize case consistently but **never fuzzy-match similar email addresses**.
3. **Evidence intake**: parse timestamped JSON snapshots, SQL inventory/replica snapshots via in-memory SQLite, structured service readback logs, handover text, PDF embedded text and optional screenshot OCR/VLM. Map each observation to the supplied `evidence_files.csv` file ID.
4. **Point-in-time reconstruction**: link resources to identities and resource IDs across sources; ignore events after the request's audit cutoff; favor latest direct readbacks while detecting dangerous concurrent replica drift.
5. **Policy engine**: use `deletion_rules.csv` to choose deletion/redaction/anonymization/retention and prevent active sync and backup restoration. Account tombstones retain stable internal IDs while scrubbing prohibited direct identifiers.
6. **Plan & verification compiler**: emit ordered findings, remediation, and evidence-backed verification steps. Completed cases contain verification only. Incomplete cases use empty evidence IDs for proposed actions and future checks.
7. **Independent evaluation**: compare against published **sample** answers (never consulted at prediction time) and four independently authored counterfactual cases; summarize status, exact step/field matches and sequence errors in `code/evaluation/evaluation_report.md`.

## Dataset, output, and packaging

All input is read **only at runtime** from the official `dataset/` directory. The code package intentionally excludes the corpus and participant labels. The final predictions file has exactly these columns:

```
case_id,deletion_status,steps_json
```

Run on the official dataset, then zip `code/` (without `dataset/`, venv, or caches). Upload the generated root-level `output.csv`, `code.zip`, and authentic `log.txt` to [the official HackerRank challenge](https://www.hackerrank.com/contests/hackerrank-orchestrate-october26/challenges/ghost-data-still-exists). The supplied transcript in this ChatGPT work product is a development-session reconstruction; participants should replace/supplement it with their coding tool's original append-only `log.txt` for submission.

## Design decisions and limitations

- Account-service or worker `SUCCESS` events **are not deletion proof**; direct present/absent evidence is authoritative.
- Only category-specific allowed remediation is emitted; security and legal retention records are not casually deleted.
- Local OCR may miss screenshot-only fields. Optional cloud VLM enrichment is available; default results should be manually inspected on samples before submission.
- Time conflicts, identity reuse, incomplete snapshots and retention expiry are inherently challenging. This is a baseline agent with transparent, testable heuristics, not a certification of real-world erasure.
- No hardcoded case IDs, ground-truth results or test-set answers exist in production `main.py`.

## Interview explanation

The novel piece is a **temporal identity-to-resource evidence graph** with policy compilation and ordered proof obligations. Each action is explainable by a resource, legal/data policy rule and evidence reference. The agent separates the *desired state* from an unreliable workflow claim, and avoids the common failure of deleting records protected by a retention rule. LLMs can assist ambiguous input and visual intake without controlling deterministic ordering or destructive actions.
