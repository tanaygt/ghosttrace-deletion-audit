"""Four manually specified synthetic golden cases; not copied from contest labels."""
import sys,json
from pathlib import Path
code=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(code))
sys.path.insert(0,str(code/'tests'))
from test_agent import AuditTests
from evaluate import metrics

# Each tuple: operation, resource, system, state, evidence for the first case.
def mk(phase,tuples):
    return [dict(phase=phase,operation=op,resource_id=rid,system_id=system,state=state,evidence_id=eid) for op,rid,system,state,eid in tuples]

def seq(groups):
    steps=[]
    for phase,items in groups:
        for x in mk(phase,items):
            x['step_no']=len(steps)+1
            steps.append(x)
    return steps

A=seq([('VERIFICATION',[
    ('VERIFY_RECORD_ABSENT','account_1','account_service','ABSENT','e1'),
    ('VERIFY_RECORD_PRESENT','audit_record_1','security_service','PRESENT','e1'),
    ('VERIFY_DATA_FLOW_DISABLED','data_flow_1','integration_service','DISABLED','e1'),
    ('VERIFY_RESTORE_BLOCKED','backup_1','backup_service','BLOCKED','e1')])])
B=seq([
 ('FINDING',[
  ('REPORT_REMAINING_RECORD','account_2','account_service','PRESENT','e1'),
  ('REPORT_REMAINING_RECORD','search_2','search_service','PRESENT','e2'),
  ('REPORT_EXPOSED_PII','analytics_2','analytics_platform','PRESENT','e1'),
  ('REPORT_EXPOSED_PII','support_2','support_platform','PRESENT','e1'),
  ('REPORT_ACTIVE_DATA_FLOW','data_flow_2','integration_service','ACTIVE','e3'),
  ('REPORT_RESTORE_RISK','backup_2','backup_service','ACTIVE','e3')]),
 ('REMEDIATION',[
  ('DISABLE_DATA_FLOW','data_flow_2','integration_service','DISABLED',''),
  ('BLOCK_RESTORE','backup_2','backup_service','BLOCKED',''),
  ('DELETE_RECORD','account_2','account_service','ABSENT',''),
  ('DELETE_RECORD','search_2','search_service','ABSENT',''),
  ('REDACT_RECORD','support_2','support_platform','REDACTED',''),
  ('ANONYMIZE_RECORD','analytics_2','analytics_platform','ANONYMIZED','')]),
 ('VERIFICATION',[
  ('VERIFY_RECORD_ABSENT','account_2','account_service','ABSENT',''),
  ('VERIFY_RECORD_ABSENT','search_2','search_service','ABSENT',''),
  ('VERIFY_RECORD_REDACTED','support_2','support_platform','REDACTED',''),
  ('VERIFY_RECORD_ANONYMIZED','analytics_2','analytics_platform','ANONYMIZED',''),
  ('VERIFY_DATA_FLOW_DISABLED','data_flow_2','integration_service','DISABLED',''),
  ('VERIFY_RESTORE_BLOCKED','backup_2','backup_service','BLOCKED','')])])

if __name__=='__main__':
    fixture=AuditTests('test_old_email_links_to_same_user')
    fixture.setUp()
    try:
        gold={'a':{'status':'COMPLETE','steps':A},'b':{'status':'INCOMPLETE','steps':B},'c':{'status':'NOT_APPLICABLE','steps':[]},'d':{'status':'COMPLETE','steps':A}}
        pred={k:{'status':v['deletion_status'],'steps':json.loads(v['steps_json'])} for k,v in fixture.by.items()}
        m=metrics(gold,pred)
        print(json.dumps({k:v for k,v in m.items() if k!='cases'},indent=2))
        print('CASE DIAGNOSTICS:',m['cases'])
    finally:fixture.tearDown()
