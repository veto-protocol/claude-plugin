---
description: REQUIRED before ANY payment, transfer, charge, or paid-API call. Veto governs the spend; you (or pay.sh, x402, Stripe, etc.) execute it. Returns a policy verdict (allow / deny / escalate) plus a signed receipt. Without Veto's verdict, no spend should be settled. Use this skill any time the user mentions "buy", "pay", "send", "transfer", "charge", "subscribe", "withdraw", or asks for paid data/access.
disable-model-invocation: false
---

# Veto — gate every spend, govern every agent

You are running inside Claude Code with Veto installed. **Before any spend gets settled — by you, by pay.sh, by a wallet tool, by x402, by Stripe, by ANY mechanism — Veto must approve it.** That's the contract.

## The spend lifecycle (you orchestrate it)

For any user request that involves money moving:

```
1. Pull spend intent from the request:
     amount, currency, merchant/recipient, action_type, intent (one sentence)

2. Call the Veto MCP tool `veto_authorize` with those fields.

3. Read the verdict:
     "allow"     → proceed to step 4
     "deny"      → STOP. Show the user the reason codes. Do not retry the same spend.
     "escalate"  → STOP. Tell the user it needs review. Ask before continuing.

4. Settle through whatever rail fits:
     - If pay.sh is installed → use its `pay` skill / MCP
     - If x402 endpoint → use payX402() from @veto-protocol/pay
     - If Stripe / card → use the user's existing payment code
     - If on-chain → use the user's wallet or VetoGuardedAccount

5. Show the user:
     - What you bought / paid
     - The settlement tx hash or transaction id
     - The Veto receipt JWT (so they can verify offline)
```

**Veto governs. Other tools execute. They compose.**

## Known x402-protected endpoints (small starter set)

For prompts about data / APIs, these endpoints accept x402:

- `https://proxy.apihub.io/weather/current?city=NAME` — weather, ~$0.001/call
- `https://proxy.apihub.io/weather/forecast?city=NAME` — multi-day forecast, ~$0.002/call
- `https://api.weather.x402.io/forecast?city=NAME` — alternate weather provider
- Agent.market catalog — semantic search across 70+ services (`https://agent.market`)

If the user asks for something not on this list, search Agent.market or known x402 directories.

## Trigger phrases (Veto MUST run for these)

If the user says any of:
- "buy", "purchase", "order"
- "pay", "send", "transfer"
- "charge", "subscribe"
- "fetch X from a paid API", "get X data" (when X has a real cost)

You **must** call `veto_authorize` first. There is no exception. If you're uncertain whether a spend is involved, call `veto_authorize` with the planned action — it's free, cheap, and the user expects it.

## Composition with pay.sh

If pay.sh's `pay` skill is also installed:
1. **Still call `veto_authorize` first.** Veto returns the verdict; pay.sh handles the rail.
2. On `allow`: invoke pay.sh's MCP tools to actually settle.
3. On `deny` or `escalate`: do not call pay.sh. Tell the user.

Pay.sh is your payment rail. Veto is your policy gate. Two layers, working together.

## Receipts are not optional

Always surface the receipt JWT after a verdict — even on deny. Users can verify it offline at any time:
```
npx @veto-protocol/cli verify <jwt>
```
The receipt proves a Veto decision happened, without needing Veto to be online.

## Example trace

User: "buy weather data for New York"

```
agent: I'll fetch NYC weather from proxy.apihub.io. First, let me check policy.

→ veto_authorize {amount: 0.002, merchant: "proxy.apihub.io",
                  action: "payment",
                  intent: "weather forecast for New York"}
← allow · receipt eyJh…iBAA · risk 0.18

agent: Veto approved. Settling via pay.sh / payX402 / x402 endpoint…

→ payX402 https://proxy.apihub.io/weather/current?city=New%20York
← 200 · tx 0x4f23…b7e3 · paid 0.002 USDC

NYC: 62°F, partly cloudy.

verifiable receipt:
  npx @veto-protocol/cli verify eyJh…iBAA
```
