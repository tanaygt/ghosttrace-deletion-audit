"""Strict validator for the required submission CSV."""
import argparse,csv,json,re
from pathlib import Path
from main import OPS,PHASES,OP_RANK,case_sort_key
VALID_STATUSES={'COMPLETE','INCOMPLETE','NOT_APPLICABLE'}
FIELDS={'step_no','phase','system_id','resource_id','operation','state','evidence_id'}
STATES={"REPORT_REMAINING_RECORD":"PRESENT","REPORT_EXPOSED_PII":"PRESENT","REPORT_ACTIVE_DATA_FLOW":"ACTIVE","REPORT_RESTORE_RISK":"ACTIVE","DISABLE_DATA_FLOW":"DISABLED","BLOCK_RESTORE":"BLOCKED","DELETE_RECORD":"ABSENT","REDACT_RECORD":"REDACTED","ANONYMIZE_RECORD":"ANONYMIZED","VERIFY_RECORD_ABSENT":"ABSENT","VERIFY_RECORD_PRESENT":"PRESENT","VERIFY_RECORD_REDACTED":"REDACTED","VERIFY_RECORD_ANONYMIZED":"ANONYMIZED","VERIFY_DATA_FLOW_DISABLED":"DISABLED","VERIFY_RESTORE_BLOCKED":"BLOCKED"}

def read(path):
    with open(path,encoding='utf-8-sig',newline='') as f:
        r=csv.DictReader(f)
        if r.fieldnames!=['case_id','deletion_status','steps_json']:raise AssertionError(f'Wrong columns: {r.fieldnames}')
        return list(r)

def validate(output:Path,requests:Path):
    data=read(output)
    with requests.open(newline='',encoding='utf-8-sig') as f: expected=[r['case_id'] for r in csv.DictReader(f)]
    got=[r['case_id'] for r in data]
    assert sorted(got)==sorted(expected) and len(got)==len(set(got)),f'Case mismatch: {len(got)} vs {len(expected)}'
    assert got==sorted(got,key=lambda cid:case_sort_key({'case_id':cid})),'Cases not in numeric case_id order'
    for r in data:
        cid=r['case_id'];status=r['deletion_status']
        assert status in VALID_STATUSES,(cid,'invalid status')
        steps=json.loads(r['steps_json'])
        assert isinstance(steps,list),(cid,'not an array')
        assert (not steps) if status=='NOT_APPLICABLE' else True,(cid,'unauthorized steps')
        keys=[]
        for i,s in enumerate(steps,1):
            assert isinstance(s,dict) and set(s)==FIELDS,(cid,i,'keys')
            assert s['step_no']==i,(cid,i,'step number')
            assert s['operation'] in OPS and s['state']==STATES[s['operation']],(cid,i,'operation/state')
            phase=s['phase'];op=s['operation']
            assert phase in PHASES,(cid,i,'phase')
            assert (phase=='FINDING')==(op.startswith('REPORT_')) or (phase!='FINDING' and not op.startswith('REPORT_')),(cid,i,'phase/operation')
            assert (phase=='REMEDIATION')==(op in {'DISABLE_DATA_FLOW','BLOCK_RESTORE','DELETE_RECORD','REDACT_RECORD','ANONYMIZE_RECORD'}) or (phase!='REMEDIATION' and op not in {'DISABLE_DATA_FLOW','BLOCK_RESTORE','DELETE_RECORD','REDACT_RECORD','ANONYMIZE_RECORD'}),(cid,i,'phase/operation')
            assert s['evidence_id'] if (phase=='FINDING' or status=='COMPLETE' and phase=='VERIFICATION') else s['evidence_id']=='', (cid,i,'evidence rules')
            keys.append((PHASES[phase],OP_RANK[op],s['system_id'],s['resource_id']))
        assert keys==sorted(keys),(cid,'out of order')
        if status=='COMPLETE':assert all(s['phase']=='VERIFICATION' for s in steps),(cid,'complete must only verify')
        if status=='INCOMPLETE':assert any(s['phase']=='FINDING' for s in steps),(cid,'incomplete missing findings')
    return len(data)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,default=Path('output.csv'));p.add_argument('--requests',type=Path,default=Path('dataset/deletion_requests.csv'))
    args=p.parse_args();print(f'PASS {validate(args.output,args.requests)} rows')
