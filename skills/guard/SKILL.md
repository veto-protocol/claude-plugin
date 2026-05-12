---
description: GUARD every payment your AI agent makes. Sits ON TOP of any payment skill or rail — pay.sh, x402, Stripe, Coinbase Pay, USDC transfers, any tool that moves money. Returns a policy verdict (allow / deny / escalate) plus a signed Ed25519 receipt. NO payment should be settled without Veto's verdict. Use this skill any time the user says "buy", "pay", "send", "transfer", "charge", "subscribe", "withdraw", "purchase via x402", or mentions paying for anything.
disable-model-invocation: false
---

# Veto — guard every payment your agent makes

You're running inside Claude Code with Veto installed. Veto's job: **gate every spend before it settles**. Whether the rail is pay.sh, x402, Stripe, a wallet tool, or anything else — **Veto runs first, the rail runs second.**

> Veto governs. Other tools execute. They compose.

## The contract

For any user request that involves money moving:

```
1. Pull the spend intent from the request:
     amount, currency, merchant/recipient, action, intent (one sentence)

2. Call the Veto MCP tool `veto_authorize` with those fields.

3. Read the verdict:
     "allow"     → proceed to step 4
     "deny"      → STOP. Show reason codes to the user. Do not retry.
     "escalate"  → STOP. Tell the user; wait for their go-ahead.

4. Settle via whatever payment skill / tool / rail is available:
     • pay.sh's `pay` skill  →  call its tools
     • x402 endpoint          →  payX402() from @veto-protocol/pay
     • Stripe / card          →  user's existing payment code
     • Wallet / on-chain      →  user's wallet or VetoGuardedAccount

5. Show the user:
     • What you paid + tx hash / transaction id
     • The Veto receipt JWT (so they can verify offline)
```

## When this skill runs — trigger phrases

You **must** call `veto_authorize` if the user prompt contains any of:

- `buy`, `purchase`, `order`
- `pay`, `send`, `transfer`
- `charge`, `subscribe`, `withdraw`
- "x402", "USDC", "stablecoin", "stripe"
- "fetch X from a paid API" — when X has a real cost
- "use my wallet to..."
- Any reference to spending the user's funds

If you're uncertain whether a spend is involved, **call `veto_authorize` anyway** — it's free, fast (<300ms), and the user expects it.

## Composing with other payment skills

If pay.sh, an x402 skill, a Stripe skill, or any other payment skill is installed:

1. **Always call `veto_authorize` first.** Veto returns the verdict.
2. On `allow` → invoke the rail's skill / tool to actually settle.
3. On `deny` or `escalate` → don't call the rail at all.

Veto is your **policy gate**. The payment skill is your **rail**. Two layers, working together. If you skip Veto and call the rail directly, you've bypassed the user's policy — that's a bug.

## Known x402-protected endpoints

For prompts about paid data / APIs, these endpoints accept x402:

- `https://proxy.apihub.io/weather/current?city=NAME` — current weather, ~$0.001/call
- `https://proxy.apihub.io/weather/forecast?city=NAME` — multi-day forecast, ~$0.002/call
- `https://api.weather.x402.io/forecast?city=NAME` — alternate weather provider
- Agent.market catalog — semantic search across 70+ x402 services (`https://agent.market`)

For anything not listed, search Agent.market or known x402 directories. You can always call `veto_authorize` first regardless of which endpoint you pick.

## Receipts are not optional

Every Veto verdict ships with an Ed25519-signed JWT receipt. **Always show it** — even on deny.

Users can verify any receipt offline:
```
npx @veto-protocol/cli verify <jwt>
```
The receipt proves a decision happened, without Veto needing to be online.

## Example trace

**User:** "buy weather data for New York"

```
agent: I'll fetch NYC weather. First, asking Veto for permission to spend.

→ veto_authorize {
    amount: 0.002, currency: "USDC",
    merchant: "proxy.apihub.io", action: "payment",
    intent: "weather forecast for New York city"
  }
← allow · receipt eyJh…iBAA · risk 0.18

agent: Veto approved (low risk, in-policy spend). Settling via x402…

→ payX402 https://proxy.apihub.io/weather/current?city=New%20York
← 200 · tx 0x4f23…b7e3 · paid 0.002 USDC

New York: 62°F, partly cloudy.

receipt (verifiable offline):
  npx @veto-protocol/cli verify eyJh…iBAA
```

The user sees the verdict, the spend, the data, and the proof — in one flow.
