---
description: Inspect or check the Veto policy that governs the user's agent. Use when the user asks "what's my policy", "would X be allowed", "show me the rules", or wants to dry-run a spend without actually authorizing it.
disable-model-invocation: false
---

# Veto policy

A Veto policy is a YAML document declaring the rules under which an agent is
allowed to spend: per-tx caps, daily/monthly caps, merchant allowlists/blocklists,
escalation thresholds, rail constraints. Policies are versioned and
content-hashed — the hash binds receipts to the exact policy that was active
at decision time.

## What to do

### Show the active policy

If the user asks "what's my policy" or similar:

Call `veto__policy_show` (no arguments needed for the default agent, or pass
`agent_id` if they specify one).

Render the YAML with sensible formatting. Highlight:
- `max_per_transaction`
- `daily_limit`, `monthly_limit`
- `merchant_allowlist` (if non-empty)
- `merchant_blocklist`
- `require_human_approval_above` (the escalate threshold)

### Dry-run a spend

If the user asks "would Veto allow $X to Y" or "check this spend without
paying":

Call `veto__policy_check` with:
- `amount`
- `currency`
- `merchant` or `recipient`
- `action` (`payment` / `crypto_transfer` / `subscribe`)

This runs the full engine *without* settling — same verdict shape as
`/veto:authorize` but no payment is made and no receipt is issued.

Useful for: testing policy changes, debugging false-positive denies,
auditing a planned campaign before kickoff.

### Edit policy

Editing policy is intentionally **out of scope** for this skill — policy
changes flow through `veto policy push <yaml>` from the CLI, which validates,
versions, and content-hashes them. Tell the user to run that command and
exit the skill.

## Reminders

- A policy is identified by `(agent_id, version)`. The active version is the
  one new spends evaluate against.
- `policy_check` does not mutate state — safe to call as often as you want.
- Receipts include the policy `version` + `hash` so a verdict is always
  traceable to the exact rules that produced it.
