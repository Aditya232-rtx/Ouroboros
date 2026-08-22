# Ouroboros — Revised Implementation Plan
### Local Hermes (Ouro bot) + Strix, no rebrand, no Honcho

*Companion to `hackathon_mvp_ouroboros.md` and `ouroboros_full_flow.mermaid` — this supersedes their gateway-orchestration and multi-tenancy sections for the current phase.*

---

## 0. What changed, and what that buys you

- **No "Fang" rebrand** — you're driving the real `strix` CLI directly. That means you inherit Strix's *own* run artifacts, its own local web dashboard (`strix view`), and its own agent-graph UI for free — the screenshot you sent is that dashboard's **Agent graph** tab, not something you need to build.
- **No Honcho** — you lose a shared Postgres/pgvector memory layer, but you also lose the entire per-user multi-tenant gateway-session orchestration layer that the old plan's Section 5.4 flagged as "real infrastructure work." For a single-machine hackathon demo, Hermes's own on-disk state (`~/.hermes/`) is enough. Treat this as **one live demo session at a time**, not a scalable SaaS — that's a simplification, not a gap.
- **One Ouro bot, not five separate agents** — Research/Governance/Blue/Compliance are best implemented as **skills** (procedural knowledge Ouro switches between) inside the one Hermes profile you've already set up, the same way you added the research skill. Hermes doesn't have a native "spawn distinct persona sub-agents" primitive the way Strix does internally — don't build toward that.

## 1. Reality check on what Hermes and Strix actually expose

Your plan assumes a couple of things that are worth correcting *before* you build against them, so you don't lose hours chasing files/endpoints that don't exist:

| You assumed | What's actually there |
|---|---|
| Frontend hits "Hermes's default port" for everything | Hermes's API server (default **port 8642**) is a real, documented HTTP API — but it's a generic OpenAI-compatible + agent-run API. It does **not** expose gateway-config endpoints (pairing a WhatsApp number, restarting the gateway). Those are CLI/config-file operations only. See §3. |
| `strix.log`, `run.json`, `findings.sarif` streamed continuously | Local Strix CLI runs write to `strix_runs/<run-name>/{report.md, findings.json, proof-of-concepts/, logs/}`, updated live as the scan progresses. SARIF export is a **managed-cloud** feature (`app.strix.ai` REST API), not something the open-source CLI writes to disk locally. Point your frontend at `findings.json` + `logs/`, not `findings.sarif`. |
| Need to reverse-engineer Strix's agent-graph rendering | You don't — `strix view` **is** that rendering, shipped prebuilt with the CLI, reading run files straight off disk, no cloud upload. See §4. |

## 2. Components you need on the local machine

```
┌─────────────────────────────────────────────────────────────┐
│ Local machine (Docker Desktop running)                       │
│                                                                │
│  Hermes Agent (profile: ouro)                                 │
│   ├─ hermes gateway         → WhatsApp bridge (Baileys)       │
│   ├─ API server :8642       → /v1/chat/completions, /v1/runs  │
│   └─ skills: research, (new) compliance                       │
│                                                                │
│  Strix CLI (invoked by Ouro via its shell tool)                │
│   └─ writes strix_runs/<run>/{report.md,findings.json,logs/}  │
│   └─ strix view              → local read-only/live dashboard │
│                                (agent graph, steering, history)│
│                                                                │
│  Orchestrator (NEW — small local service, see §3)              │
│   └─ the only piece that does gateway pairing/restart          │
│                                                                │
│  cloudflared tunnel(s) → exposes 8642 + orchestrator publicly │
└─────────────────────────────────────────────────────────────┘
                          ▲
                          │ HTTPS (tunnel)
                          ▼
                 Deployed public frontend
```

The one genuinely new piece of infrastructure is the **orchestrator** — a thin local service, because neither Hermes nor Strix ships a REST endpoint for "pair WhatsApp" or "restart the gateway." Everything else (triggering a scan, polling progress, resolving approvals) can go straight through Hermes's existing API server.

## 3. Part 1 — Frontend → tunnel → local Hermes → Strix scan

**Setup, once:**

```bash
# Hermes, as a profile dedicated to this demo
hermes profile create ouro
# ~/.hermes (or the profile's HERMES_HOME) config.yaml:
gateway:
  api_server:
    enabled: true
    port: 8642
    host: 0.0.0.0            # tunnel needs it reachable, not just 127.0.0.1
    key: <a real secret>
    cors_origins: https://<your-deployed-frontend-domain>
```

```bash
# Strix, once
export STRIX_LLM="anthropic/claude-sonnet-4-6"   # or whichever provider you're using , i'll provide api key for other model from the aws accound aws bedrock 
export LLM_API_KEY="..."
```

```bash
# expose it
cloudflared tunnel --url http://localhost:8642
# note the https://<random>.trycloudflare.com URL (or use a named tunnel + your own domain)
```

**Runtime flow when the judge/user enters a URL:**

1. Frontend `POST`s to `https://<tunnel>/v1/runs` (bearer token = your `key`) with an instruction telling Ouro: *"Run a quick Strix scan against `<target-url>` and report findings."* Ouro's shell tool then actually runs:
   ```bash
   strix -n --target "<target-url>" --scan-mode quick
   ```
   `-n` keeps it headless (no TUI), `--scan-mode quick` trades thoroughness for speed (Strix's default is `deep`).
2. Frontend opens `GET /v1/runs/{id}/events` (Server-Sent Events) and streams progress into the UI — no polling loop needed, this is a native Hermes capability.
3. In parallel, the frontend (or the orchestrator) tails `strix_runs/<run-name>/findings.json` for the structured vulnerability list to render your read-only report cards (severity, CVE/CWE, description) — this file updates as findings land, not just at the end.
4. When the run event stream reports completion, flip the UI from "scanning" to "report ready" and reveal **Fix All**.

For a local codebase repo target vs. a live URL target, Strix accepts both transparently (`--target https://github.com/org/repo` or `--target https://your-app.com`) — no branching needed on your side beyond passing through whatever the user typed.

## 4. Part 2 — Agent graph, logs, and the Research sidebar

Two honest options, pick based on time left:

**Option A — embed, don't rebuild (recommended default).**
`strix view` starts a local server bound to `127.0.0.1` on a random port, serving a prebuilt UI with **Overview / Vulnerabilities / Agent graph / Steering / History / Reports** tabs — this is exactly the screenshot you sent. Have the orchestrator launch `strix view --run <run-name>` once a scan starts, capture its tokened URL from stdout, and reverse-proxy that path through the same tunnel. Iframe it into a panel of your frontend. You get the real agent graph, click-to-see-that-agent's-logs, and even the **Steering** tab (send live instructions mid-scan) for near-zero build cost. Trade-off: it's Strix's own visual style, not yours, inside that panel.

**Option B — build your own renderer (only if you have time and want it on-brand).**
Strix tracks the graph as plain data you can poll instead of iframing anything:
```python
# shape, from Strix's agents_graph tool
{
  "nodes": {
    "agent_abc123": {
      "id": "agent_abc123", "name": "JWT Specialist", "task": "Test authentication",
      "status": "running",  # running | completed | error | waiting
      "parent_id": "agent_xyz789", "created_at": "...", "result": None,
    }
  },
  "edges": []  # parent-child relationships
}
```
Poll this (or read it out of the run's `logs/`) and drive a React Flow / D3 graph yourself, with "click a node → show that agent's transcript" wired to the matching log slice. This is real frontend work — budget accordingly, it's not a quick wrapper.

**Research sidebar:** since Research is a skill on Ouro rather than a separate process, schedule it with Hermes's native cron feature (`/api/jobs`, backed by `hermes cron`) so it runs independent of the scan/fix cycle, exactly matching your original "Research runs continuously" requirement. The sidebar polls `GET /api/jobs` (or the events of its last run) through the same tunnelled API server — no separate channel needed.

## 5. Part 3 — Fix All → WhatsApp Gateway (the orchestrator's real job)

This is the one place you can't avoid custom glue, because pairing/restarting the gateway is CLI- and config-file-level, not an HTTP endpoint Hermes ships. Build a small local service (FastAPI/Express — whatever you're fastest in) that runs alongside Hermes and is reachable through the tunnel:

| Orchestrator endpoint | Does |
|---|---|
| `POST /gateway/connect {phone_number}` | Writes the number into the WhatsApp allowlist (config.yaml or `hermes config set`), then runs/restarts `hermes gateway setup` (or `hermes gateway`), capturing whatever it emits for the QR step |
| `GET /gateway/qr` | Returns the raw pairing payload so the frontend renders it as an actual QR image (e.g. the `qrcode` npm package) instead of trying to screenshot a terminal |
| `POST /gateway/restart` | Bounces the `hermes gateway` process (run it as a supervised child process, or a `hermes gateway install` service you can restart) |

**Do this spike first, before building UI around it:** run `hermes gateway setup` manually once and watch exactly *where* the QR data comes from — stdout ASCII, a written session file, or a structured event. Your original plan already flagged this as the highest-risk, easiest-to-underestimate piece ("looks trivial and isn't until you've done it once") — that's still true here, it's just now a Hermes CLI wrapping problem instead of a Baileys-library problem.

Once paired, the session persists under `~/.hermes/platforms/whatsapp/session` and survives restarts — no fresh QR needed unless the user manually unlinks the device or the session invalidates.

Frontend copy should say plainly what's happening: *"This links your WhatsApp as a linked device — like WhatsApp Web — you can unlink it anytime from Settings → Linked Devices."*

## 6. Part 4 — Governance scope, approvals, GitHub auth, fix + PR, report delivery

**GitHub auth "via a link" — use the device flow, don't build a GitHub App.** The simplest, fastest-to-ship version of "give Hermes GitHub auth via a link" is GitHub CLI's own device flow:
```bash
gh auth login --web
```
This prints a one-time code and a `https://github.com/login/device` URL. Have Ouro run this (it already has shell access), capture the code + URL from the output, and send them as the WhatsApp message. The user opens the link, enters the code, approves in their browser — no PAT ever touches the chat transcript, no GitHub App registration needed. Once authenticated, `gh`/`git` calls from Hermes's shell tool inherit the login automatically. (Fallback if you're short on time: a fine-grained PAT pasted and stored via `hermes config set GITHUB_TOKEN "..."`, called out on stage as a shortcut.)

**Governance scope — two layers, be honest about which is which:**
- *Hard gate (enforced):* set `approvals.mode: always_ask` on the terminal/git/write-file tools in `config.yaml`, so every fix-apply and PR-push call actually blocks and waits for a human decision. Hermes's API server has a native run-approval mechanism for this — a gated tool call pauses the run, and a decision posted back to the run resumes it. That's the real mechanism under "approve specific vulnerabilities," whether the approval arrives via a WhatsApp reply (gateway-native) or a frontend button hitting the same endpoint through the tunnel.
- *Soft gate (reasoning-based, not enforced):* "what's not allowed" at a category level (e.g. "don't touch payment code," "block anything in auth without explicit sign-off") isn't a structured Hermes feature — write it as a policy instruction/skill Ouro is told to check before drafting any fix. It shapes behavior; it isn't a hard technical guarantee the way the approval gate is. Say this plainly if it comes up on stage.

**Fix → verify → PR:** unchanged from your original plan — Blue drafts the fix on an isolated branch, Strix re-attacks just that finding (`strix -n --target <original-target> --instruction "re-verify: <finding-id>"` or your original single-finding-verify wrapper), loop up to 3 times, then push the PR via the now-authenticated `gh`/`git`.

**Report delivery:** send the compliance report as a document attachment in the WhatsApp thread (Hermes's gateway supports document sends), and mirror the same content on the frontend's report page by having the orchestrator (or Ouro itself) drop the generated report file somewhere the frontend can fetch it through the tunnel.

## 7. Part 5 — The compliance skill (the piece you haven't started)

You already drafted the hard part in `hackathon_mvp_ouroboros.md` Section 6 — the DPDP §8(5)/§8(6)/§9/§10 mapping table with penalties, and the lighter SOC 2 / ISO 27001 control-mapping table. Turn that directly into a skill:

```
~/.hermes/skills/compliance-report/SKILL.md
```
containing:
1. The DPDP finding-pattern → section → obligation → penalty table (verbatim from your existing doc).
2. The SOC 2 TSC / ISO 27001 Annex A lighter mapping table.
3. A fixed report structure: a technical section (finding → control mapped → status: fixed/open) and a plain-language section for a non-technical reader.
4. An instruction telling Ouro, at the end of a run, to walk every finding (fixed and still-open) through both tables and emit the report in that structure.

This is the one item from your five points that's genuinely unbuilt — everything else in this plan is wiring together things Hermes/Strix already do. Since Hermes skills follow the same `SKILL.md` convention Strix itself uses, this is a self-contained, low-risk build task — do it any time, it doesn't block the rest of the pipeline.

## 8. Suggested build order

1. **Spike the WhatsApp QR capture first** (§5) — highest uncertainty, cheapest to de-risk early with a throwaway script before any UI exists for it.
2. Wire the scan trigger end-to-end: frontend → `POST /v1/runs` → Ouro shells `strix -n --target ... --scan-mode quick` → `findings.json` renders on the frontend. Get one real finding on screen before anything else.
3. Embed `strix view` (Option A, §4) for the agent graph — cheapest win on the list.
4. Build the orchestrator's three gateway endpoints (§5), get a real phone paired end-to-end.
5. `gh auth login --web` flow through the self-chat thread (§6), one real fix → re-attack → PR cycle, approved via the native run-approval mechanism.
6. Write the compliance skill (§7) — independent, do in parallel with anything above once someone's free.
7. Research cron job (§4) + sidebar — lowest priority, it's a visible nice-to-have, not load-bearing for the demo's core proof point.

## 9. Open questions worth answering with a quick local test rather than guessing

- Exact shape of `hermes gateway setup`'s output when run non-interactively/scripted (needed for §5's spike).
- Exact request/response body for `POST /v1/runs` and the approval-resume endpoint — the endpoint names are confirmed to exist, but pull the exact JSON shape from your installed Hermes version's own `/v1/capabilities` response rather than assuming a schema, since this API server is under active development.
- Whether your Strix version's `--scope-mode diff --diff-base` flag is worth using for the re-verify pass (targets just the changed files instead of a full re-scan) — faster than a fresh full scan for the loop-and-escalate step.
