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
- `require_human_approval_above` (the escalate threshold)
- `merchant_allowlist` / `merchant_blocklist` (if non-empty)
- `per_merchant_caps` — dollar cap per individual merchant
- `categories_allowlist` / `categories_blocklist` — semantic categories (weather, search, inference, finance, …)
- `time_windows` — allowed spend hours/days
- `rate_limit_per_hour`, `rate_limit_per_day` — count-based rate caps
- `intent_keywords_required` / `intent_keywords_forbidden` — words that must (not) appear in intent text

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

Two paths, depending on context:

- **From inside a Claude Code session** — you have MCP tools that each push a
  new policy version: `veto_policy_set_caps`, `veto_policy_set_time_windows`,
  `veto_policy_set_rate_limits`, `veto_policy_categories_set`,
  `veto_policy_per_merchant_cap_set`, `veto_policy_intent_keywords_set`,
  `veto_policy_allowlist_add`. Each one fetches the active policy, merges your
  patch, and pushes a new version (the old one stays for audit).
  **Always confirm with the user before calling any of these.**
- **From the shell** — `veto policy push <yaml>` for full-file edits;
  validates, versions, and content-hashes.

Either way, policies are immutable — every change is a new version.

## Reminders

- A policy is identified by `(agent_id, version)`. The active version is the
  one new spends evaluate against.
- `policy_check` does not mutate state — safe to call as often as you want.
- Receipts include the policy `version` + `hash` so a verdict is always
  traceable to the exact rules that produced it.
