"""Reference answer evaluator: python code/evaluation/evaluate.py --pred output.csv --gold dataset/sample_output.csv
Computes status accuracy, exact-step set F1, field accuracy, and sequence accuracy.
"""
import argparse,csv,json
from collections import Counter
from pathlib import Path

FIELDS=("phase","system_id","resource_id","operation","state","evidence_id")

def load(path):
    with open(path,encoding="utf-8-sig",newline="") as f:
        return {r["case_id"]:{"status":r["deletion_status"],"steps":json.loads(r["steps_json"])} for r in csv.DictReader(f)}

def identity(step):return tuple(step.get(k,"") for k in FIELDS)

def lcs(a,b):
    dp=[0]*(len(b)+1)
    for x in a:
        old=dp[:]
        for j,y in enumerate(b,1):dp[j]=old[j-1]+1 if x==y else max(old[j],dp[j-1])
    return dp[-1]

def metrics(gold,pred):
    common=set(gold)&set(pred)
    status=sum(gold[c]["status"]==pred[c]["status"] for c in common)
    exact=0; seq=0; nfield=0; rightfield=0; tp=fp=fn=0; lcs_sum=0; longest=0
    per=[]
    for cid in sorted(common):
        g=gold[cid];p=pred[cid]
        gs=[identity(s) for s in g["steps"]];ps=[identity(s) for s in p["steps"]]
        exact+=gs==ps
        seq+=gs==ps and g["status"]==p["status"]
        gc=Counter(gs);pc=Counter(ps);hit=sum((gc&pc).values())
        tp+=hit;fp+=len(ps)-hit;fn+=len(gs)-hit
        matched=lcs(gs,ps); lcs_sum+=matched;longest+=max(len(gs),len(ps))
        for i in range(max(len(gs),len(ps))):
            for field in FIELDS:
                nfield+=1
                if i<len(g["steps"]) and i<len(p["steps"]) and g["steps"][i].get(field)==p["steps"][i].get(field):rightfield+=1
        per.append({"case_id":cid,"status_match":g["status"]==p["status"],"steps_exact":gs==ps,"gold_steps":len(gs),"pred_steps":len(ps),"matched_steps":hit})
    precision=tp/(tp+fp) if tp+fp else 1
    recall=tp/(tp+fn) if tp+fn else 1
    return {"evaluated_cases":len(common),"missing_predictions":len(gold)-len(common),"status_accuracy":status/len(common) if common else 0,"exact_step_array_accuracy":exact/len(common) if common else 0,"full_sequence_accuracy":seq/len(common) if common else 0,"step_precision":precision,"step_recall":recall,"step_f1":2*precision*recall/(precision+recall) if precision+recall else 0,"aligned_step_field_accuracy":rightfield/nfield if nfield else 1,"sequence_lcs_fraction":lcs_sum/longest if longest else 1,"cases":per}

if __name__=="__main__":
    a=argparse.ArgumentParser();a.add_argument("--pred",type=Path,required=True);a.add_argument("--gold",type=Path,required=True);a.add_argument("--json",type=Path,default=None);o=a.parse_args()
    result=metrics(load(o.gold),load(o.pred))
    print(json.dumps({k:v for k,v in result.items() if k!="cases"},indent=2))
    if o.json:o.json.write_text(json.dumps(result,indent=2)+"\n")
