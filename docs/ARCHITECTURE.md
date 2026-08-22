# Architecture

## Components

```
<img width="1024" height="559" alt="image" src="https://github.com/user-attachments/assets/3eddfb2c-abbf-4bed-882a-12e8f8b00a7e" />

```

### Frontend

A Next.js app that is the single operator-facing surface. Owns:

- Target submission and live dashboard rendering (findings, agent graph, vulnerability timeline).
- The `GatewayModal` — WhatsApp pairing flow (QR code, phone number, connection status).
- Client-side scan state, kept in sync with the orchestrator via Server-Sent Events with a polling fallback (see below).

The frontend never talks to Fang or Ouro directly — everything routes through the orchestrator.

### Orchestrator

A FastAPI service that is the seam between the operator-facing frontend and both agent systems. It:

- Launches Fang scans as sandboxed subprocesses, one per run, and tracks each as an in-memory record (`run_id → run directory, status, target URL`).
- Streams findings to the frontend as they're written to disk, via SSE (`/scan/{run_id}/events`) with a REST fallback (`/scan/{run_id}/findings`) for when a long-lived connection isn't reliable.
- Exposes the scan's live agent graph and transcript by reading Fang's own run-state files — it doesn't reimplement that state, it projects it.
- Owns the WhatsApp pairing lifecycle (`/gateway/*`): generating and rotating the QR code, tracking connection state, and — critically — ensuring a *new* phone number pairing always fully replaces whoever was previously paired, rather than silently reusing stale session credentials.
- Hands off to Ouro (`/fix-all`) once an operator wants to move from findings to remediation, passing the run's findings summary and the paired phone number.

The orchestrator holds no long-term state of its own beyond the current process's lifetime — durable state lives in the run directory on disk (see below), so a restart doesn't lose scan history, only the in-memory index pointing to it (recoverable via the run-adoption endpoint).

### Fang

The scanning and exploitation engine. Runs each target as an isolated, sandboxed job and writes its findings and live state to a dedicated run directory as it works:

- `findings.sarif` — the finding set, SARIF 2.1.0 format.
- `run.json` — target metadata, status, timing.
- `.state/agents.json`, `.state/agents.db` — the live agent graph (which specialist is running, its status, its message/tool history) that the dashboard's agent view projects directly.

Fang accepts either a live URL or a Git repository as a target. For a repository, it clones into an isolated workspace and performs source-level analysis rather than live probing — dependency CVEs, SAST findings, and business-logic review all come from the same engine, the target type just changes what's reachable.

### Ouro

The remediation agent. Runs as a persistent gateway process that owns two conversational channels — WhatsApp (the primary approval channel, paired per-operator) and Slack (team escalation and feedback) — plus a set of task-specific "skills" that encode the step-by-step remediation and compliance-reporting workflows.

Ouro is invoked by the orchestrator two ways:

1. **Headless, one-shot** — for a specific workflow step (send the opening message, present findings, apply one fix), the orchestrator launches Ouro as a bounded single-turn process with an explicit prompt and exits when that one step is done. This is the reliable path: verifiable input, verifiable output, no ambiguity about what it's allowed to do.
2. **Live gateway** — a long-running process that listens for and responds to inbound WhatsApp/Slack messages conversationally. This is what makes the channel feel like a normal chat rather than a form.

### Storage

There is no database. State lives in two places:

- **The run directory** (one per scan) — the durable record: findings, agent transcripts, compliance reports, and a structured false-positive log (`false_positives.json`) that accumulates one entry per finding a human has overridden, with the reason, so future scans of that target can down-weight the same signature.
- **The orchestrator's in-memory scan index** — ephemeral, rebuilt on demand by pointing it at an existing run directory. This is deliberate: scan results should survive a process restart; a mid-flight in-memory pointer to "which run_id maps to which directory" doesn't need to.

## Data flow — a scan, end to end

1. Frontend `POST /scan` → orchestrator launches Fang as a subprocess, returns a `run_id`.
2. Frontend opens `GET /scan/{run_id}/events` (SSE). Orchestrator tails the run directory and pushes new findings as they're written.
3. Frontend renders findings live; a 5-second poll of `/scan/{run_id}/findings` runs alongside the stream as a safety net for the case where the SSE connection didn't establish cleanly.
4. Operator pairs WhatsApp via `/gateway/connect` → `/gateway/qr` (polled by the frontend) → `/gateway/status`.
5. Operator triggers remediation → `POST /fix-all` → orchestrator launches Ouro headless with the findings summary and paired phone number.
6. Ouro conducts the approval conversation over WhatsApp/Slack, applies fixes, opens PRs, and writes feedback (false positives, declined-fix reasons) back into the run directory.

## Design decisions worth knowing about

- **Single-message-then-stop.** Every remediation step is a bounded, single-purpose invocation rather than a long autonomous loop. This trades some latency for the property that matters more here: an agent that's about to push code to a real repository should not decide on its own to keep going past what it was explicitly asked to do.
- **SSE with a polling fallback, not SSE alone.** A long-lived stream that fails silently on its first connection attempt is worse than no stream at all — the fallback exists because that failure mode is real, not hypothetical.
- **Disk as the source of truth.** Findings, transcripts, and feedback all live in the run directory rather than in a database or in-memory store, so a process restart is a recoverable event, not a data-loss event.
