# API Reference

The orchestrator exposes a REST + SSE API on `:7891`. This is the full surface the frontend uses; nothing else in the system is called directly by clients.

All responses are JSON unless noted otherwise. `run_id` is an 8-character identifier minted when a scan is started or adopted; it is not the same as the underlying run's directory name.

---

## Scans

### `POST /scan`

Launch a new scan against a target.

```json
// Request
{ "url": "https://example.com", "scan_mode": "quick" }

// Response
{ "run_id": "a1b2c3d4", "run_name": "ouro-a1b2c3d4" }
```

Accepts either a live URL or a Git repository URL as `url`. The scan engine detects which and adjusts its approach accordingly (live probing vs. source-level review of a clone).

### `POST /scan/adopt`

Register an already-running or already-finished scan that wasn't started through `/scan`, for example one launched manually, or left over from a restarted orchestrator, so the frontend can pick it up.

Query params: `run_name` (optional, defaults to the most recently modified run), `run_id` (optional, re-registers under a specific id rather than minting a new one, used to heal a frontend's existing reference after a restart).

```json
{ "run_id": "a1b2c3d4", "run_name": "ouro-a1b2c3d4", "url": "https://example.com", "status": "completed" }
```

### `GET /scan/{run_id}/events`

Server-Sent Events stream. Pushes a `finding` event for each new finding as it's written, and a periodic `status` event with the running count. The connection stays open for the life of the scan.

```
data: {"type": "finding", "finding": { ... }}
data: {"type": "status", "status": "running", "findings_count": 4}
```

### `GET /scan/{run_id}/findings`

Point-in-time snapshot of everything found so far. This is the fallback used alongside the SSE stream. A long-lived connection that fails to establish on its first attempt won't retry itself, so the frontend also polls this on an interval while a scan is active.

```json
{ "findings": [ { "id": "...", "severity": "critical", "cve": "...", "title": "..." } ], "status": "running" }
```

### `GET /scan/{run_id}/agents`

The live agent graph: every specialist agent spawned for this run, its parent, status, and message/tool-call counts. Powers the dashboard's agent graph view.

### `GET /scan/{run_id}/transcript`

Full event transcript for the run: tool calls, tool results, and agent messages, reconstructed from the scan engine's own session state.

### `GET /scan/{run_id}/status`

```json
{ "status": "running", "url": "https://example.com" }
```

### `POST /scan/{run_id}/research`

Trigger the research agent for this run, cross-referencing the target's inferred stack against recently disclosed CVEs, independent of the main scan. Idempotent per run; a duplicate trigger while one is already in flight is a no-op.

### `GET /scan/{run_id}/research`

```json
{ "ready": true, "findings": [ { "cve": "...", "summary": "..." } ] }
```

### `GET /report/{run_id}`

```json
{ "report": "<markdown or null>", "compliance_report": "<markdown or null>", "findings": [ ... ] }
```

---

## Remediation

### `POST /fix-all`

Kick off the remediation workflow for a completed scan: the remediation agent is launched with the run's findings summary and the currently-paired phone number, and starts the approval conversation over WhatsApp.

```json
// Request
{ "run_id": "a1b2c3d4", "target_url": "https://example.com", "phone_number": "15551234567" }

// Response
{ "status": "started", "run_id": "a1b2c3d4", "findings_count": 12, "message": "..." }
```

This call returns immediately. The actual conversation happens asynchronously over WhatsApp/Slack, not over this HTTP connection.

---

## Gateway (WhatsApp pairing)

### `POST /gateway/connect`

Start or resume pairing. If no phone number was previously paired, or a *different* number is submitted than whoever is currently paired, this forces a fresh QR pairing rather than silently reusing stale session credentials. A new phone always fully replaces the previous one.

```json
// Request
{ "phone_number": "+15551234567" }

// Response (already paired to this number)
{ "status": "already_paired", "phone": "15551234567" }

// Response (fresh pairing started)
{ "status": "connecting", "phone": "15551234567" }
```

### `GET /gateway/qr`

Poll this while `status` is `connecting` until `qr_data` is non-null, then render it as a QR code for the operator to scan.

```json
{ "state": "waiting_qr", "qr_data": "<pairing payload>", "phone": "15551234567" }
```

### `GET /gateway/status`

```json
{ "state": "connected", "disk_state": "connected", "phone": "15551234567" }
```

### `POST /gateway/restart`

Restart the remediation gateway process.

### `POST /gateway/disconnect`

Reset in-memory gateway state so the frontend can start a fresh pairing flow. Does not remove the linked WhatsApp session by itself; a subsequent `/gateway/connect` with a new number handles that.

---

## Misc

### `POST /demo/seed`

Seed a demo scan with pre-recorded findings, for presenting the dashboard without running a live scan.

```json
{ "run_id": "demo-1234", "findings_count": 20 }
```

### `GET /health`

```json
{ "status": "ok" }
```
