# Approval contract review v0.1

Date: 2026-09-30. Scope: Conciencia core commit
`383ac445a17fe839325aa546138aee183a8fb06b` and the SIMULATED Lab adapter.
No core behavior changed and no action is authorized by this review.

## Current behavior

`approval: true` writes `waiting_approval` and a random `approval_token` into
`WorkflowRun.step_results`, pauses the run, and writes generic events to
`WorkflowRun.events`. `approve_step()` requires a paused run and waiting step,
then marks it approved or rejected. Approval resumes after the gate step;
rejection cancels. A second sequential approval fails because the run is no
longer paused.

This is workflow continuation, not authorization for a particular action. The
approved step is skipped on resume; later steps execute from the current
workflow definition. A normal workflow without `approval: true` completes.
The gate does not call append-only `AuditEvent`.

Routers require `get_current_user`, but the approval handler receives no user,
stores no approver and checks no role. `User.role` and `Policy` exist but are
not used by `approve_step()`. Signals/Evidence can document a result but have
no foreign key to decision, target, plan or verification.

## Characterization matrix

| Guarantee sought | Current behavior | Evidence | Gap |
| --- | --- | --- | --- |
| Missing approval | Gated run pauses | characterization artifact | Gate is opt-in |
| Rejection | Pending run cancels | characterization artifact | No reason or actor |
| Changed plan | JSON may change while paused; approval still succeeds | artifact | No snapshot, digest or version binding |
| Preconditions | Plan JSON is not evaluated | source and artifact | No provider recheck |
| Expiry/revocation | 30-day old run approves; no revoke endpoint | artifact | No lifecycle control |
| Identity/permission | Authentication dependency only | route signature/model | No role enforcement |
| Reuse | Second sequential approval fails | artifact | No atomic consume token |
| Concurrency | No row lock/version found | source/model | Race not proven or controlled |
| Retry | `retries` gives one failed result | artifact | No retry loop/attempt identity |
| Audit/evidence | Mutable run events only | artifact/model | No decision/attempt/verifier links |

The test uses SQLite in memory and fixture identity. It proves this code path,
not deployed authentication, PostgreSQL transactions or real infrastructure.

## Minimum proposed contract

Create a core-owned `ActionAuthorization`; the Lab remains an adapter and never
issues approvals. Bind the record to this canonical snapshot:

```json
{"schema_version":"action-authorization/1","action":"pause_admission","provider":{"kind":"simulated_gpu","id":"simulated/0.1"},"environment":{"kind":"SIMULATED","id":"lab-local"},"target":{"kind":"node","id":"sim-node-001"},"parameters":{"paused":true},"plan_version":3,"preconditions":{"provider_revision":18,"diagnosis":"THERMAL_ANOMALY"}}
```

Canonicalize with RFC 8785 JSON Canonicalization Scheme UTF-8 and SHA-256.
Persist exact canonical snapshot and digest; reject unknown schema versions,
duplicate keys, missing units and non-finite numbers. A digest detects changed
trusted bytes only; it does not identify an approver, grant permission, prove
provider state or protect a record altered together with its digest.

The record stores links to Mission/WorkflowRun/step, requester, action/provider/
environment/target, snapshot/digest/version, lifecycle, approver/rejector/
revoker identities and timestamps, expiry, consumed-at, idempotency key and row
version. States: `pending → approved → consuming → consumed → executing →
verified`, with rejected, revoked, expired, execution_failed and
verification_failed exits.

Only an authenticated user with enforced `approve_infrastructure_action` may
approve. Requester and approver differ by default; break-glass requires reason
and audit. Approval atomically verifies pending/digest/expiry, writes actor,
time and expiry, and appends `approval_granted` in the same transaction.
Revocation works only before consumption.

Immediately before execution, the Lab submits authorization id, digest, plan
version, target, observed provider revision/preconditions and idempotency key.
The core atomically checks approved, unexpired, unrevoked and unconsumed state,
then reserves consumption. The Lab rechecks provider state; the provider needs
revision/CAS support or fails closed. One idempotency key returns the same
result; a different key after consumption is rejected. Signals/Evidence record
request, decision, attempt, result and independent verification by correlation
ID.

## Minimum core change plan

1. Add `ActionAuthorization`, an additive migration, expiry/run indexes, row
   version and unique authorization-id/idempotency-key attempt storage.
2. Add typed plan schema and canonicalization helper in core.
3. Add approve/revoke/consume/read APIs; pass current user to service methods,
   enforce permissions and append audit events transactionally.
4. Keep `approval:true` as compatible legacy review gate. Typed infrastructure
   steps reference authorization ID; no legacy decision is backfilled.
5. Update only the Lab SIMULATED adapter to consume an authorization before
   mutation and emit Signals/Evidence. Do not create Lab approvals.
6. Test PostgreSQL concurrency, roles, expiry, revocation, binding mismatch,
   duplicate consume, execution failure/retry and audit/evidence links.

## Later implementation brief

Implement model and read-only inspection first, then approval, revocation and
atomic consume behind a feature flag. Prove generic workflow compatibility
before using it for new SIMULATED actions. Do not enable a real provider until
binding, role, expiry, revocation, concurrency and verification tests pass.
`FIXTURE_ONLY` approvals remain test inputs, never ActionAuthorizations.
