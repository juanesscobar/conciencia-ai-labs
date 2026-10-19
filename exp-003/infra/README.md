# EXP-003 infrastructure notes

## What was actually used

Session 001 was provisioned **through the Nebius console**. The repository does
not contain Terraform, Pulumi or cloud-init for this experiment.

- Provider: Nebius AI Cloud
- Region: `eu-north1`
- GPU: 1× NVIDIA H200 NVLink
- vCPU / RAM: 16 vCPU / 200 GiB provisioned
- Disk: 100 GiB SSD
- OS: Ubuntu 24.04 LTS with CUDA 13.0 and NVIDIA driver 580.173.02
- Access: SSH with a public key; dedicated Security Group
- Inference port: host loopback only (`127.0.0.1:8000`)

## What is in this directory

| File | Purpose | Tested? |
| --- | --- | --- |
| `docker-run.sh` | Reference vLLM launch command, derived from the observed container configuration | No (reference only) |

## What is not here

- No Terraform or Pulumi.
- No cloud-init.
- No automatic instance provisioning.
- No automatic deletion or cleanup.

Those items are candidates for Session 002 and must be validated before being
described as reproducible automation.
