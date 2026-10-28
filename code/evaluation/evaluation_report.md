# Evaluation Report

## Public Sample (not used to build predictions)

- Evaluated sample cases: **32** (missing: 0).
- Case-level deletion status accuracy: **96.88%**.
- Step-level exact-match precision / recall / F1: **79.52% / 68.39% / 73.54%**.
- Field-level accuracy (position-aligned phase/system/resource/operation/state/evidence): **65.64%**.
- Step-array exact match: **34.38%**.
- Full sequence including case status: **34.38%**.
- Longest-common-subsequence coverage: **68.04%**.

## Team-Created Evaluation Cases

1. **Deleted profile + retained security evidence**: keep security record, ensure disabled integration and blocked backup.
2. **Cross-system ghost**: primary, search, support, analytics, active connector and restorable backup; all phases ordered.
3. **No deletion consent**: request explicitly asks not to delete; `NOT_APPLICABLE` and empty plan.
4. **Historical identifier**: old email links to current user and retained security record.

Author-created case status accuracy: **100.00%**; step F1: **100.00%**; field accuracy: **100.00%**; full sequence accuracy: **100.00%**.

## Failures Found (public sample)

- `case_03`: status correct=True, exact step sequence=False, matching steps=2/3 gold, 2 predicted.
- `case_04`: status correct=True, exact step sequence=False, matching steps=0/2 gold, 0 predicted.
- `case_07`: status correct=False, exact step sequence=False, matching steps=0/4 gold, 1 predicted.
- `case_09`: status correct=True, exact step sequence=False, matching steps=3/5 gold, 3 predicted.
- `case_10`: status correct=True, exact step sequence=False, matching steps=1/4 gold, 4 predicted.
- `case_12`: status correct=True, exact step sequence=False, matching steps=2/5 gold, 5 predicted.
- `case_17`: status correct=True, exact step sequence=False, matching steps=5/5 gold, 6 predicted.
- `case_18`: status correct=True, exact step sequence=False, matching steps=12/14 gold, 13 predicted.
- `case_20`: status correct=True, exact step sequence=False, matching steps=6/8 gold, 7 predicted.
- `case_21`: status correct=True, exact step sequence=False, matching steps=0/3 gold, 1 predicted.
- `case_22`: status correct=True, exact step sequence=False, matching steps=7/8 gold, 7 predicted.
- `case_23`: status correct=True, exact step sequence=False, matching steps=5/8 gold, 7 predicted.
- `case_24`: status correct=True, exact step sequence=False, matching steps=5/7 gold, 7 predicted.
- `case_25`: status correct=True, exact step sequence=False, matching steps=0/3 gold, 1 predicted.
- `case_26`: status correct=True, exact step sequence=False, matching steps=1/6 gold, 5 predicted.
- `case_27`: status correct=True, exact step sequence=False, matching steps=1/6 gold, 5 predicted.
- `case_28`: status correct=True, exact step sequence=False, matching steps=0/6 gold, 4 predicted.
- `case_29`: status correct=True, exact step sequence=False, matching steps=8/14 gold, 11 predicted.
- `case_30`: status correct=True, exact step sequence=False, matching steps=8/14 gold, 11 predicted.
- `case_31`: status correct=True, exact step sequence=False, matching steps=2/3 gold, 2 predicted.

## Failures Found and Improvements Made During Development

- Initial design sorted `case_id` strings lexicographically; changed to numeric-suffix case ordering.
- SQL row `updated_at` can be older than the snapshot capture date; changed temporal priority to use evidence capture time.
- Added historical email mapping, explicit account tombstones, and same-day replica-drift checks.
- Prevented active-flow remediation from being ordered after record deletion by enforcing operation precedence.
- Added a strict CSV schema and evidence-ID validator and four independent synthetic regression fixtures.

## Known Limitations / Next Improvement Cycle

- Screenshot OCR is environment-dependent; `--vision` enables optional screenshot VLM extraction after checking privacy and cost.
- Activity results are not considered proof of final state; missing readback evidence may reduce recall.
- Conflicting snapshot and replica observations need human review; the heuristic favors a contemporaneous unsafe replica.
- This evaluation only assesses the supplied sample and authored cases, never the hidden judge answers.

## Reproduction

```bash
python -m unittest discover -s code/tests -v
python code/evaluation/custom_eval.py
python code/evaluation/run_eval.py --dataset dataset
python code/main.py --dataset dataset --output output.csv --usage-report code/evaluation/usage_report.md
python code/validate.py --requests dataset/deletion_requests.csv --output output.csv
```
