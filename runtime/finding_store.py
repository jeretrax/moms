"""Local, single-operator MOMS pilot persistence. No network execution authority."""
import argparse
import json
import sqlite3
from datetime import datetime, timezone
from uuid import uuid4

SCHEMA = '''
PRAGMA foreign_keys=ON;
CREATE TABLE IF NOT EXISTS schema_version(version INTEGER PRIMARY KEY);
INSERT OR IGNORE INTO schema_version VALUES(1);
CREATE TABLE IF NOT EXISTS records(
 customer_id TEXT NOT NULL,
 kind TEXT NOT NULL CHECK(kind IN ('business','property','assessment','observation','finding','work_item')),
 id TEXT NOT NULL,
 created_at TEXT NOT NULL,
 payload TEXT NOT NULL CHECK(json_valid(payload)),
 PRIMARY KEY(customer_id,kind,id));
CREATE TABLE IF NOT EXISTS links(
 customer_id TEXT NOT NULL,
 source_kind TEXT NOT NULL, source_id TEXT NOT NULL,
 target_kind TEXT NOT NULL, target_id TEXT NOT NULL,
 PRIMARY KEY(customer_id,source_kind,source_id,target_kind,target_id),
 FOREIGN KEY(customer_id,source_kind,source_id) REFERENCES records(customer_id,kind,id),
 FOREIGN KEY(customer_id,target_kind,target_id) REFERENCES records(customer_id,kind,id));
CREATE TABLE IF NOT EXISTS events(
 sequence INTEGER PRIMARY KEY AUTOINCREMENT,
 customer_id TEXT NOT NULL, kind TEXT NOT NULL, id TEXT NOT NULL,
 occurred_at TEXT NOT NULL, actor TEXT NOT NULL,
 payload TEXT NOT NULL CHECK(json_valid(payload)),
 FOREIGN KEY(customer_id,kind,id) REFERENCES records(customer_id,kind,id));
CREATE TRIGGER IF NOT EXISTS immutable_record_update BEFORE UPDATE ON records BEGIN SELECT RAISE(ABORT,'append a revision instead'); END;
CREATE TRIGGER IF NOT EXISTS immutable_record_delete BEFORE DELETE ON records BEGIN SELECT RAISE(ABORT,'immutable pilot record'); END;
CREATE TRIGGER IF NOT EXISTS immutable_event_update BEFORE UPDATE ON events BEGIN SELECT RAISE(ABORT,'immutable event'); END;
CREATE TRIGGER IF NOT EXISTS immutable_event_delete BEFORE DELETE ON events BEGIN SELECT RAISE(ABORT,'immutable event'); END;
CREATE TRIGGER IF NOT EXISTS immutable_link_update BEFORE UPDATE ON links BEGIN SELECT RAISE(ABORT,'immutable link'); END;
CREATE TRIGGER IF NOT EXISTS immutable_link_delete BEFORE DELETE ON links BEGIN SELECT RAISE(ABORT,'immutable link'); END;
'''

class Store:
    def __init__(self, path):
        self.db = sqlite3.connect(path)
        self.db.executescript(SCHEMA)

    def add(self, customer, kind, payload, actor, id=None):
        if not customer or not actor:
            raise ValueError('customer and actor required')
        if kind == 'observation':
            for key in ('url','observed_at','retrieval_method','excerpt'):
                if not payload.get(key):
                    raise ValueError('observation requires '+key)
        id = id or str(uuid4())
        stamp = datetime.now(timezone.utc).isoformat()
        encoded = json.dumps(payload, sort_keys=True)
        self.db.execute('INSERT INTO records VALUES(?,?,?,?,?)', (customer,kind,id,stamp,encoded))
        self.db.execute('INSERT INTO events(customer_id,kind,id,occurred_at,actor,payload) VALUES(?,?,?,?,?,?)',
                        (customer,kind,id,stamp,actor,json.dumps({'event':'created'})))
        return id

    def link(self, customer, source_kind, source_id, target_kind, target_id):
        self.db.execute('INSERT INTO links VALUES(?,?,?,?,?)', (customer,source_kind,source_id,target_kind,target_id))

    def list(self, customer):
        return [{'kind':r[0],'id':r[1],'created_at':r[2],'payload':json.loads(r[3])}
                for r in self.db.execute('SELECT kind,id,created_at,payload FROM records WHERE customer_id=? ORDER BY created_at,id',(customer,))]

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--db', required=True)
    p.add_argument('--customer', required=True)
    p.add_argument('command',choices=['init','list','import'])
    p.add_argument('--input',help='JSON bundle of records and links; IDs are customer scoped')
    a=p.parse_args()
    s=Store(a.db)
    if a.command=='import':
        if not a.input: p.error('--input required')
        with open(a.input) as f: bundle=json.load(f)
        with s.db:
            for r in bundle['records']:
                s.add(a.customer,r['kind'],r['payload'],bundle['actor'],r['id'])
            for link in bundle.get('links',[]): s.link(a.customer,**link)
    print(json.dumps(s.list(a.customer),indent=2))
    s.db.close()

if __name__=='__main__': main()
