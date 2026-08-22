# Workflow

How a target goes from "paste a URL" to "merged, verified fix," and how the system gets smarter every time a human overrides it.

---

## 1. Entry point: submit a target

The operator pastes a target into the dashboard: a live URL, or a Git repository URL. Either is accepted the same way.

- **URL target.** Fang probes the live application surface: endpoints, forms, auth flows, headers.
- **Repository target.** Fang clones the repo into an isolated sandbox and runs a full code-level review: dependency CVEs, SAST patterns, business-logic flaws, secrets, and more. Fang reasons over the actual source even when it can't safely attack a live instance.

Either way, submitting a target spins up **Fang's Agents**, a set of specialist agents (SAST/SCA, injection & RCE, auth & access control, XSS, deserialization, NoSQL injection, app-runtime) that work the target in parallel, each reporting only findings they can substantiate.

## 2. Triage: live findings

The dashboard shows the scan as it happens:

- **Attack Log**: each finding as it's confirmed, with severity and CVE/CWE identifiers.
- **Vulnerability Timeline**: findings plotted over the scan's duration.
- **Agent graph**: which specialist is running, what it's found, live tool activity.
- **Research Agent**: cross-references the target's inferred stack against newly disclosed CVEs, independent of what Fang found directly.

Nothing here requires an operator decision yet, this is observation.

## 3. Deploy: connect a remediation channel

Clicking **Deploy Agent** pairs the operator's WhatsApp as a companion device (a QR scan, same as WhatsApp Web). This becomes the primary channel for approvals; a connected Slack workspace can additionally receive escalations and team-wide feedback.

Once paired, **Ouro** takes over the conversation:

1. Sends an opening summary of the scan (target, finding count, severity breakdown).
2. Requests GitHub device-flow authorization and sends the code and link.
3. On confirmation, verifies the grant and presents the findings for approval.

Every step is single-message-then-stop: Ouro never advances to the next step without an explicit reply. This is deliberate: an unattended agent should not be pushing code on its own judgment.

## 4. Approve: fix, one decision at a time

Once GitHub access is confirmed, Ouro presents the findings and waits for **APPROVE** (all) or **REJECT `<id>`** (specific findings to skip).

Any critical-severity finding gets an additional gate before anything is touched:

> 🚨 VERY CRITICAL: `<finding>`
> This blocks ALL other fixes until resolved.
> Reply APPROVE to proceed, or BLOCK to escalate without touching it.

For everything else, Ouro works one finding at a time: status message, patch applied on a branch, re-attack verification, confirmation, then waits for **OK** before moving to the next finding. Nothing is batched silently.

## 5. Fix and verify

For each approved finding:

1. Ouro applies the fix on a dedicated branch (`ouro/fix/<slug>`) and opens a pull request against the governance-approved repository.
2. Fang re-attacks the patched path to confirm the exploit no longer works, not a lint pass, an actual re-verification.
3. If the re-attack still succeeds, the fix is revised and re-tried, up to a bounded number of attempts before escalating (see Loop 2 below).

A PR that reaches "ready" has been proven closed against the same attack that found it.

## 6. Compliance report

Once every finding is resolved (fixed, escalated, or explicitly rejected), Ouro generates a compliance summary (frameworks: DPDP, SOC 2, ISO 27001) and attaches the full report to the run.

---

## Resilience: the two feedback loops

Every automated system gets things wrong sometimes: a false alarm, a fix that breaks something. Ouroboros treats a human catching one of those as data, not just an interruption.

### Loop 1: False positives (Slack)

An engineer looks at an escalated finding and disagrees. Instead of just dismissing it, they flag it as a false positive, and Ouro asks *why*, with candidate reasons reasoned from the specific finding (not a generic checklist), plus room to describe it in their own words.

The answer is recorded against that exact signature and target (package, rule ID, and the stated reason) and excluded from the fix pipeline. It is not counted as resolved; it's parked, with context, so the next scan of the same target doesn't raise it again without cause.

### Loop 2: Declined fixes (WhatsApp)

A PR gets closed without merging: it broke something, missed an edge case, or used the wrong dependency version. Ouro follows up:

> Hey, I noticed the patch for `<finding>` was declined. Quick feedback, what went wrong?
>
> [1] Broke existing functionality / tests failed
> [2] Incomplete fix / missed edge case
> [3] Used wrong library version / syntax
> [4] Please describe

The stated reason becomes an explicit correction constraint on the retry ("prior attempt broke existing tests, run the suite before opening the PR this time") rather than a blind second attempt at the same fix.

### Why this matters

Both loops write to the same place: a structured record per finding, per target, of what a human actually said and why. That record is what makes repeat scans of the same target faster and quieter over time, not a bigger model, a better memory of what this specific codebase's false alarms and failure modes actually look like.

---

## Governance

- Ouro only opens PRs against repositories an admin has explicitly allowlisted.
- Protected branches (`main`, `release`, anything marked production-critical) never receive an auto-merge; they require manual review regardless of how the fix was generated.
- Structured feedback (Loop 1 and Loop 2) is not optional to review, it's the primary channel through which the system's behavior improves. Ignoring it just means repeating the same false positives and the same broken fixes.

## Quick start

1. Start the services, see [DEPLOYMENT.md](DEPLOYMENT.md).
2. Open the dashboard, sign in.
3. Paste a target URL or repository link.
4. Watch findings arrive live; click **Deploy Agent** to pair WhatsApp.
5. Approve findings from your phone; review PRs as they land.
6. Use the Slack/WhatsApp feedback prompts whenever the system gets something wrong, that's what makes the next scan better.
