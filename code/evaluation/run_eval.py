"""Generate reproducible evaluation_report.md from the provided public sample and authored fixtures.
Run after cloning challenge repository: python code/evaluation/run_eval.py --dataset dataset
"""
from pathlib import Path
import argparse,json,sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from main import EvidenceCorpus,rows
from evaluate import load,metrics

def as_pct(v):return f'{100*v:.2f}%'

def main():
    p=argparse.ArgumentParser();p.add_argument('--dataset',type=Path,default=Path('dataset'));p.add_argument('--report',type=Path,default=Path('code/evaluation/evaluation_report.md'));p.add_argument('--vision',action='store_true');a=p.parse_args()
    corpus=EvidenceCorpus(a.dataset,vision=a.vision)
    sample=a.dataset/'sample_deletion_requests.csv'; gold_file=a.dataset/'sample_output.csv'
    if not sample.exists() or not gold_file.exists():raise SystemExit('Public sample CSVs are missing from the local dataset.')
    corpus.requests=rows(sample)
    # Keep the scratch file beside the report. Some restricted runners deny
    # writes to the operating-system temp directory even though the project
    # workspace is writable.
    predicted=a.report.parent/'.sample_preds.csv'
    try:
        corpus.run(predicted)
        m=metrics(load(gold_file),load(predicted))
    finally:
        try:predicted.unlink()
        except FileNotFoundError:pass
    from subprocess import run
    cmd=[sys.executable,str(Path(__file__).with_name('custom_eval.py'))]
    custom=run(cmd,capture_output=True,text=True,check=True)
    beginning=custom.stdout.split('CASE DIAGNOSTICS:')[0].strip()
    cm=json.loads(beginning)
    errors=[c for c in m['cases'] if not c['steps_exact'] or not c['status_match']]
    lines=[
       '# Evaluation Report', '',
       '## Public Sample (not used to build predictions)', '',
       f'- Evaluated sample cases: **{m["evaluated_cases"]}** (missing: {m["missing_predictions"]}).',
       f'- Case-level deletion status accuracy: **{as_pct(m["status_accuracy"])}**.',
       f'- Step-level exact-match precision / recall / F1: **{as_pct(m["step_precision"])} / {as_pct(m["step_recall"])} / {as_pct(m["step_f1"])}**.',
       f'- Field-level accuracy (position-aligned phase/system/resource/operation/state/evidence): **{as_pct(m["aligned_step_field_accuracy"])}**.',
       f'- Step-array exact match: **{as_pct(m["exact_step_array_accuracy"])}**.',
       f'- Full sequence including case status: **{as_pct(m["full_sequence_accuracy"])}**.',
       f'- Longest-common-subsequence coverage: **{as_pct(m["sequence_lcs_fraction"])}**.',
       '', '## Team-Created Evaluation Cases', '',
       '1. **Deleted profile + retained security evidence**: keep security record, ensure disabled integration and blocked backup.',
       '2. **Cross-system ghost**: primary, search, support, analytics, active connector and restorable backup; all phases ordered.',
       '3. **No deletion consent**: request explicitly asks not to delete; `NOT_APPLICABLE` and empty plan.',
       '4. **Historical identifier**: old email links to current user and retained security record.',
       '',
       f'Author-created case status accuracy: **{as_pct(cm["status_accuracy"])}**; step F1: **{as_pct(cm["step_f1"])}**; field accuracy: **{as_pct(cm["aligned_step_field_accuracy"])}**; full sequence accuracy: **{as_pct(cm["full_sequence_accuracy"])}**.',
       '', '## Failures Found (public sample)', '',
    ]
    if errors:
        for err in errors[:20]:lines.append(f'- `{err["case_id"]}`: status correct={err["status_match"]}, exact step sequence={err["steps_exact"]}, matching steps={err["matched_steps"]}/{err["gold_steps"]} gold, {err["pred_steps"]} predicted.')
    else:lines.append('- No mismatches detected on provided public sample.')
    lines += ['','## Failures Found and Improvements Made During Development','',
       '- Initial design sorted `case_id` strings lexicographically; changed to numeric-suffix case ordering.',
       '- SQL row `updated_at` can be older than the snapshot capture date; changed temporal priority to use evidence capture time.',
       '- Added historical email mapping, explicit account tombstones, and same-day replica-drift checks.',
       '- Prevented active-flow remediation from being ordered after record deletion by enforcing operation precedence.',
       '- Added a strict CSV schema and evidence-ID validator and four independent synthetic regression fixtures.',
       '', '## Known Limitations / Next Improvement Cycle', '',
       '- Screenshot OCR is environment-dependent; `--vision` enables optional screenshot VLM extraction after checking privacy and cost.',
       '- Activity results are not considered proof of final state; missing readback evidence may reduce recall.',
       '- Conflicting snapshot and replica observations need human review; the heuristic favors a contemporaneous unsafe replica.',
       '- This evaluation only assesses the supplied sample and authored cases, never the hidden judge answers.',
       '', '## Reproduction', '',
       '```bash',
       'python -m unittest discover -s code/tests -v',
       'python code/evaluation/custom_eval.py',
       'python code/evaluation/run_eval.py --dataset dataset',
       'python code/main.py --dataset dataset --output output.csv --usage-report code/evaluation/usage_report.md',
       'python code/validate.py --requests dataset/deletion_requests.csv --output output.csv',
       '```', ''
    ]
    a.report.parent.mkdir(parents=True,exist_ok=True)
    a.report.write_text('\n'.join(lines),encoding='utf-8')
    print(f'Evaluation report written: {a.report}')

if __name__=='__main__':main()
