# Ouroboros — Documentation

Ouroboros is an autonomous application-security platform. Point it at a target — a live URL or a GitHub repository — and it finds real, exploitable vulnerabilities, proposes fixes, and walks a human through approving and shipping the patch, entirely from chat.

It closes the loop that most security tooling leaves open: scanners produce a list nobody reads, and fixes live in a backlog nobody prioritizes. Ouroboros scans, proves exploitability, drafts the fix, gets sign-off over WhatsApp or Slack, opens the PR, and re-verifies the patch actually closes the hole — then remembers the outcome so the next scan is smarter.

## Start here

| Document | What's in it |
|---|---|
| [WORKFLOW.md](WORKFLOW.md) | The full user journey: submitting a target, triaging findings, approving fixes, and the two resilience feedback loops. Read this first. |
| [ARCHITECTURE.md](ARCHITECTURE.md) | System components, how they talk to each other, and where state lives. |
| [API.md](API.md) | Every orchestrator endpoint the frontend (or anything else) calls. |
| [DEPLOYMENT.md](DEPLOYMENT.md) | Running Ouroboros locally or on a server — processes, ports, environment variables. |

## What it does, in one pass

1. **Scan.** A target URL or repository is handed to **Fang**, a network of specialized offensive agents (SAST/SCA, injection, auth, XSS, deserialization, and more) that work the surface in parallel and only report findings they can actually demonstrate — not lint-style guesses.
2. **Triage.** Findings land on a live dashboard with severity, CVE/CWE mapping, and a running attack log, plus a research agent that cross-references the target's stack against newly disclosed CVEs in real time.
3. **Approve.** The operator pairs their WhatsApp as a companion device. **Ouro**, the remediation agent, walks them through GitHub authorization, presents the findings for approval, and — for anything critical — asks for an explicit go/no-go before touching code.
4. **Fix.** Approved findings get patched, committed to a branch, and opened as a pull request against the governance-approved repository, with a re-attack pass to confirm the patch actually closes the exploit.
5. **Learn.** Every human judgment call — a finding marked false positive, a PR declined with a reason — is captured as structured feedback and logged against that exact signature, so future scans of the same target don't repeat the same false alarm or the same broken fix.

## Naming

The product surface uses two names consistently, everywhere — UI, chat, docs:

- **Fang** — the scanning and exploitation engine.
- **Ouro** — the remediation agent: WhatsApp/Slack conversation, GitHub authorization, PR creation, and the feedback loops.

There is no third name for anything user-facing. If you're extending this system, keep it that way.

## Project layout

```
ouro/
├── frontend/       Next.js dashboard — scan submission, live findings, agent graph, gateway pairing
├── orchestrator/   FastAPI service — owns scan lifecycle, findings, and the remediation handoff
├── fang/           the scanning engine
├── ouro.agent/     the remediation agent runtime
├── skills/         Ouro's conversation skills (remediation workflow, compliance reporting)
└── docs/           you are here
```
