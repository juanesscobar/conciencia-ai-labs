# EXP-001 landing handoff — data and visual brief

Audience: OpenClaw / `labs-web`. This repository does **not** edit the landing. Generate the data package locally:

```powershell
py -3.12 -m ai_factory_lab --export-comparison artifacts/landing-exp001
```

Files: `comparison.json` (three comparable decisions), `timeline.json` (only observed model points), `results.json` (full reproducible runs), and `manifest.json` (hashes). They all declare `environment: SIMULATED`; the package is deterministic with seed 7 and the virtual start clock. It is a reproduction export (`interactive: false`), not an interactive execution control.

Visual sequence: **observación → evidencia → propuesta → decisión → acción → verificación**.

- Observation/evidence: plot the four `before` temperature readings as points, not a smoothed or invented series. Label synthetic / SIMULATED.
- Proposal: `pause_admission` for `sim-node-001`, with plan/evidence hash visible in a detail drawer.
- Decision comparison: approved = `PASS` and action executed; rejected = `BLOCKED`, no action; absent = `BLOCKED`, no action.
- Action/verification: only approved has the action event and five post-action temperature points. Explain that cooling and job completion are model assumptions, not hardware observations.
- Avoid status colors that imply human approval or real GPU control. The decision is a test fixture.

Suggested headline: “A reproducible simulation of a governed thermal response.”

Required footnote: “SIMULATED data. The fixture approval is not a human authorization; no NVIDIA or Nebius infrastructure was controlled.”
