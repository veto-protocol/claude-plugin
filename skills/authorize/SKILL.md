---
description: Run a spend through Veto's policy + risk engine before paying. Use this any time the user asks Claude Code to pay something, send funds, charge a card, or hit a paid API. Returns allow/deny/escalate with signed receipt.
disable-model-invocation: false
---

# Veto authorize

The user is about to spend money — directly, or through an agent action that
moves funds. Run it through Veto first.

## What to do

1. **Pull the spend intent out of the user's request.** You need:
   - `amount` — number, in the currency unit (e.g., 5.00 for $5)
   - `currency` — `USD`, `USDC`, `ETH`, `SOL`, etc.
   - `merchant` or `recipient` — domain (`api.openai.com`) for SaaS/API,
     0x-address for EVM, base58 for Solana
   - `action` — `payment` for SaaS/API, `crypto_transfer` for on-chain,
     `subscribe` for recurring
   - `intent` (one sentence) — what the spend is *for* (e.g., "buying weather
     forecast data for the user's trip-planning agent")

2. **Call the Veto MCP tool** `veto__authorize` with those fields.

3. **Read the verdict carefully:**
   - `allow` → tell the user the spend was approved, show the receipt jwt id,
     then proceed with the actual settle/payment.
   - `deny` → **do not pay.** Show the user the `reason_codes` from the
     verdict and the merchant/amount that was rejected. Suggest they fix the
     policy or merchant if the deny was a false positive.
   - `escalate` → the spend needs human review. Tell the user explicitly,
     show the reason codes, and **wait for their confirmation** before doing
     anything else.

4. **Always show the user the receipt id** (`receipt` field) — that's their
   audit trail. They can verify it offline at any time with
   `pip install veto-cli && veto verify receipt <id>`.

## Useful arguments

`$ARGUMENTS` will contain whatever the user said after the slash command.
Parse it for amount + merchant. If anything is missing, ask the user before
calling the tool — don't guess on amounts.

## Examples

User: `/veto:authorize $5 to api.weather.x402.io for the agent's trip plan`

Pull: amount=5, currency=USD, merchant=api.weather.x402.io,
action=payment, intent="weather data for trip planning agent". Call the
MCP tool. Show the verdict.

User: `/veto:authorize 0.05 ETH to 0xCBbb…d92c5 for the demo wallet`

Pull: amount=0.05, currency=ETH, recipient=0xCBbb…d92c5,
action=crypto_transfer, intent="topping up the demo wallet". Call the
MCP tool. Show the verdict.

## Reminders

- Never pay directly without an authorize call first.
- A `deny` is *final* — never retry the same spend after a deny.
- If `escalate`, the user has to ack before you proceed.
- Veto returns a signed Ed25519 receipt for every decision (allow, deny,
  escalate). Show the receipt id; it's not optional.
