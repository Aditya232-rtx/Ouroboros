# Deployment

Running Ouroboros locally or on a server: processes, ports, environment, and the operational quirks worth knowing before you hit them in front of someone.

## Prerequisites

- Node.js and npm (frontend)
- Python 3 with a virtualenv (orchestrator)
- Docker, running (the scan engine sandboxes every target in an isolated container)
- A phone with WhatsApp, for pairing the remediation agent
- `gh` (GitHub CLI), authenticated as the account that should own remediation PRs

## Processes

Three things run independently:

| Process | Port | Purpose |
|---|---|---|
| Frontend | `3000` | Next.js dashboard |
| Orchestrator | `7891` | FastAPI service: scan lifecycle, findings, remediation handoff |
| Remediation gateway | n/a | WhatsApp/Slack connection for the remediation agent; launched on demand, not tied to a fixed port |

`./start-all.sh` from the repo root starts the frontend and orchestrator, checks Docker is up (launching it if not), and prints both URLs. Pass `--tunnel` to also stand up a public tunnel to the orchestrator (useful for pairing WhatsApp from a phone that isn't on the same network); requires `cloudflared`.

The remediation gateway is not started by `start-all.sh`; it's launched by the orchestrator when the operator pairs WhatsApp through the dashboard, or can be run standalone for scripting/testing.

## Configuration

Each component reads its own `.env`:

- `orchestrator/.env`: the scan engine's LLM provider, model, and reasoning effort; the orchestrator's port.
- The remediation agent's runtime configuration (channel credentials, allowed users, default model) lives in its own config, separate from the orchestrator.

At minimum, set a scan-engine model and API key before running a real scan. Without one, `start-all.sh` will start the services but scans will fail immediately.

## First-time WhatsApp pairing

1. Click **Deploy Agent** in the dashboard and enter the operator's phone number.
2. If no session is currently linked, a QR code appears. Scan it with the *same* phone whose number was entered. Pairing links WhatsApp as a companion device, the same mechanism as WhatsApp Web.
3. Once connected, that number becomes both the allowed sender and the default delivery target for remediation messages.

**A new number always replaces the previous one.** If someone else's phone was previously paired, entering a different number forces a fresh QR pairing rather than silently continuing to route through the old session, which matters if more than one person tests the flow on the same machine.

## Operational notes

A few things worth knowing before they surprise you mid-demo:

- **The remediation gateway's session-resume behavior can outlast a restart.** If a conversational turn is interrupted mid-task, a plain restart is not guaranteed to prevent it picking back up where it left off. If you need to be certain an in-progress task has actually stopped, not just that the process restarted, verify by checking whether the target repository's working tree actually changed, not just by checking the process list.
- **Prefer bounded, single-purpose invocations over the live conversational gateway for anything that touches a real repository.** The live gateway is good for a natural chat experience; it is not the right tool to hand an open-ended "fix this and open a PR" instruction to unsupervised, especially against a repository that wasn't the one you meant.
- **WhatsApp self-chat message delivery does not require the full gateway process.** The messaging bridge and the conversational-agent loop are separable. If you only need to push a message (not receive and act on replies), running the messaging layer standalone is lower-risk than bringing up the full gateway.
- **Verify delivery, don't trust the return value.** A send command returning success does not always mean the message reached the platform. Confirm via the platform's own message history or delivery logs before treating something as sent.

## Troubleshooting

| Symptom | Likely cause |
|---|---|
| Scan fails immediately on submit | No LLM provider/model configured in `orchestrator/.env` |
| Docker-dependent scan hangs at startup | Docker Desktop isn't running; `start-all.sh` will try to launch it, but give it a few seconds |
| Findings dashboard stuck at zero despite a completed scan | Frontend adopted the run but never fetched its findings; check that the adopt flow fetches findings for already-completed runs, not just running ones |
| WhatsApp messages not arriving | Confirm the paired number matches who's actually sending; a mismatch here silently drops inbound messages by design (it's the anti-spoofing check, not a bug) |
| A remediation task keeps running after you thought you stopped it | See "session-resume behavior" above; check the actual filesystem state of the target repo, not just whether you restarted a process |
