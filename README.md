# MOMS runtime

Local single-operator finding-store pilot, aligned to moms-design Domain Model and Marketing Work Item. SQLite is an isolated development implementation, not a production hosting or tenancy decision.

## Run
Python 3 with SQLite JSON support; no third-party dependencies.

```bash
python runtime/finding_store.py --db pilot.sqlite3 --customer example init
python runtime/finding_store.py --db pilot.sqlite3 --customer example import --input bundle.json
python runtime/finding_store.py --db pilot.sqlite3 --customer example list
```

Import bundle: actor, records [{kind,id,payload}], links [{source_kind,source_id,target_kind,target_id}]. Kind maps to existing Business Profile, Web Property, Assessment, Observation, InsightFinding and Marketing Work Item concepts. Payloads are provisional JSON storage, not a competing canonical schema. Records and events are immutable; corrections use new records and explicit links. Import is atomic; duplicate IDs fail without replacing history.

Verified: reopen persistence, scoped reads, rejected cross-customer links and rejected record updates. This pilot does not implement authentication, row-level authorization, encryption/key management, automated collection, approved execution, production migrations or retention/redaction. Customer scoping is relational integrity, not protection against a user with direct database access. Do not deploy as a shared production service. Future schema versions require migrations; current schema_version is 1.

No customer records or database files belong in this public repository. Private pilot database is saved separately.
