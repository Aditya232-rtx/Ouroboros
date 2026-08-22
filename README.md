# Ouroboros

**Find real vulnerabilities. Fix them from your phone. Prove the fix worked.**

Ouroboros is an autonomous application-security platform. Point it at a target — a live URL or a GitHub repository — and it scans for exploitable vulnerabilities, drafts the fix, gets your sign-off over WhatsApp or Slack, opens the pull request, and re-attacks the patched code to prove the fix actually holds.

Most security tooling stops at "here's a list." Ouroboros closes the loop: scan → triage → approve → patch → verify → remember.

## What it does

- **Scans** a live URL or a Git repository with a network of specialist offensive agents — SAST/SCA, injection, auth, XSS, deserialization, and more — that only report findings they can actually demonstrate, not lint-style guesses.
- **Surfaces findings live** on a dashboard: severity, CVE/CWE mapping, an attack log, and a research agent cross-referencing your stack against newly disclosed CVEs in real time.
- **Puts approval in your pocket.** Pair your WhatsApp, review findings, approve a fix with a reply. Critical findings get an explicit extra confirmation before anything is touched.
- **Fixes and proves it.** Each approved finding gets patched on its own branch, opened as a PR, and re-attacked to confirm the exploit no longer works — not assumed fixed, verified fixed.
- **Learns from being overruled.** Mark a finding a false positive or decline a PR, and the reason is captured against that exact signature — so the next scan of the same target doesn't repeat the same false alarm or the same broken fix.

## Quick start

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
