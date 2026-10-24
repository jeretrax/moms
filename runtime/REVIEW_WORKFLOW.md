# Confirmation and change-review workflow

User-authorized workflow, 2026-10-23. Local single-operator prototype; no authenticated web portal or external publishing implemented.

Uses Store from finding_store.py. Instantiate Workflow(store) and call apply(customer, request, expected_version, actor, role, event, data). Each transition is an immutable event in the same SQLite database. Composite customer/request keys and tenant-scoped finding validation preserve relational scope. BEGIN IMMEDIATE plus expected_version prevents stale concurrent transitions. Browser input must never supply trusted roles in production; a future authenticated service must derive customer membership and role server-side.

## Flow
created → sent (confirmed delivery reference) → responses_recorded → confirmation_reviewed → proposal_prepared → internally_reviewed → customer_approved → implementation_recorded → verification_recorded → completion_reported → monitoring_recorded.

All-correct/not-applicable reviews can close_no_change before completion reporting. Uncertain responses can be clarified and resubmitted before proposal preparation. Proposals may be revised before implementation; every revision requires internal review and customer approval again. Customer rejection blocks implementation until a newly reviewed proposal is approved.

Confirmation outcomes: confirmed_correct, confirmed_issue, opportunity, not_applicable, unable_to_verify. Every outcome requires evidence. Responses and approvals are separate. Exact proposed changes record finding ID, target, before, after and reason. Approval binds the canonical changes hash. Implementation requires backup, baseline (or a reference explaining unavailable baseline) and execution evidence. Successful verification is mandatory before reporting completion; failed verification leaves implementation uncompleted and requires investigation/retest. These events record real external actions; they do not perform them.

## Verification
python -m unittest discover -s runtime -p 'test_review_workflow.py' -v

Tests cover premature implementation, wrong/stale approval, proposal revision invalidation, customer scope, backup requirements, failed verification, persistence and optimistic version checks. Fixture-only tests send no messages and change no websites.

## Remaining implementation
Authenticated tenant-scoped APIs, customer form and granular question-to-finding bindings, delivery integration, reminders, authenticated customer signatures, implementation adapters, retry/recovery UI, and production hosting/retention. Existing local pilot request is created, not sent. No automatic external execution is enabled.
