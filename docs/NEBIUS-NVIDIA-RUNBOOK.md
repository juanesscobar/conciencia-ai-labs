# Nebius / NVIDIA telemetry runbook — read-only preparation

Status: **not executed**. This is a bounded preparation for a future operator-run cloud test; it neither creates Nebius resources nor reads credentials. A captured file is `REAL_CAPTURE`, never `SIMULATED`, and missing fields remain `null`.

## Contract and collection

The collector issues one read-only command, with a 10-second timeout:

```powershell
nvidia-smi --query-gpu=timestamp,index,uuid,name,driver_version,pstate,temperature.gpu,utilization.gpu,power.draw,memory.used,memory.total --format=csv,noheader,nounits
```

It records the raw CSV, collection time, command/query version, GPU UUID/name, driver version, units (`C`, `%`, `W`, `MiB` in the query field names) and all values returned by the driver. It does not introduce DCGM: `nvidia-smi` supplies the present contract and DCGM is a later, separately justified option. NVIDIA documents `--query-gpu` and CSV output in its [nvidia-smi documentation](https://docs.nvidia.com/deploy/nvidia-smi/index.html); consult the exact driver manual on the instance before running.

Capture and analysis are separate. On the temporary instance, save the command output as UTF-8 CSV. After transfer to the local Lab, import it without a GPU:

```powershell
py -3.12 scripts/collect_nvidia.py --input capture.csv --out artifacts/nvidia-capture.json
```

The explicit local capture mode exists only for an operator who is already on an authorized instance; it is never the default:

```powershell
py -3.12 scripts/collect_nvidia.py --execute --out capture.json
```

## Short operator trial

1. Before provisioning, record instance/GPU hourly price, region, image, disk policy and the approved maximum duration. Estimate cost as `hourly price × ceiling(minutes / 60)` plus any documented storage/egress charges. This repository has no current price and makes no cost claim.
2. On an authorized temporary GPU instance, record one capture at rest.
3. Run one normal, already-authorized workload; do not use this Lab to schedule or control it. Capture at its normal observation interval.
4. Stop the workload, wait for rest, and capture again.
5. Export CSV and import locally with the command above. Review UUID, timestamps, units, driver version, and nulls before analysis.
6. Stop/terminate the compute resource and delete any temporary disk, snapshot, IP, or other billable resources according to the provider console. Verify the provider shows no remaining billable resources.

Requirements: operator access to Nebius, an approved cost ceiling, a documented workload, NVIDIA driver with `nvidia-smi`, UTC clock, and an approved secure transfer path. No credential, resource identifier, workload command, or price belongs in this repo.

## Limits

The collector does not prove Nebius integration, scheduler state, job attribution, power accuracy, or physical recovery. No Nebius call has been made. `REAL_CAPTURE` is evidence of one imported driver output, not a control-plane approval and not permission to run `pause_admission`.
