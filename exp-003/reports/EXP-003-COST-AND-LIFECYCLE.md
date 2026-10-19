# EXP-003 — Cost and lifecycle

**Session 001 · Nebius AI Cloud · `eu-north1` · 1× NVIDIA H200**

---

## Observed cost

| Item | Value |
| --- | --- |
| Observed session spend (operator report) | **~USD 1.70** |
| Reported session duration | **~55 minutes** |
| Arithmetic average | **~USD 1.85/h** |
| Spot maximum price policy | **USD 2.70 per GPU-hour** (price ceiling, not a budget cap) |
| Reconciliation status | **Pending** — no invoice-level breakdown was analyzed |

### How to read these numbers

- USD 1.70 / (55/60 h) = **USD 1.8545/h**. This is an arithmetic average over a
  very short session, not a contractual rate.
- The **USD 2.70/GPU-hour** policy is the maximum Spot price the operator was
  willing to pay per GPU-hour. It is **not** a maximum session budget. A session
  can spend less than, or potentially more than, a naive `price × hours`
  estimate depending on billing components.
- Spot pricing is variable. The observed spend can include compute, managed
  disk, public IP/network allocations, discounts and taxes.
- The managed disk may continue to be billed while the VM is `STOPPED`.
- No per-line billing export was available. Do not treat USD 1.70 as a
  reproducible rate for future sessions.

---

## Lifecycle states

| State | Compute billing | What it means |
| --- | --- | --- |
| `RUNNING` | Billed while running | GPU, vCPU and RAM are allocated; the inference endpoint is available. |
| `STOPPED` | Compute stopped; **possible persistent charges** | The instance is not running, but its managed disk, IP allocation or other attached resources may still be billed. Restart is possible. |
| `DELETED` | Instance removed; attached resources follow their own lifecycle | The compute instance is gone. Managed disks may need to be deleted separately or may be retained depending on configuration. This is destructive and was **not** performed. |
| Preemptible / Spot | Capacity-dependent | The instance can be reclaimed by the provider. Availability and price vary. |

**Session 001 close:** the VM was **stopped**, not deleted.
A read-only Nebius CLI query on 2026-10-19 found **one instance in
`eu-north1` with state `STOPPED`**. No resources were created, started,
restarted or deleted as part of the documentation work.

---

## Cost drivers

| Driver | Notes |
| --- | --- |
| GPU class | H200 is the dominant cost; the 0.6B model does not reduce GPU price. |
| Uptime | The VM is billed while running, including model download and startup. |
| Model download | ~1.40 GiB downloaded on first start; network and time cost. |
| Storage | 100 GiB managed disk; may persist while `STOPPED`. |
| IP / network | Any reserved or public IP allocation may have its own charge. |
| Spot policy | A maximum price policy limits the Spot bid, not the accumulated spend. |

---

## Cleanup checklist for a future session

Run this **read-only** checklist before deleting anything. Confirm each item in
the provider console or with read-only CLI queries. Do not delete resources
without explicit approval.

- [ ] **Instances** — list all instances in every project/region; confirm which
      are `RUNNING`, `STOPPED` or obsolete.
- [ ] **Disks** — list managed disks attached and unattached; confirm retention
      policy and whether they are still billed.
- [ ] **IP addresses / allocations** — list reserved and public IPs; release only
      after approval.
- [ ] **Security Groups** — list dedicated groups; remove rules or groups only
      after confirming no instance depends on them.
- [ ] **Spot policies** — list active policies and maximum prices; remove unused
      policies.
- [ ] **Other billable resources** — snapshots, images, buckets, load balancers,
      NAT gateways, monitoring.
- [ ] **Billing / usage** — export or review the usage breakdown for the session
      period; reconcile against the observed USD 1.70.
- [ ] **Evidence** — confirm the private originals are preserved and the public
      mirror is sanitized before deleting any local copy.

### Read-only helper

```bash
python3 scripts/check-vm-state.py
```

The helper prints only project names, instance names, states and regions. It
does not print tenant/project IDs, credentials or IP addresses, and it does not
modify resources.

---

## Cost reporting rules for future experiments

1. Record start and end timestamps in UTC.
2. Record the provider's billing state (`RUNNING`, `STOPPED`, `DELETED`) at close.
3. Separate **observed spend** from **estimated hourly rate**.
4. State whether the rate is on-demand, Spot or a maximum-price policy.
5. Export the billing breakdown when available; otherwise mark the figure as
   **unreconciled**.
6. Never present a short-session average as a long-term projection.

---

## Status

- Session 001 spend: **~USD 1.70 observed, unreconciled**.
- VM state at close: **STOPPED** (read-only verification).
- Resources deleted: **none**.
- Next action: reconcile with Billing before Session 002 and decide whether to
  keep or delete the stopped instance and its disk.
