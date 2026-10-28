"""Ghost Data Still Exists: evidence-first deletion audit engine.

Usage: python code/main.py --dataset dataset --output output.csv
No credentials required. Optional LLM intent fallback: OPENAI_API_KEY and --llm-intent.
This is an audit and remediation *proposal*, never a destructive executor.
"""
from __future__ import annotations
import argparse
import base64
import collections
import csv
import dataclasses
from datetime import datetime,timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import sqlite3
import subprocess
import sys
from typing import Any

PHASES = {"FINDING": 0, "REMEDIATION": 1, "VERIFICATION": 2}
OPS = ["REPORT_REMAINING_RECORD", "REPORT_EXPOSED_PII", "REPORT_ACTIVE_DATA_FLOW", "REPORT_RESTORE_RISK", "DISABLE_DATA_FLOW", "BLOCK_RESTORE", "DELETE_RECORD", "REDACT_RECORD", "ANONYMIZE_RECORD", "VERIFY_RECORD_ABSENT", "VERIFY_RECORD_PRESENT", "VERIFY_RECORD_REDACTED", "VERIFY_RECORD_ANONYMIZED", "VERIFY_DATA_FLOW_DISABLED", "VERIFY_RESTORE_BLOCKED"]
OP_RANK = {n:i for i,n in enumerate(OPS)}
PREFIX_CATEGORY = {"account_":"USER_PROFILE","tombstone_":"ACCOUNT_TOMBSTONE","search_":"SEARCH_INDEX_ENTRY","analytics_":"ANALYTICS_PROFILE","support_":"SUPPORT_MESSAGE","export_":"USER_EXPORT","data_flow_":"DATA_FLOW","backup_":"BACKUP_ARCHIVE","audit_record_":"SECURITY_AUDIT_LOG","cache_":"CACHE_ENTRY","secondary_":"SECONDARY_IDENTIFIER","marketing_":"MARKETING_PROFILE","telemetry_":"PRODUCT_TELEMETRY","email_delivery_":"EMAIL_DELIVERY_LOG","legal_":"LEGAL_HOLD_RECORD"}
PREFIX_SYSTEM = {"account_":"account_service","tombstone_":"identity_service","search_":"search_service","analytics_":"analytics_platform","support_":"support_platform","export_":"export_service","data_flow_":"integration_service","backup_":"backup_service","audit_record_":"security_service","cache_":"cache_service","marketing_":"marketing_service","telemetry_":"telemetry_service","email_delivery_":"email_delivery_service","legal_":"legal_service"}
COL_CATEGORY = {"customer_profiles":"USER_PROFILE","customer_search_documents":"SEARCH_INDEX_ENTRY","customer_analytics_reports":"ANALYTICS_PROFILE","customer_analytics_profiles":"ANALYTICS_PROFILE","support_records":"SUPPORT_MESSAGE","support_messages":"SUPPORT_MESSAGE","support_attachments":"SUPPORT_ATTACHMENT","customer_export_jobs":"USER_EXPORT","customer_exports":"USER_EXPORT","connector_subscriptions":"DATA_FLOW","backup_restore_entries":"BACKUP_ARCHIVE","backup_catalog":"BACKUP_ARCHIVE","security_audit_records":"SECURITY_AUDIT_LOG","customer_search_index":"SEARCH_INDEX_ENTRY"}
NOT_FOUND = {"NOT_FOUND", "ABSENT", "DELETED", "404", "MISSING", "NO_MATCH", "NO_RESULTS"}
PRESENT = {"FOUND", "PRESENT", "ACTIVE", "IDENTIFIABLE", "HIT", "EXISTS", "SUCCESS", "200", "PARTIAL"}
DIRECT_FIELDS = {"email","email_hash","phone","full_name","display_name","requester_name","requester_email","requester_phone","owner_email","owner_phone","customer_email","customer_phone","name","matched_value","correlation_key"}
REFERENCE_FIELDS = {"user_id","subject_reference","subject_ref","customer_reference","subject_selector","lookup_key","match_key","subject_key","owner_key","account_user_id"}
ALL_IDENTITY_FIELDS = DIRECT_FIELDS | REFERENCE_FIELDS
KV_RE = re.compile(r'([a-zA-Z_][\w.-]*)=("[^"]*"|\'[^\']*\'|\S+)')
RESOURCE_RE = re.compile(r'\b(?:account|tombstone|search|analytics|support|export|data_flow|backup|audit_record|cache|marketing|telemetry|email_delivery|legal|secondary)_[a-zA-Z0-9]+\b', re.I)


def norm(value: Any) -> str:
    if value is None or isinstance(value,(dict,list)):return ""
    s = str(value).strip().strip('"\'').lower()
    return s if s not in {"none","null","nan","n/a","no direct identifier","", "-"} else ""


def asbool(value: Any) -> bool | None:
    if isinstance(value,bool):return value
    if isinstance(value,int):return bool(value)
    s = norm(value)
    if s in {"1","true","yes","enabled","active","allowed"}: return True
    if s in {"0","false","no","disabled","stopped","blocked"}: return False
    return None


def rows(path: Path) -> list[dict]:
    with path.open(encoding="utf-8-sig",newline="") as f:return list(csv.DictReader(f))


def time_ok(at: str, audit: str) -> bool:
    return not at or at[:20] <= audit[:20]


def tokens_of(v: Any, allowed_fields: set[str] | None = None) -> set[str]:
    # Extract only canonical identity fields. No fuzzy matching of similar emails.
    out: set[str] = set()
    if isinstance(v,dict):
        for k,val in v.items():
            key=str(k).lower()
            if key in (allowed_fields or ALL_IDENTITY_FIELDS):
                if isinstance(val,(str,int)):out.add(norm(val))
            if isinstance(val,(dict,list)):out |= tokens_of(val,allowed_fields)
    elif isinstance(v,list):
        for it in v:out |= tokens_of(it,allowed_fields)
    return {x for x in out if x and len(x)>2}


def system_for(resource: str, fallback: str="") -> str:
    return next((s for p,s in PREFIX_SYSTEM.items() if resource.startswith(p)),fallback or "unknown_service")


def category_for(resource: str, collection: str="", fallback: str="") -> str:
    return (fallback if fallback and fallback not in {"DATA_RECORD", "UNKNOWN"} else None) or COL_CATEGORY.get(collection) or next((v for p,v in PREFIX_CATEGORY.items() if resource.startswith(p)), "UNKNOWN")


def implied_state(category: str, obj: dict, explicit: str="") -> str:
    e = str(explicit or obj.get("result") or obj.get("status") or obj.get("state") or "").upper()
    if e in NOT_FOUND:return "ABSENT"
    if category=="ACCOUNT_TOMBSTONE":
        # A permitted stable user reference is not itself prohibited direct PII.
        return "IDENTIFIABLE" if tokens_of(obj,DIRECT_FIELDS) else "REDACTED"
    if e in {"REDACTED", "ANONYMIZED", "DISABLED", "BLOCKED", "IDENTIFIABLE", "PRESENT"}:return e
    if category == "DATA_FLOW":
        b=asbool(obj.get("enabled"))
        return "ACTIVE" if b else "DISABLED" if b is False else ("ACTIVE" if e=="ACTIVE" else "UNKNOWN")
    if category=="BACKUP_ARCHIVE":
        b=asbool(obj.get("restore_allowed"))
        return "ACTIVE" if b else "BLOCKED" if b is False else ("ACTIVE" if e=="ACTIVE" else "UNKNOWN")
    if category in {"ANALYTICS_PROFILE","PRODUCT_TELEMETRY"}:
        ids=tokens_of(obj, ALL_IDENTITY_FIELDS)
        # For readbacks, identity can be absent even if user_id was formerly associated with resource.
        return "IDENTIFIABLE" if ids else "ANONYMIZED"
    if category in {"SUPPORT_MESSAGE","EMAIL_DELIVERY_LOG","ACCOUNT_TOMBSTONE"}:
        direct=tokens_of(obj,DIRECT_FIELDS)
        return "IDENTIFIABLE" if direct else "REDACTED"
    if category in {"USER_PROFILE","ACCOUNT_TOMBSTONE"} and any(t in norm(obj.get("account_status")) for t in ("deleted","tombstone")):
        return "IDENTIFIABLE" if tokens_of(obj,DIRECT_FIELDS) else "REDACTED"
    if e in PRESENT:return "PRESENT"
    return "PRESENT" if obj else "UNKNOWN"


@dataclasses.dataclass(frozen=True)
class Observation:
    resource: str
    system: str
    category: str
    state: str
    at: str
    evidence: str
    tokens: frozenset[str]
    quality: int = 2
    topology: str = ""
    source: str = ""


class EvidenceCorpus:
    def __init__(self,dataset: Path,vision: bool=False):
        self.dataset=dataset
        self.vision=vision
        self.model_usage=[]
        self.rules = {x["data_category"]:x["required_action"] for x in rows(dataset/"deletion_rules.csv")}
        self.requests=rows(dataset/"deletion_requests.csv")
        self.people=rows(dataset/"user_identities.csv")
        self.audit=rows(dataset/"user_audit_log.csv")
        self.activity=rows(dataset/"system_activity.csv")
        self.manifest=rows(dataset/"evidence_files.csv")
        self.observations: list[Observation]=[]
        self.by_resource: dict[str,list[Observation]]=collections.defaultdict(list)
        self.identities: dict[str,set[str]]={}
        self.token_users: dict[str,set[str]]=collections.defaultdict(set)
        self.user_resources: dict[str,set[str]]=collections.defaultdict(set)
        self._build_identity()
        self._read_evidence()
        self._index_resources()

    def _build_identity(self):
        for x in self.people:
            uid=norm(x["user_id"])
            toks={uid}
            for f in ("email","phone","email_hash","name"):
                if norm(x.get(f)):toks.add(norm(x[f]))
            self.identities[uid]=toks
        for x in self.audit:
            uid=norm(x["user_id"])
            if uid not in self.identities:self.identities[uid]={uid}
            for f in ("old_value","new_value"):
                if norm(x.get(f)):self.identities[uid].add(norm(x[f]))
        for uid,toks in self.identities.items():
            for tok in toks:self.token_users[tok].add(uid)

    def add(self,resource,system,category,state,at,evidence,tokens,quality=2,topology="",source=""):
        resource=norm(resource)
        if not resource or not RESOURCE_RE.fullmatch(resource):return
        o=Observation(resource,system_for(resource,norm(system)),category_for(resource,norm(category),category if category in self.rules else ""),str(state or "UNKNOWN").upper(),at or "",evidence,frozenset({norm(t) for t in tokens if norm(t)}),quality,topology,source)
        self.observations.append(o)
        self.by_resource[resource].append(o)

    def _json_walk(self,x:Any,eid:str,at:str,system:str="",collection:str="",topology:str="",source:str=""):
        if isinstance(x,list):
            for row in x:self._json_walk(row,eid,at,system,collection,topology,source)
            return
        if not isinstance(x,dict):return
        cur_at=x.get("observed_at") or x.get("captured_at") or x.get("recorded_at") or at
        # snapshot captured_at is sometimes nested; always favor the nearest observation time.
        cur_sys=x.get("data_store") or x.get("system") or x.get("origin_system") or system
        cur_col=x.get("record_type") or x.get("collection") or x.get("collection_name") or collection
        cur_top=x.get("topology") or x.get("database_topology") or topology
        rid=str(x.get("resource_id") or "")
        if RESOURCE_RE.fullmatch(rid):
            category=category_for(rid,str(cur_col),str(x.get("record_type") or ""))
            obs_obj=dict(x)
            if isinstance(x.get("record_json"),str):
                try:obs_obj.update(json.loads(x["record_json"]))
                except (json.JSONDecodeError,TypeError):pass
            explicit=x.get("result") or x.get("state") or x.get("status") or ""
            if "status_code" in x:
                explicit="ABSENT" if str(x["status_code"])=="404" else "PRESENT"
            if "rows" in x and str(x["rows"])=="0":explicit="ABSENT"
            if "total_hits" in x:explicit="PRESENT" if int(x["total_hits"])>0 else "ABSENT"
            if x.get("profile") is None and "profile" in x: explicit="ABSENT"
            if x.get("hits") and isinstance(x["hits"],dict) and "total" in x["hits"]:
                explicit="PRESENT" if int(x["hits"]["total"]) else "ABSENT"
            if category=="USER_PROFILE" and any(t in norm(obs_obj.get("account_status")) for t in ("deleted","tombstone")):category="ACCOUNT_TOMBSTONE"
            st=implied_state(category,obs_obj,str(explicit))
            self.add(rid,cur_sys,category,st,cur_at,eid,tokens_of(obs_obj),3,cur_top,source)
        # propagate service_exports keys as system scopes
        for k,v in x.items():
            if isinstance(v,(dict,list)):
                next_sys=k if k.endswith("_service") or k in {"analytics_platform","support_platform","integration_service"} else cur_sys
                self._json_walk(v,eid,cur_at,next_sys,cur_col,cur_top,source)

    def _read_json(self,p:Path,eid:str,at:str):
        try:self._json_walk(json.loads(p.read_text(encoding="utf-8")),eid,at,source=p.name)
        except (ValueError,UnicodeError) as e:print(f"Warning: JSON {p}: {e}",file=sys.stderr)

    def _read_sql(self,p:Path,eid:str,at:str):
        # Executes local organizer-supplied SQLite snapshots in isolated memory only.
        db=sqlite3.connect(":memory:")
        try:
            db.executescript(p.read_text(encoding="utf-8"))
            db.row_factory=sqlite3.Row
            names=[x[0] for x in db.execute("SELECT name FROM sqlite_master WHERE type='table'")]
            for name in names:
                if name=="snapshot_scope":continue
                safe='"'+name.replace('"','""')+'"'
                try:entries=db.execute(f"SELECT * FROM {safe}").fetchall()
                except sqlite3.DatabaseError:continue
                table_cat=next((v for k,v in COL_CATEGORY.items() if k in name),"")
                seen=set()
                for record in entries:
                    obj=dict(record)
                    raw=obj.get("record_json")
                    if raw:
                        try:obj.update(json.loads(raw))
                        except (TypeError,ValueError):pass
                    rid=str(obj.get("resource_id") or "")
                    if not rid:continue
                    seen.add(rid)
                    cat=category_for(rid,name)
                    if cat=="USER_PROFILE" and any(t in norm(obj.get("account_status")) for t in ("deleted","tombstone")): cat="ACCOUNT_TOMBSTONE"
                    self.add(rid,str(obj.get("origin_system") or ""),cat,implied_state(cat,obj),at,eid,tokens_of(obj),3,name,p.name)
                # A point-in-time snapshot proves absence when a deletion target is
                # named by the operational ledger but is missing from the relevant
                # table. This is particularly important for deleted profiles whose
                # row naturally contains no email/user token anymore.
                if table_cat:
                    for activity in self.activity:
                        arid=norm(activity.get("resource_id"))
                        if not arid or arid in seen or norm(activity.get("event_type"))!="delete_record":continue
                        if category_for(arid)!=table_cat:continue
                        if not time_ok(activity.get("event_time",""),at):continue
                        self.add(arid,activity.get("target_system") or activity.get("source_system") or "",table_cat,"ABSENT",at,eid,set(),1,name,p.name)
        except sqlite3.DatabaseError as e:print(f"Warning: SQL {p}: {e}",file=sys.stderr)
        finally:db.close()

    def _read_text(self,p:Path,eid:str,at:str):
        try:raw=p.read_text(encoding="utf-8",errors="replace")
        except OSError:return
        traces:dict[str,set[str]]=collections.defaultdict(set)
        lines=raw.splitlines()
        for line in lines:
            when=re.search(r'20\d\d-\d\d-\d\dT\d\d:\d\d:\d\dZ',line)
            t=when.group() if when else at
            parts=re.search(r'\|\s*([a-z_]+)\s*\|\s*([a-z_]+\w*)\s*\|\s*([A-Z_]+)\s*\|\s*([A-Z_]+)\s*\|\s*(.+)$',line)
            if parts:
                system,rid,cat,state,subject=parts.groups()
                self.add(rid,system,cat,implied_state(cat,{"subject_reference":subject},state),t,eid,{norm(subject)},3,source=p.name)
                continue
            kv={k:v.strip('"\'') for k,v in KV_RE.findall(line)}
            trace=kv.get("trace_id","")
            toks={norm(v) for k,v in kv.items() if k in (ALL_IDENTITY_FIELDS|{"subject","query"}) and norm(v)}
            if trace:
                traces[trace].update(toks)
                toks=traces[trace]|toks
            rid=kv.get("resource_id","")
            event=kv.get("event","").lower()
            if not rid:continue
            cat=category_for(rid)
            state=""
            # Positive readbacks only: never turn a workflow DELETE success into proof.
            readback = any(w in event for w in (
                "lookup_completed","query_completed","read_completed","scan_completed",
                "config_read_completed","policy_read_completed","message_pii_scan",
                "marker_check","candidate_evaluated","contact_lookup_completed",
            ))
            if readback:
                state=implied_state(cat,kv,kv.get("result","") or kv.get("status",""))
                if kv.get("rows")=="0" or kv.get("http_status")=="404" or kv.get("total_hits")=="0":state="ABSENT"
                elif kv.get("rows")=="1" or kv.get("http_status")=="200" or kv.get("result")=="hit":state="PRESENT"
                elif event=="message_pii_scan" or "direct_identifier" in event:state="IDENTIFIABLE"
                elif event=="marker_check":
                    state="PRESENT" if asbool(kv.get("marker_found")) is False else "ABSENT"
                elif event=="candidate_evaluated":
                    state="ACTIVE" if asbool(kv.get("eligible")) else "BLOCKED"
                elif cat=="DATA_FLOW" and "enabled" in kv:
                    state="ACTIVE" if asbool(kv.get("enabled")) else "DISABLED"
                elif cat=="BACKUP_ARCHIVE" and ("eligible" in kv or "deletion_block" in kv):
                    state="ACTIVE" if asbool(kv.get("eligible")) and not asbool(kv.get("deletion_block")) else "BLOCKED"
            elif any(w in event for w in ("restored","recreated","rehydrated")):
                state="PRESENT"
            elif event in {"connector_heartbeat","connector_status_read"} and "enabled" in kv:
                state="ACTIVE" if asbool(kv.get("enabled")) else "DISABLED"
            # Readback logs require actual resource state, not generic event messages.
            if state:
                self.add(rid,kv.get("service",""),cat,state,t,eid,toks,2,source=p.name)

    def _read_pdf_image(self,p:Path,eid:str,at:str):
        # Prefer embedded PDF text. Images use optional local OCR (no cloud upload).
        text=""
        if p.suffix.lower()==".pdf":
            try:
                x=subprocess.run(["pdftotext","-layout",str(p),"-"],capture_output=True,text=True,timeout=15)
                if x.returncode==0:text=x.stdout
            except (OSError,subprocess.TimeoutExpired):pass
        else:
            try:
                x=subprocess.run(["tesseract",str(p),"stdout"],capture_output=True,text=True,timeout=15)
                if x.returncode==0:text=x.stdout
            except (OSError,subprocess.TimeoutExpired):pass
        if text:
            tmp_lines=text.splitlines()
            for line in tmp_lines:
                rid_match=RESOURCE_RE.search(line)
                if not rid_match:continue
                rid=rid_match.group(0)
                cat=category_for(rid)
                tokens={norm(a) for a in re.findall(r'[\w.+-]+@[\w.-]+\.[a-zA-Z]{2,}',line)}
                tokens |= {norm(a) for a in re.findall(r'\buser_\d+\b',line)}
                low=line.lower()
                state=next((v for key,v in [("not_found","ABSENT"),("not found","ABSENT"),("anonymized","ANONYMIZED"),("redacted","REDACTED"),("disabled","DISABLED"),("blocked","BLOCKED"),("identifiable","IDENTIFIABLE"),("active","ACTIVE"),("found","PRESENT") ] if key in low),"PRESENT")
                self.add(rid,"",cat,state,at,eid,tokens,1,source=p.name)

    def _vision_extract(self,p:Path,eid:str,at:str):
        """Opt-in VLM fallback for screenshots; evidence is never modified."""
        if not os.getenv("OPENAI_API_KEY"):
            print("--vision requested but OPENAI_API_KEY is absent",file=sys.stderr)
            return
        try:
            from openai import OpenAI
            content=base64.b64encode(p.read_bytes()).decode("ascii")
            mime="image/png" if p.suffix.lower()==".png" else "image/jpeg"
            model=os.getenv("OPENAI_VISION_MODEL",os.getenv("OPENAI_MODEL","gpt-4.1-mini"))
            resp=OpenAI().responses.create(model=model,input=[{"role":"user","content":[
                {"type":"input_text","text":"Transcribe only resource rows visibly present in this administrative screenshot. Respond with a JSON object {\"records\":[{\"resource_id\":\"...\",\"system_id\":\"...\",\"category\":\"...\",\"state\":\"PRESENT/ABSENT/IDENTIFIABLE/REDACTED/ANONYMIZED/ACTIVE/DISABLED/BLOCKED\",\"subject_reference\":\"visible exact user ID or email, otherwise empty\"}]}. Do not infer hidden values or invent resources."},
                {"type":"input_image","image_url":f"data:{mime};base64,{content}"}] }],max_output_tokens=1200)
            self._meter(resp,model)
            payload=resp.output_text.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
            parsed=json.loads(payload)
            for row in parsed.get("records",[]):
                rid=row.get("resource_id","")
                if not RESOURCE_RE.fullmatch(str(rid)):continue
                cat=category_for(rid,"",row.get("category",""))
                state=str(row.get("state") or "UNKNOWN").upper()
                if state not in {"PRESENT","ABSENT","IDENTIFIABLE","REDACTED","ANONYMIZED","ACTIVE","DISABLED","BLOCKED"}:continue
                toks=tokens_of(row) | ({norm(row.get("subject_reference"))} if row.get("subject_reference") else set())
                self.add(rid,row.get("system_id",""),cat,state,at,eid,toks,1,source=p.name)
        except Exception as e:
            print(f"VLM image reading failed for {p.name}: {e}",file=sys.stderr)

    def _meter(self,resp,model:str):
        usage=getattr(resp,"usage",None)
        self.model_usage.append({"provider":"OpenAI","model":model,
             "input_tokens":int(getattr(usage,"input_tokens",0) or 0),
             "output_tokens":int(getattr(usage,"output_tokens",0) or 0)})

    def write_usage_report(self,path:Path):
        by_model=collections.defaultdict(lambda:[0,0,0])
        for u in self.model_usage:
            k=(u["provider"],u["model"]);v=by_model[k]
            v[0]+=1;v[1]+=u["input_tokens"];v[2]+=u["output_tokens"]
        total_calls=sum(v[0] for v in by_model.values())
        inp=sum(v[1] for v in by_model.values());out=sum(v[2] for v in by_model.values())
        n=len(self.requests) or 1
        # Configurable dollar per million token rates avoid stale hardcoded model pricing.
        ir=float(os.getenv("MODEL_INPUT_PRICE_PER_MILLION","0"))
        orate=float(os.getenv("MODEL_OUTPUT_PRICE_PER_MILLION","0"))
        cost=(inp*ir+out*orate)/1e6
        t=["# Token Usage Report", "",f"Dataset requests: {len(self.requests)}", "",
           "| Provider | Model | Calls | Input tokens | Output tokens | Estimated cost (USD) |",
           "| --- | --- | ---: | ---: | ---: | ---: |"]
        for (provider,model),(calls,i,o) in sorted(by_model.items()):
            t.append(f"| {provider} | {model} | {calls} | {i} | {o} | ${(i*ir+o*orate)/1e6:.6f} |")
        if not by_model:t.append("| None (local deterministic evidence engine) | None | 0 | 0 | 0 | $0.000000 |")
        t += ["",f"**Total calls:** {total_calls}; **input tokens:** {inp}; **output tokens:** {out}; **combined tokens:** {inp+out}.",
              f"**Average tokens/request:** {(inp+out)/n:.2f}; **estimated total cost:** ${cost:.6f}; **estimated cost/request:** ${cost/n:.6f}.",
              "", "Token estimates use `MODEL_INPUT_PRICE_PER_MILLION` and `MODEL_OUTPUT_PRICE_PER_MILLION` (USD), default 0 if not supplied; configure actual provider pricing before reporting paid run costs.",
              "Local Python computation and OCR consume no API tokens. Development-time ChatGPT tokens are not counted as runtime calls."]
        path.parent.mkdir(parents=True,exist_ok=True)
        path.write_text("\n".join(t)+"\n",encoding="utf-8")

    def _read_evidence(self):
        for meta in self.manifest:
            p=self.dataset/meta["file_path"]
            if not p.is_file():continue
            at=meta.get("captured_at","")
            eid=meta["file_id"]
            if p.suffix.lower()==".json":self._read_json(p,eid,at)
            elif p.suffix.lower()==".sql":self._read_sql(p,eid,at)
            elif p.suffix.lower() in {".log",".txt"}:self._read_text(p,eid,at)
            elif p.suffix.lower() in {".pdf",".png",".jpg",".jpeg"}:
                self._read_pdf_image(p,eid,at)
                if self.vision and p.suffix.lower() in {".png",".jpg",".jpeg"}:self._vision_extract(p,eid,at)

    def _index_resources(self):
        for o in self.observations:
            for tok in o.tokens:
                for uid in self.token_users.get(tok,()):self.user_resources[uid].add(o.resource)
        # Activity may provide resource IDs for resources with only a state claim.
        # Do not mark these as audited without readback evidence.

    def _user_for(self,request:dict) -> str:
        key=norm(request.get("email"))
        us=self.token_users.get(key,set())
        if len(us)==1:return next(iter(us))
        if us:
            direct=[u for u in us if any(norm(p.get("email"))==key and norm(p.get("user_id"))==u for p in self.people)]
            if len(direct)==1:return direct[0]
            return sorted(us)[0]
        return ""

    def _intent(self,request:dict, llm:bool=False) -> bool:
        tx=norm(request.get("request_text"))
        if not tx:return False
        disallow=[r'\bdo not delete\b',r"\bdon['’]?t delete\b",r'\bnot (?:ask(?:ing)?|request(?:ing)?) (?:for |to )?(?:delet|eras)',r'\bwithout deleting\b',r'\bkeep my account\b',r'\bonly (?:unsubscribe|update|correct|download|export|change)\b',r'\bplease (?:do not|don.t) erase\b',r'\bnot a deletion request\b',r'\bwithdraw my deletion request\b',r'\bcancel (?:my|the) deletion\b']
        if any(re.search(s,tx) for s in disallow):return False
        yes=["delet", "eras", "remov", "close my account", "close this account", "close the account", "closed my account", "account is gone", "account completely", "deleted-account", "deleted account", "profile is gone", "profile is deleted", "still existed", "check the latest state", "nothing tied to", "retained personal", "personal-data", "data be gone", "cannot identify me", "no longer send my data", "de-identif", "anonym", "right to be forgotten", "privacy page", "permanently", "my request failed", "audit the deletion", "account was deleted", "account to be gone", "delete this account", "suppression", "supprimer", "effacer", "eliminaci", "eliminación", "exclusão", "apagar", "삭제", "削除", "消去"]
        if any(s in tx for s in yes):return True
        # Optional model adjudication for short or multilingual edge cases.
        if llm:
            try:
                from openai import OpenAI
                cleaned=re.sub(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}","[EMAIL]",request.get("request_text",""))
                model=os.getenv("OPENAI_MODEL","gpt-4.1-mini")
                ans=OpenAI().responses.create(model=model,input=[{"role":"system","content":"Classify only whether the person requests or audits personal data/account deletion. Return exactly YES or NO."},{"role":"user","content":cleaned}],max_output_tokens=5)
                self._meter(ans,model)
                return ans.output_text.strip().upper().startswith("YES")
            except Exception as e:print(f"LLM fallback unavailable: {e}",file=sys.stderr)
        # Conservative: do not authorize a deletion without clearly stated intent.
        return False

    def _selected(self,request:dict,uid:str) -> dict[str,Observation]:
        aud=request["audit_at"]
        identity=self.identities.get(uid,{norm(request.get("email"))})
        matched=set(self.user_resources.get(uid,()))
        # Additional direct association for emails absent in user_identities: exact match.
        for o in self.observations:
            if time_ok(o.at,aud) and identity & o.tokens:matched.add(o.resource)
        # Deletion workflows often leave the final account row empty, so the
        # operational ledger is also used as a narrow temporal join. We only
        # accept targets within five minutes of a request/report/audit milestone;
        # this avoids treating unrelated activity as evidence for the user.
        milestones=[]
        for key in ("requested_at","reported_at","audit_at"):
            value=request.get(key,"")
            if value:
                try:milestones.append(datetime.fromisoformat(value.replace("Z","+00:00")))
                except ValueError:pass
        temporal_accounts=[]
        for activity in self.activity:
            rid=norm(activity.get("resource_id")); when=activity.get("event_time","")
            if not rid or not time_ok(when,aud) or not rid.startswith("account_"):continue
            if norm(activity.get("event_type"))!="delete_record":continue
            try:at=datetime.fromisoformat(when.replace("Z","+00:00"))
            except ValueError:continue
            if milestones:
                temporal_accounts.append((min(abs((at-m).total_seconds()) for m in milestones),rid))
        if temporal_accounts:
            distance,rid=min(temporal_accounts)
            if distance<=600:matched.add(rid)
        selected={}
        for rid in matched:
            available=[o for o in self.by_resource[rid] if time_ok(o.at,aud)]
            if not available:continue
            # Prefer newest direct readback; ties favor quality/primary observations.
            available.sort(key=lambda o:(o.at,o.quality,0 if "replica" in o.topology else 1, o.state not in {"ABSENT","REDACTED","ANONYMIZED","DISABLED","BLOCKED"}))
            best=available[-1]
            # An otherwise-deleted primary can still coexist with a live replica.
            # Preserve a same-day risky replica observation rather than erasing replication drift.
            good={"ABSENT","REDACTED","ANONYMIZED","DISABLED","BLOCKED"}
            if best.state in good:
                try:
                    best_t=datetime.fromisoformat(best.at.replace("Z","+00:00"))
                    lagging=[o for o in available if o.state not in good and
                             ("replica" in o.topology.lower() or "replica" in o.source.lower()) and
                             datetime.fromisoformat(o.at.replace("Z","+00:00")) <= best_t]
                    if lagging:best=max(lagging,key=lambda o:(o.at,o.quality))
                except ValueError:pass
            selected[rid]=best
        return selected

    def _target_action(self,obs:Observation,audit:str) -> str:
        category=obs.category
        if category=="SECURITY_AUDIT_LOG":return "RETAIN"
        if category=="LEGAL_HOLD_RECORD":return "RETAIN"
        if category=="BACKUP_ARCHIVE":return "BLOCK"
        if category=="DATA_FLOW":return "DISABLE"
        if category=="ACCOUNT_TOMBSTONE":return "REDACT"
        return self.rules.get(category,"DELETE")

    def audit_one(self,request:dict,llm=False) -> dict:
        cid=request["case_id"]
        if not self._intent(request,llm):return {"case_id":cid,"deletion_status":"NOT_APPLICABLE","steps_json":"[]"}
        uid=self._user_for(request)
        selected=self._selected(request,uid)
        findings=[]; remediation=[]; verification=[]
        for rid,o in selected.items():
            target=self._target_action(o,request["audit_at"])
            actual=o.state
            # Keep all required checks even if record was already treated correctly.
            if target=="DELETE":
                vop="VERIFY_RECORD_ABSENT"
                if actual!="ABSENT":
                    findings.append(("REPORT_REMAINING_RECORD",o))
                    remediation.append(("DELETE_RECORD",o))
            elif target=="REDACT":
                vop="VERIFY_RECORD_REDACTED"
                if actual!="REDACTED":
                    findings.append(("REPORT_EXPOSED_PII",o))
                    remediation.append(("REDACT_RECORD",o))
            elif target=="ANONYMIZE":
                vop="VERIFY_RECORD_ANONYMIZED"
                if actual!="ANONYMIZED":
                    findings.append(("REPORT_EXPOSED_PII",o))
                    remediation.append(("ANONYMIZE_RECORD",o))
            elif target=="RETAIN":
                vop="VERIFY_RECORD_PRESENT"
                # Absence of a required retained record is not fixed by unsafe fabrication.
            elif target=="BLOCK":
                vop="VERIFY_RESTORE_BLOCKED"
                if actual!="BLOCKED":
                    findings.append(("REPORT_RESTORE_RISK",o))
                    remediation.append(("BLOCK_RESTORE",o))
            elif target=="DISABLE":
                vop="VERIFY_DATA_FLOW_DISABLED"
                if actual!="DISABLED":
                    findings.append(("REPORT_ACTIVE_DATA_FLOW",o))
                    remediation.append(("DISABLE_DATA_FLOW",o))
            else:continue
            verification.append((vop,o))
        status="INCOMPLETE" if findings else "COMPLETE"
        items=[]
        for phase,pairs in [("FINDING",findings),("REMEDIATION",remediation),("VERIFICATION",verification)]:
            pairs.sort(key=lambda x:(OP_RANK[x[0]],x[1].system,x[1].resource))
            for op,o in pairs:
                state=("ACTIVE" if op in {"REPORT_ACTIVE_DATA_FLOW","REPORT_RESTORE_RISK"} else "PRESENT" if op.startswith("REPORT_") else {"DISABLE_DATA_FLOW":"DISABLED","BLOCK_RESTORE":"BLOCKED","DELETE_RECORD":"ABSENT","REDACT_RECORD":"REDACTED","ANONYMIZE_RECORD":"ANONYMIZED","VERIFY_RECORD_ABSENT":"ABSENT","VERIFY_RECORD_PRESENT":"PRESENT","VERIFY_RECORD_REDACTED":"REDACTED","VERIFY_RECORD_ANONYMIZED":"ANONYMIZED","VERIFY_DATA_FLOW_DISABLED":"DISABLED","VERIFY_RESTORE_BLOCKED":"BLOCKED"}[op])
                eid=o.evidence if phase=="FINDING" or (status=="COMPLETE" and phase=="VERIFICATION") else ""
                items.append({"step_no":len(items)+1,"phase":phase,"system_id":o.system,"resource_id":o.resource,"operation":op,"state":state,"evidence_id":eid})
        return {"case_id":cid,"deletion_status":status,"steps_json":json.dumps(items,ensure_ascii=False,separators=(",",":"))}

    def run(self,out:Path,llm:bool=False):
        data=[self.audit_one(req,llm) for req in sorted(self.requests,key=case_sort_key)]
        out.parent.mkdir(parents=True,exist_ok=True)
        with out.open("w",encoding="utf-8",newline="") as f:
            wr=csv.DictWriter(f,fieldnames=["case_id","deletion_status","steps_json"])
            wr.writeheader();wr.writerows(data)
        counts=collections.Counter(x["deletion_status"] for x in data)
        print(json.dumps({"requests":len(data),"observations":len(self.observations),"resources":len(self.by_resource),"statuses":counts,"output":str(out)},indent=2))


def case_sort_key(row):
    value=str(row["case_id"])
    match=re.search(r"(\d+)$",value)
    return (value[:match.start()],int(match.group(1))) if match else (value,0)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--dataset",type=Path,default=Path("dataset"))
    ap.add_argument("--output",type=Path,default=Path("output.csv"))
    ap.add_argument("--requests",type=Path,default=None,help="Override case list; e.g. sample_deletion_requests.csv")
    ap.add_argument("--llm-intent",action="store_true",help="Optional OpenAI fallback for ambiguous intent; request text emails are masked")
    ap.add_argument("--vision",action="store_true",help="Opt-in cloud VLM extraction for screenshots; sends images to API")
    ap.add_argument("--usage-report",type=Path,default=None,help="Save model runtime token/cost report")
    args=ap.parse_args()
    c=EvidenceCorpus(args.dataset,vision=args.vision)
    if args.requests:c.requests=rows(args.requests)
    c.run(args.output,args.llm_intent)
    if args.usage_report:c.write_usage_report(args.usage_report)

if __name__=="__main__":main()
