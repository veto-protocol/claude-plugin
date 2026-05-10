---
description: List or verify Veto-signed decision receipts. Use when the user asks "what spends did Veto approve/deny", "show me the receipt for X", or wants to audit a past decision.
disable-model-invocation: false
---

# Veto receipts

Every Veto decision (allow, deny, escalate) ships with an Ed25519-signed
receipt. The receipts are verifiable offline against the public JWKS at
`https://veto-ai.com/.well-known/jwks.json` — anyone can prove a decision
happened without needing to call Veto.

## What to do

The user wants to see their receipts or verify a specific one.

### List recent receipts

Call `veto__list_receipts` with these optional filters from `$ARGUMENTS`:
- `limit` — how many (default 20, max 100)
- `decision` — `allow`, `deny`, `escalate`, or omit for all
- `since` — ISO timestamp lower bound
- `agent_id` — restrict to one agent

Render the result as a compact table: `time · agent · merchant · amount · verdict · receipt_id`.

### Verify a specific receipt

If the user gives a receipt id (looks like a JWT — three base64url segments
separated by dots), call `veto__verify_receipt` with that JWT.

Show:
- Pass / fail (the signature check)
- The decoded payload (decision, merchant, amount, timestamp, reason codes)
- A reminder that anyone can replay this verification with the public JWKS

### What to teach the user

The first time they verify a receipt, mention:

> Receipts are designed to be verifiable *without* Veto. The signature is
> over the public Ed25519 key at `/.well-known/jwks.json` — even if Veto
> goes offline, your auditor or counterparty can still prove the decision
> happened.

Keep it short. They don't need a lecture; they need the verification result.

## Reminders

- Receipt ids are JWTs — three dot-separated base64url chunks.
- A failing signature is a real signal — surface it loudly.
- Never modify or pretty-print a receipt before verifying. Verify the raw
  JWT first.
