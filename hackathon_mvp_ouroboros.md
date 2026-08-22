# Ouroboros — Hackathon MVP Plan & Implementation Guide
### Public frontend (strix.ai-style) + Fang (rebranded Strix) + Ouro (rebranded Hermes) + Honcho memory + Hermes Gateway self-chat WhatsApp bridge + connected Slack escalation + SOC2 / ISO27001 / DPDP compliance moat

**Naming:**
- The rebranded, standalone Strix red-team tool is called **Fang**.
- The rebranded Hermes agent/orchestration core is **Ouro**. "Ouroboros" is the product; Ouro is the agent — and Ouro is also the name that shows up in the user's own WhatsApp self-chat thread.

*Assumes a ~30–36 hour window.*

---

## 1. Demo Narrative

A judge opens the Ouroboros site — one field, "Enter a URL." Fang scans in the backend; the frontend shows a live vulnerability report and nothing else.

The judge clicks **Fix All**. Instead of typing a business-bot's number, they see a QR code and a phone-number field. They type their number, scan the QR with their own phone (Settings → Linked Devices), and a moment later their own "Message yourself" chat in WhatsApp lights up with a message from **Ouro** — on their own account, in a thread they already had. They're also offered an optional "Connect Slack" button; if they click it, an OAuth install adds Ouro to a channel of their choice.

From there: Ouro asks for GitHub access via a link, a very-critical finding blocks and pings them in that same self-chat, they tap Approve, Blue fixes it, Fang re-attacks to verify, PR goes up. To prove the governance story isn't just "message the user and hope," the demo deliberately walks one finding through a fix that keeps failing verification. After the third attempt, the judge watches Ouro give up on WhatsApp and instead post the full finding and every attempted fix into the connected Slack channel — a live, visible handoff from "agent talking to you" to "agent escalating to a human team," which is a stronger proof point than anything staying in one channel the whole time.

---

## 2. Surfaces

| Surface | Purpose | Who sees it |
|---|---|---|
| **Public frontend** | URL in, vulnerability report out. Read-only. Styled like strix.ai. | Anyone, no login |
| **WhatsApp self-chat (Ouro)** | Everything after "Fix All": GitHub access, approvals, status, final report — inside the requester's own "Message yourself" thread | The person who clicked Fix All, on their own phone |
| **Slack (connected by the requester, optional)** | The escalation channel specifically — where a fix that can't close after 3 loops gets handed off, demoed live | Whichever Slack channel the requester picks during connect |
| **GitHub** | Repo access target and PR destination | The requester's repo |

The frontend never holds credentials. WhatsApp pairing and Slack OAuth both happen inside the Hermes Gateway step triggered by "Fix All," and everything sensitive lives in Honcho, not the browser.

---

## 3. Agents & Personas

**Agents — unchanged:**

| Agent | Role |
|---|---|
| **Research** | Autonomous, continuous CVE/CWE monitoring — runs independently of the scan/fix cycle |
| **Fang** | Standalone rebranded Strix — full scans and narrow re-attack-only verification passes |
| **Governance** | Triages findings against policy, routes by severity, owns the approval gate (WhatsApp self-chat) |
| **Blue** | Drafts and applies fixes in an isolated branch — never touches prod |
| **Compliance** | DPDP + SOC 2 + ISO 27001 mapping, dual technical/layman report |

**Ouro** is the renamed Hermes fork, running Hermes's own gateway process per session, bridged to WhatsApp (Baileys/self-chat) and, optionally, Slack.

| Persona (internal to Ouro) | Reviews inside Ouro | Distributes to |
|---|---|---|
| **SOC Analyst** | General triage queue (critical/high/medium/low) | Requester's WhatsApp self-chat |
| **Red Teamer** | Fang's findings — validates they're real, not noise | Internal only — no requester-facing role in this demo |
| **Blue Teamer** | The fix stage, and the 3-loop escalation specifically | WhatsApp self-chat for normal fix updates; **connected Slack channel** for the escalation case (falls back to WhatsApp if no Slack connected) |
| **Cybersecurity Compliance Analyst** | Compliance report generation | Requester's WhatsApp self-chat (report delivery) |
| **CISO** | Very-critical escalations, the compliance report | Requester's WhatsApp self-chat (immediate block/approve) |

---

## 4. Full Operational Flow

*(see companion diagram: `ouroboros_full_flow.mermaid`)*

1. **Research runs continuously**, independent of everything else.
2. **User lands on the public frontend**, enters a target URL, hits scan.
3. **Fang scans** — a full pass, findings written to Honcho.
4. **Cross-reference** against Research's latest knowledge.
5. **Frontend renders the vulnerability report** — findings, severity, CVE/CWE references, a **Fix All** button.
6. **Fix All → Hermes Gateway connect.** The user enters their WhatsApp number and scans a QR code (rendered on the page from `hermes whatsapp`'s pairing step) with their own phone to link it as a companion device. They're also offered an optional "Connect Slack" button (standard Slack OAuth install). See Section 5 for the full mechanics.
7. **Ouro opens the conversation inside the user's own "Message yourself" thread** — no separate contact to add, no opt-in message to send first, since this isn't the Business Platform. First message confirms the session and asks for GitHub access via a link.
8. **Governance triages** every finding against policy:
   - **Very Critical** → immediate message in the self-chat thread. Default state is blocked — nothing proceeds without an explicit reply.
   - **Critical / High / Medium / Low** → queued into the same thread as a batched approval request.
9. **On approval**, Blue drafts and applies a fix in an isolated branch.
10. **Fang re-attacks** — only the specific exploit path from the original finding.
11. **Loop**: if not closed, Blue tries again — up to 3 total attempts.
12. **Escalation, now the demoable moment**: if still not closed after 3 loops, Ouro packages the full finding + every attempted fix. If the requester connected Slack, that package posts to the connected Slack channel — live, in front of the judge. If they didn't connect Slack, it falls back to the WhatsApp self-chat thread with the same "needs manual follow-up" framing. No infinite retry either way.
13. **On verified closure**, push a PR to GitHub. Ouro sends a WhatsApp status update; the frontend report flips that finding to "fixed."
14. **Compliance Agent runs**: DPDP + SOC 2 + ISO 27001 mapped report, technical and plain-language, delivered as a document in the WhatsApp self-chat thread, mirrored on the frontend report page.
15. **Self-improvement**, same "human reviews before rules silently change" principle as before.

---

## 5. Hermes Gateway — WhatsApp connection layer (details)

This has the most moving pieces of anything in the plan, so it gets full treatment.

### 5.1 What this actually is, and the trade-off to know up front

Hermes ships its own **gateway** process — a background service that connects to messaging platforms (Telegram, Discord, Slack, WhatsApp, Signal, and others) and routes conversations to the agent. For WhatsApp specifically, Hermes uses a built-in bridge (built on Baileys) that emulates a WhatsApp Web session rather than talking to Meta's official Business Cloud API. That means: no Meta developer account, no Business verification, no template pre-approval, no per-message cost, and pairing takes seconds instead of days.

The trade-off, worth being upfront about since it's the requester's *personal* number this time, not a disposable business one: this bridge is an unofficial, reverse-engineered protocol, not something Meta sanctions for automated use. Two consequences to flag on stage rather than gloss over:
- Heavy automated messaging on a personal account carries some risk of Meta rate-limiting or flagging that number — low risk at hackathon-demo message volumes, but worth saying out loud rather than presenting as risk-free.
- The user is linking their real, daily-use WhatsApp account as a companion device to Ouro's backend, not just receiving messages from a bot number. That's a bigger trust ask than a business number texting them, and it's worth the frontend copy saying so plainly ("this links your WhatsApp as a linked device — like WhatsApp Web — you can unlink it anytime from Settings → Linked Devices") rather than burying it.

If a future, production version needs a compliant business number, Hermes also supports the official Meta Cloud API adapter as a separate, distinct integration — but that's out of scope here; this plan commits to the personal-account bridge for the hackathon.

### 5.2 Pairing flow — what the user actually does

1. User clicks **Fix All**, enters their WhatsApp number (this auto-populates the session's allowlist so only that number's messages are accepted).
2. The frontend requests a fresh gateway session from the backend (Section 5.4) and renders the QR code that the pairing step produces — same QR you'd normally see in a terminal, just drawn on the web page instead.
3. User opens WhatsApp on their own phone → Settings → Linked Devices → Link a Device → scans it. This links their account as a companion device to that session's gateway process.
4. **Self-chat mode**: the session is configured so the allowed user and the home channel both default to the paired number itself — no separate contact to add, no first message required to "opt in." The user just opens the chat they already have with themselves, and that's the live thread with Ouro.
5. Optional, same step: **Connect Slack** — a standard "Add to Slack" OAuth install, so the bot gets added to a workspace and channel the user picks. This is independent of the WhatsApp pairing and can be skipped entirely (escalation then just stays on WhatsApp).

No opt-in message, no 24-hour messaging window, no template approval — those are Meta Business Platform rules that don't apply to the personal-account bridge.

### 5.3 Session lifecycle

- Once paired, auth credentials persist, so the link survives restarts without a fresh scan — until the user manually unlinks the device, resets their phone, or a WhatsApp update invalidates the session.
- When that happens, the gateway surfaces a connection error and needs a fresh QR to re-pair — worth having a visible "reconnect" affordance on the frontend so a demo hiccup is a quick re-scan, not a dead end.
- Transient disconnects (a network blip, the phone briefly offline) are handled automatically with reconnection logic — no fresh QR needed for those.
- Inbound message bursts from the same chat get batched with a short quiet period before Ouro responds, so rapid multi-line pastes don't trigger several disjointed replies — this is default gateway behavior, nothing Ouro needs to build.

### 5.4 Multi-tenancy: one gateway session per user, not one shared bot

This is the piece that adds real backend complexity compared to a shared business number, and it's worth budgeting for honestly. Pairing links one specific WhatsApp account to one specific gateway process — there's no "one bot, many users" shortcut the way a Business API bot can message any number. Every requester who chooses WhatsApp needs their own isolated gateway session.

Practical pattern for the hackathon:
- Each "Fix All → WhatsApp" click spins up a lightweight, isolated gateway process (containerized), with its own session config directory and its own auth-key storage — so one user's pairing never touches another's.
- That session's ID is the same ID used everywhere else (Honcho, Governance, Compliance) to know which paired thread a given finding belongs to.
- Idle sessions should hibernate or tear down after the report is delivered, both for resource cost and because there's no reason to keep a companion-device link open once the run is finished — surface an explicit "disconnect" action rather than leaving it linked indefinitely.
- Store the per-session auth/key material encrypted in Honcho (or an adjacent secrets store), same tier of sensitivity as the GitHub token in Section 5.5.

This orchestration layer — spinning up, tracking, and tearing down per-user gateway sessions — is real build surface, not a small add-on. Budget real hours for it (see Section 9); it's easy to underestimate as "just add a QR code."

### 5.5 GitHub access — still a link, not a pasted token

Ouro's first substantive message in the self-chat thread sends a GitHub App install link (scoped to the specific repo, not org-wide), the user taps it, GitHub's own consent screen handles authorization, and the backend receives an installation token via callback — never a raw PAT sitting in the chat transcript. If the App-install flow doesn't fit the time budget, the fallback is a scoped, short-expiry PAT pasted directly, called out on stage as a known shortcut and rotated immediately after the demo.

### 5.6 Slack — connected for escalation, not for everything

Slack comes back into the core plan, with a specific job:
- Added as a second, independent connection in the same Fix All step (Section 5.2, step 5) — standard OAuth "Add to Slack," so the bot lands in a channel the requester actually picked, not a pre-shared demo workspace.
- Wired specifically to the 3-loop escalation branch (Section 4, step 12). Normal approvals, status, and the compliance report all stay on WhatsApp — Slack's only job is the moment Ouro needs to hand a stuck fix to a human.
- Scope is deliberately narrow — one channel, one clear reason it lit up — rather than mirroring every persona's output to its own channel. Narrower scope reads as a cleaner, more legible demo moment.
- If the requester skips connecting Slack, escalation just falls back to a WhatsApp message with the same content — the feature degrades gracefully rather than blocking the flow.

### 5.7 Report delivery

The final compliance report goes out as a document attachment in the self-chat thread, mirrored on the frontend's report page so the demo doesn't depend entirely on a phone screen for the payoff moment.

---

## 6. Compliance Mapping — DPDP + SOC 2 + ISO 27001

DPDP is the verified/deep tier; SOC 2 and ISO 27001 are a lighter control-mapping tier.

### 6.1 DPDP Act mapping (verified)

| Finding Pattern | DPDP Section | Obligation | Max Penalty |
|---|---|---|---|
| Exposed PII / weak access control / unencrypted personal data | §8(5) | Reasonable security safeguards | ₹250 crore |
| Any finding indicating an actual/simulated data breach | §8(6) | Notify Data Protection Board (72 hrs) + affected Data Principals ("without delay") | ₹200 crore |
| Finding on a system processing children's data | §9 | Special provisions for children's data | ₹200 crore |
| Finding on a system meeting Significant Data Fiduciary criteria | §10 | Additional SDF obligations (DPO, audits, impact assessments) | ₹150 crore |

DPDP Rules were notified Nov 13, 2025; Phase 1 (Board) is live, Phase 2 (consent manager registration) lands Nov 2026, Phase 3 (full substantive obligations incl. breach notification, SDF) takes effect May 2027. CERT-In's separate 6-hour cyber-incident reporting mandate is distinct from DPDP's breach notification — worth a one-line mention.

### 6.2 SOC 2 and ISO 27001 mapping (lighter tier — control ID + one-line obligation, no penalty column)

| Finding Pattern | SOC 2 Trust Service Criteria | ISO 27001 Annex A Control (2022) |
|---|---|---|
| Exposed PII / weak access control | Security (CC6 — Logical Access Controls) | A.5.15 Access control / A.8.3 Information access restriction |
| Unencrypted data at rest or in transit | Security (CC6.1) / Confidentiality | A.8.24 Use of cryptography |
| Missing input validation / injection-class findings | Security (CC7.1 — System Operations) | A.8.25 Secure development life cycle |
| No vulnerability/patch management evidence | Security (CC7.1) | A.8.8 Management of technical vulnerabilities |
| No incident detection/response path | Security (CC7.2–CC7.4) | A.5.24–A.5.26 Incident management |

Not a verified legal artifact the way the DPDP table is — check current SOC 2 TSC and ISO/IEC 27001:2022 Annex A numbering before using it beyond the demo.

---

## 7. Setup — Fast Path

1. **Hermes fork → Ouro:** clone `hermes-agent`, rebrand UI/CLI strings and logo. Its own gateway feature is what powers Section 5 — no separate messaging integration to build from scratch, just configure and wrap it.
2. **Public frontend:** minimal single-page app — URL input, scan status, read-only findings list, "Fix All" button.
3. **Honcho, self-hosted (Docker):** unchanged — add a namespace for per-session gateway auth/key material (Section 5.4) alongside the existing scan/agent state.
4. **Model backend:** unchanged.
5. **Fang (rebranded Strix, standalone):** unchanged — `pipx install strix-agent`, thin `fang` wrapper.
6. **Wire Fang into Ouro:** unchanged — two invocation modes.
7. **Target app:** unchanged — OWASP Juice Shop or similar, 2–3 seeded findings.
8. **Hermes Gateway orchestration:** the core-infra piece that needs the most early attention — build the "spin up an isolated gateway session, render its WhatsApp pairing QR on the frontend, tear it down after the run" layer described in Section 5.4. Test pairing end-to-end with a real phone early; QR-based pairing is the kind of thing that looks trivial and isn't, until you've done it once.
9. **Slack app registration:** register a standard Slack OAuth app ("Add to Slack") scoped to posting into one channel, for the escalation connection in Section 5.6.
10. **GitHub App:** register a GitHub App scoped to repo contents + pull requests for the install-link flow in Section 5.5.

---

## 8. Build Priority: Core vs. Stretch

**Core — protect these above everything else:**
- Public frontend: URL in → vulnerability report out
- Fang scanning the seeded app for real, producing a real finding
- Per-session Hermes Gateway spin-up + QR pairing working end-to-end on a real phone
- WhatsApp self-chat conversation with Ouro — the pairing-to-first-message moment is the new core proof point, don't let it be the thing tested for the first time on demo day
- GitHub access via the install link (or the scoped-token fallback from Section 5.5)
- At least one real fix → re-attack → confirmed-closed cycle, approved via the WhatsApp self-chat
- Severity routing: very-critical-blocks vs. everything-else-queues
- PR pushed after a verified fix
- **The escalation demo**: one finding deliberately taken through 3 failed fix attempts, shown escalating to a connected Slack channel live — a named core beat, essential to the demo
- The DPDP-mapped compliance report, delivered via WhatsApp
- The single-installer setup working on a clean machine

**Stretch — cut first if time runs short:**
- The full GitHub App OAuth flow — fall back to scoped-token-paste and say so on stage
- SOC 2 / ISO 27001 mapping table — DPDP alone is still a complete, credible compliance story
- Session hibernation/teardown polish (Section 5.4) — for the demo, a session that stays alive through the show is fine; automatic cleanup matters for a real product, not for one run
- All 5 personas visibly distinct in behavior, rather than 2–3 represented and the rest described
- Research-cross-reference meaningfully changing Fang's behavior
- Self-improvement shown live — narrate the architecture, or show a pre-run before/after diff
- Meta's official Business Cloud API adapter — out of scope entirely; the personal-account bridge is the intended design

**A note on scope, said plainly:** the per-session gateway orchestration in Section 5.4 is real infrastructure work, more than "add a QR code to the page" suggests at first glance — treat it with the same seriousness as the fix/verify loop in the hour plan below, not as a frontend nice-to-have.

---

## 9. Build Plan (hour blocks, ~30–36h window)

**Hours 0–4 — Setup (parallel tracks)**
Fork + rebrand Hermes agent → Ouro; self-host Honcho; fork + rebrand strix.ai install Fang (fast-path wrapper); scaffold the minimal frontend; register the Slack OAuth app and the GitHub App. In parallel, get one manual `hermes whatsapp` pairing working on a real phone outside the product flow — confirm the mechanism itself before building UI around it.

**Hours 4–10 — Fang + Research + cross-reference**
Wire Fang's two invocation modes into Ouro. Research agent pulling CVE/CWE data into Honcho. Checkpoint: a real Fang finding exists in Honcho and renders on the frontend report page.

**Hours 10–17 — Hermes Gateway orchestration + Governance**
Build the per-session spin-up/QR-render/pairing flow end to end (Section 5.4) — this has more moving parts than it looks like at a glance, budget accordingly. Severity triage logic. Approval requests landing in the self-chat thread with at least very-critical-vs-rest branching. Checkpoint: clicking Fix All on the frontend, scanning the QR with a real phone, and getting a real first message from Ouro in your own "Message yourself" thread.

**Hours 17–23 — GitHub access + Blue + the verify loop**
GitHub App install flow triggered from the self-chat thread (or the scoped-token fallback). Fix drafting/application, the re-attack call, the loop-and-escalate logic — including the Slack escalation branch and the Slack OAuth connect step. Checkpoint: one real finding goes fix → re-attack → confirmed closed, approved via WhatsApp; a second, seeded-to-fail finding demonstrates the Slack escalation.

**Hours 23–27 — Compliance + PR + report delivery**
DPDP mapping, GitHub PR push, WhatsApp document delivery of the report, frontend mirror. SOC 2/ISO27001 tables only if ahead of schedule.

**Hours 27–31 — Integration + reliability pass**
Run the full pipeline start to finish — frontend scan, QR pairing, approval, fix, escalation, report — repeatedly, on a real phone, until it's boring. Fall back to pre-seeded data anywhere live calls proved flaky, narrated honestly as "cached for demo reliability."

**Hours 31–34 — Demo polish + rehearsal**
Script the pitch around Section 1. Rehearse two moments specifically: the QR-scan-to-first-message beat, and the "watch it give up on WhatsApp and escalate to Slack" beat — those are the two things a judge hasn't seen a hundred other hackathon projects do. Have a recorded backup run in case of Wi-Fi/pairing failures on stage.

**Remaining buffer**
Reserved, not scheduled.
