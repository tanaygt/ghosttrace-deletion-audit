"""Four independently authored counterfactual cases: no request, complete, leakage, historical ID."""
import csv,json,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from main import EvidenceCorpus

RULES='''rule_id,data_category,condition,required_action
r1,USER_PROFILE,Always,DELETE
r2,SECONDARY_IDENTIFIER,Always,DELETE
r3,SEARCH_INDEX_ENTRY,Always,DELETE
r4,CACHE_ENTRY,Always,DELETE
r5,SUPPORT_MESSAGE,Shared context,REDACT
r6,SUPPORT_ATTACHMENT,Subject only,DELETE
r7,ANALYTICS_PROFILE,Attributable,ANONYMIZE
r8,PRODUCT_TELEMETRY,Attributable,ANONYMIZE
r9,USER_EXPORT,Always,DELETE
r10,MARKETING_PROFILE,Always,DELETE
r11,EMAIL_DELIVERY_LOG,Email,REDACT
r12,SECURITY_AUDIT_LOG,Within retention,RETAIN
r13,LEGAL_HOLD_RECORD,Active,RETAIN
r14,BACKUP_ARCHIVE,Can block restore,RETAIN
r15,ACCOUNT_TOMBSTONE,Stable ID needed,REDACT
'''

def write(d,path,s):
    p=d/path;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(s,encoding="utf-8")

class AuditTests(unittest.TestCase):
    def setUp(self):
        # Use a deterministic workspace fixture directory. This also works in
        # runners that deny writes to both the OS temp directory and Python-
        # created subdirectories.
        self.temp=None
        self.root=Path(__file__).resolve().parent/'.runtime_fixture'
        self.root.mkdir(parents=True,exist_ok=True)
        d=self.root
        write(d,"deletion_rules.csv",RULES)
        write(d,"user_identities.csv","user_id,name,email,phone,email_hash,updated_at\nuser_1,Ada,ada@demo.test,+1001,hash1,2026-01-01T00:00:00Z\nuser_2,Ben,ben@demo.test,+1002,hash2,2026-01-01T00:00:00Z\n")
        write(d,"user_audit_log.csv","audit_id,user_id,event_time,field_name,old_value,new_value\na1,user_1,2026-01-10T00:00:00Z,email,ada.old@demo.test,ada@demo.test\n")
        write(d,"system_activity.csv","activity_id,event_time,event_type,source_system,target_system,resource_id,reported_result,details\n")
        write(d,"deletion_requests.csv","case_id,email,requested_at,reported_status,reported_at,audit_at,request_text\na,ada@demo.test,2026-03-01T00:00:00Z,COMPLETE,2026-03-02T00:00:00Z,2026-03-04T00:00:00Z,Delete my account and all personal data\nb,ben@demo.test,2026-03-01T00:00:00Z,COMPLETE,2026-03-02T00:00:00Z,2026-03-04T00:00:00Z,Please erase my account\nc,ben@demo.test,2026-03-01T00:00:00Z,COMPLETE,2026-03-02T00:00:00Z,2026-03-04T00:00:00Z,Do not delete my account; only change my email\nd,ada.old@demo.test,2026-03-01T00:00:00Z,NOT_STARTED,2026-03-02T00:00:00Z,2026-03-04T00:00:00Z,Please delete my personal information\n")
        manifest="file_id,file_path,origin,captured_at\ne1,evidence/a.json,snapshot,2026-03-04T00:00:00Z\ne2,evidence/b.sql,replica,2026-03-04T00:00:00Z\ne3,evidence/c.log,service_readback,2026-03-04T00:00:00Z\n"
        write(d,"evidence_files.csv",manifest)
        blob={"snapshots":[{"captured_at":"2026-03-04T00:00:00Z","data_store":"account_service","records":[{"resource_id":"account_1","subject_reference":"user_1","result":"NOT_FOUND"},{"resource_id":"account_2","subject_reference":"user_2","result":"FOUND"}]},{"data_store":"security_service","records":[{"resource_id":"audit_record_1","subject_reference":"user_1","result":"FOUND"}]},{"data_store":"integration_service","records":[{"resource_id":"data_flow_1","subject_reference":"user_1","enabled":False}]},{"data_store":"backup_service","records":[{"resource_id":"backup_1","subject_reference":"user_1","restore_allowed":False}]},{"data_store":"analytics_platform","records":[{"resource_id":"analytics_2","email":"ben@demo.test","result":"IDENTIFIABLE"}]},{"data_store":"support_platform","records":[{"resource_id":"support_2","requester_email":"ben@demo.test","result":"IDENTIFIABLE"}]}]}
        write(d,"evidence/a.json",json.dumps(blob))
        sql='''BEGIN TRANSACTION; CREATE TABLE customer_search_documents(resource_id TEXT, customer_reference TEXT, email TEXT); INSERT INTO customer_search_documents VALUES ('search_2', NULL, 'ben@demo.test'); COMMIT;'''
        write(d,"evidence/b.sql",sql)
        write(d,"evidence/c.log",'2026-03-04T00:00:00Z level=INFO service=integration_service resource_id=data_flow_2 trace_id=x event=connector_config_read_completed customer_email=ben@demo.test enabled=true\n2026-03-04T00:00:00Z level=INFO service=backup_service resource_id=backup_2 trace_id=y event=restore_policy_read_completed customer_email=ben@demo.test restore_allowed=true\n')
        self.c=EvidenceCorpus(self.root)
        self.by={r["case_id"]:self.c.audit_one(r) for r in self.c.requests}

    def tearDown(self):pass

    def test_complete_with_retained_security_and_blocked_backup(self):
        result=self.by['a'];self.assertEqual(result['deletion_status'],'COMPLETE')
        self.assertEqual([s['operation'] for s in json.loads(result['steps_json'])],["VERIFY_RECORD_ABSENT","VERIFY_RECORD_PRESENT","VERIFY_DATA_FLOW_DISABLED","VERIFY_RESTORE_BLOCKED"])

    def test_incomplete_multi_system_order(self):
        result=self.by['b'];self.assertEqual(result['deletion_status'],'INCOMPLETE')
        st=json.loads(result['steps_json'])
        self.assertEqual([s['operation'] for s in st[:3]],["REPORT_REMAINING_RECORD","REPORT_REMAINING_RECORD","REPORT_EXPOSED_PII"])
        self.assertEqual(st[0]['step_no'],1)
        self.assertEqual(st[-1]['step_no'],len(st))
        self.assertTrue(all(s['evidence_id']=='' for s in st if s['phase']=='REMEDIATION' or s['phase']=='VERIFICATION'))

    def test_not_applicable_never_authorizes_action(self):
        self.assertEqual(self.by['c']['deletion_status'],'NOT_APPLICABLE')
        self.assertEqual(self.by['c']['steps_json'],'[]')

    def test_old_email_links_to_same_user(self):
        self.assertEqual(self.by['d']['deletion_status'],'COMPLETE')
        self.assertTrue(json.loads(self.by['d']['steps_json']))

if __name__=='__main__':unittest.main()
