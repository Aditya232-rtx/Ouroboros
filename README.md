# Ouroboros

**Find real vulnerabilities. Fix them from your phone. Prove the fix worked.**



https://github.com/user-attachments/assets/39b7905c-4688-4ce2-874d-e3970511ad43



## Overview

Ouroboros is an autonomous application-security platform: point it at a live URL or a GitHub repository and it scans for exploitable vulnerabilities, triages them on a live dashboard, and drives the entire remediation from chat. Approve a fix with a WhatsApp reply from your phone — no dashboard, no laptop required — and it patches the code, opens the pull request, and re-attacks the patched path to prove the exploit is actually closed, not just assumed fixed. Every time a human overrides the system — a false positive, a declined PR — that reason is captured against the exact finding, so the next scan of the same target gets quieter and smarter instead of repeating itself.

Most security tooling stops at "here's a list." Ouroboros closes the loop: scan → triage → approve from your phone → patch → verify → remember.

## What it does

- **Scans** a live URL or a Git repository with a network of specialist offensive agents — SAST/SCA, injection, auth, XSS, deserialization, and more — that only report findings they can actually demonstrate, not lint-style guesses.
- **Surfaces findings live** on a dashboard: severity, CVE/CWE mapping, an attack log, and a research agent cross-referencing your stack against newly disclosed CVEs in real time.
- **Puts approval in your pocket.** Pair your WhatsApp, review findings, approve a fix with a reply. Critical findings get an explicit extra confirmation before anything is touched.
- **Fixes and proves it.** Each approved finding gets patched on its own branch, opened as a PR, and re-attacked to confirm the exploit no longer works — not assumed fixed, verified fixed.
- **Learns from being overruled.** Mark a finding a false positive or decline a PR, and the reason is captured against that exact signature — so the next scan of the same target doesn't repeat the same false alarm or the same broken fix.

## Quick start

> **Important:** Ouroboros brings its own API keys — it doesn't ship with or share anyone else's. You'll need your own LLM provider key (for the scan engine and the remediation agent) and your own GitHub authentication before fixes can be opened as PRs. See [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) for exactly what to set.

```bash
git clone <this-repo>
cd ouroboros
./start-all.sh
```

Then open `http://localhost:3000`, paste a target, and watch it work. Full setup, environment variables, and troubleshooting: [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md).

## How it's put together

```
frontend/       Next.js dashboard — scan submission, live findings, agent graph, WhatsApp pairing
orchestrator/   FastAPI service — owns the scan lifecycle and the handoff to remediation
fang/           the scanning and exploitation engine
ouro.agent/     the remediation agent runtime — WhatsApp/Slack, GitHub auth, PR creation
skills/         Ouro's conversation workflows: remediation and compliance reporting
docs/           architecture, API reference, deployment, full workflow walkthrough
```

Full system design: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## Tech stack

| Layer | Technology |
|---|---|
| **Frontend** | Next.js 16, React 19, TypeScript, Tailwind CSS 4 |
| **Auth** | Supabase |
| **Agent graph & live views** | React Flow (`@xyflow/react`), Dagre for graph layout |
| **WhatsApp pairing UI** | `qrcode.react` |
| **Backend** | FastAPI (Python), Uvicorn, Pydantic |
| **Live updates** | Server-Sent Events (`sse-starlette`), with a polling fallback |
| **Sandboxing** | Docker — every scan target runs isolated |
| **Finding format** | SARIF 2.1.0 |
| **Remediation channels** | WhatsApp (companion-device pairing), Slack (Socket Mode) |
| **Version control integration** | GitHub (device-flow auth, PR automation via `gh`) |

## Documentation

| | |
|---|---|
| [docs/WORKFLOW.md](docs/WORKFLOW.md) | The full user journey — target submission through both resilience feedback loops. Start here. |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | Components, data flow, and the reasoning behind the harder design calls. |
| [docs/API.md](docs/API.md) | Every orchestrator endpoint. |
| [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) | Setup, environment variables, operational notes. |

## Why the WhatsApp/Slack thing isn't a gimmick

A patch nobody reviews is worse than no patch. Routing approval through a channel a human actually checks — and asking *why* whenever they override the agent — is what keeps an autonomous fixer from becoming an autonomous liability. The system is only as trustworthy as the review step in front of it, so that step is deliberately never optional, never batched, and never silent.

## License

See [ouro.agent/LICENSE](ouro.agent/LICENSE) and [fang/LICENSE](fang/LICENSE) for the licensing of the underlying engines this project builds on.
