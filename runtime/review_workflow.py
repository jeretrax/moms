"""Local workflow prototype. Trusted operator API; no authentication or publishing."""
import hashlib
import json
from datetime import datetime, timezone

DDL = '''
CREATE TABLE IF NOT EXISTS review_events(
 sequence INTEGER PRIMARY KEY AUTOINCREMENT,
 customer_id TEXT NOT NULL, request_id TEXT NOT NULL,
 version INTEGER NOT NULL, occurred_at TEXT NOT NULL,
 actor TEXT NOT NULL, role TEXT NOT NULL,
 event TEXT NOT NULL, data TEXT NOT NULL CHECK(json_valid(data)),
 UNIQUE(customer_id,request_id,version));
CREATE TRIGGER IF NOT EXISTS review_no_update BEFORE UPDATE ON review_events BEGIN SELECT RAISE(ABORT,'immutable review history'); END;
CREATE TRIGGER IF NOT EXISTS review_no_delete BEFORE DELETE ON review_events BEGIN SELECT RAISE(ABORT,'immutable review history'); END;
'''
OUTCOMES = {'confirmed_correct','confirmed_issue','opportunity','not_applicable','unable_to_verify'}

def digest(proposal):
    return hashlib.sha256(json.dumps(proposal,sort_keys=True,separators=(',',':')).encode()).hexdigest()

class Workflow:
    def __init__(self, store):
        self.store=store
        self.db=store.db
        self.db.executescript(DDL)

    def history(self, customer, request):
        return [{'version':r[0],'actor':r[1],'role':r[2],'event':r[3],'data':json.loads(r[4])}
          for r in self.db.execute('SELECT version,actor,role,event,data FROM review_events WHERE customer_id=? AND request_id=? ORDER BY version',(customer,request))]

    def apply(self, customer, request, expected_version, actor, role, event, data):
        """Roles must eventually come from authenticated membership, never browser input."""
        if not actor or not customer: raise ValueError('actor and customer required')
        with self.db:
            self.db.execute('BEGIN IMMEDIATE')
            h=self.history(customer,request)
            if len(h)!=expected_version: raise ValueError('stale revision')
            state=h[-1]['event'] if h else None
            if event=='created':
                if h or role!='operator': raise ValueError('creation forbidden')
                if not data.get('items'): raise ValueError('items required')
                if len(data['items'])!=len(set(data['items'])): raise ValueError('duplicate items')
                for item in data['items']:
                    if not self.db.execute("SELECT 1 FROM records WHERE customer_id=? AND kind='finding' AND id=?",(customer,item)).fetchone():
                        raise ValueError('unknown customer finding')
            elif not h: raise ValueError('unknown request')
            elif event=='sent':
                if role!='operator' or state!='created' or not data.get('delivery_reference'): raise ValueError('record confirmed delivery first')
            elif event=='responses_recorded':
                if role not in ('customer','operator') or state not in ('sent','responses_recorded','confirmation_reviewed'): raise ValueError('responses forbidden')
                answers=data.get('answers',{})
                if set(answers)!=set(h[0]['data']['items']): raise ValueError('answer every item, including unsure')
                if any(a.get('choice') not in ('correct_as_shown','needs_changes','no_longer_applicable','unsure') for a in answers.values()): raise ValueError('invalid answer')
            elif event=='confirmation_reviewed':
                if role!='operator' or state!='responses_recorded': raise ValueError('review responses first')
                outcomes=data.get('outcomes',{})
                if set(outcomes)!=set(h[0]['data']['items']): raise ValueError('outcome per item required')
                if any(v.get('outcome') not in OUTCOMES or not v.get('evidence') for v in outcomes.values()): raise ValueError('outcome and evidence required')
            elif event=='closed_no_change':
                if role!='operator' or state!='confirmation_reviewed': raise ValueError('review required')
                if any(v['outcome'] not in ('confirmed_correct','not_applicable') for v in h[-1]['data']['outcomes'].values()): raise ValueError('unresolved items remain')
            elif event=='proposal_prepared':
                if role!='operator' or state not in ('confirmation_reviewed','proposal_prepared','internally_reviewed','customer_approved','customer_rejected'): raise ValueError('proposal forbidden')
                changes=data.get('changes',[])
                if not changes: raise ValueError('exact changes required')
                for ch in changes:
                    if ch.get('finding_id') not in h[0]['data']['items'] or any(not ch.get(k) for k in ('target','before','after','reason')): raise ValueError('invalid change')
                data=dict(data,proposal_hash=digest({'changes':changes}))
            elif event in ('internally_reviewed','customer_approved','customer_rejected'):
                required={'internally_reviewed':('operator','proposal_prepared'),'customer_approved':('customer','internally_reviewed'),'customer_rejected':('customer','internally_reviewed')}
                if (role,state)!=required[event]: raise ValueError('invalid approval transition')
                proposal=next(e for e in reversed(h) if e['event']=='proposal_prepared')
                if data.get('proposal_hash')!=proposal['data']['proposal_hash']: raise ValueError('wrong proposal revision')
            elif event=='implementation_recorded':
                if role!='operator' or state!='customer_approved': raise ValueError('customer approval required')
                if data.get('proposal_hash')!=h[-1]['data']['proposal_hash']: raise ValueError('wrong approved revision')
                if not all(data.get(k) for k in ('backup_reference','baseline_reference','execution_reference')): raise ValueError('backup, baseline or explicit unavailability record, and execution evidence required')
            elif event=='verification_recorded':
                if role!='operator' or state!='implementation_recorded': raise ValueError('implementation required')
                if data.get('passed') is not True or not data.get('evidence'): raise ValueError('successful verification evidence required to complete')
            elif event=='completion_reported':
                if role!='operator' or state not in ('verification_recorded','closed_no_change') or not data.get('report_reference'): raise ValueError('verified completion/report required')
            elif event=='monitoring_recorded':
                if role!='operator' or state not in ('completion_reported','monitoring_recorded') or not data.get('evidence'): raise ValueError('monitoring evidence required')
            else: raise ValueError('unknown event')
            self.db.execute('INSERT INTO review_events(customer_id,request_id,version,occurred_at,actor,role,event,data) VALUES(?,?,?,?,?,?,?,?)',(customer,request,expected_version+1,datetime.now(timezone.utc).isoformat(),actor,role,event,json.dumps(data,sort_keys=True)))
        return self.history(customer,request)[-1]
