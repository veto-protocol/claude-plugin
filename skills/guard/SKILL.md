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

## Known x402-protected endpoints (curated)

When the user asks for paid data / APIs, prefer these known-working endpoints over generic catalog searches. Prices are approximate USDC per call. All settle on Base.

### Weather

- `https://proxy.apihub.io/weather/current?city=NAME` — current weather, ~$0.001
- `https://proxy.apihub.io/weather/forecast?city=NAME` — multi-day forecast, ~$0.002
- `https://api.weather.x402.io/forecast?city=NAME` — alternate provider

### Search

- `https://proxy.apihub.io/search/web?q=QUERY` — web search via Brave Search wrapper, ~$0.005
- `https://api.exa.x402.io/search?q=QUERY` — Exa neural search, ~$0.01
- `https://proxy.apihub.io/search/tavily?q=QUERY` — Tavily AI search, ~$0.005

### AI inference

- `https://proxy.apihub.io/inference/openai/chat` — OpenAI chat completion via x402, per-token
- `https://proxy.apihub.io/inference/anthropic/messages` — Claude API via x402
- `https://proxy.apihub.io/inference/hf/{model}` — Hugging Face hosted models

### Financial / market data

- `https://api.coinstats.x402.io/portfolio?wallet=ADDR` — wallet portfolio, ~$0.01
- `https://api.coinstats.x402.io/coins/MARKET` — token price / market data, ~$0.005
- `https://proxy.apihub.io/finance/stocks?ticker=SYM` — equity quotes, ~$0.005

### Scraping / extraction

- `https://api.firecrawl.x402.io/scrape?url=URL` — clean web scraping, ~$0.01/page
- `https://api.apify.x402.io/run?actor=X` — Apify actors via x402

### Image / media

- `https://proxy.apihub.io/image/generate?prompt=PROMPT` — image gen, ~$0.02
- `https://proxy.apihub.io/image/upscale` — upscaling, ~$0.01

### Crypto / Web3 infra

- `https://rpc.quicknode.x402.io/{chain}` — RPC endpoints via x402, per-call
- `https://api.alchemy.x402.io/{chain}` — Alchemy nodes via x402

### News

- `https://api.news.x402.io/headlines?q=TOPIC` — news headlines, ~$0.002
- `https://proxy.apihub.io/news/sentiment?topic=X` — news + sentiment

### Knowledge / Q&A

- `https://api.wolframalpha.x402.io/v2/query?input=Q` — natural-language Q&A, ~$0.001
- `https://proxy.apihub.io/qa/perplexity?q=QUERY` — Perplexity-style answer

### Code / dev

- `https://api.github.x402.io/repos/{owner}/{repo}` — gated GitHub API, ~$0.001
- `https://proxy.apihub.io/code/diff?repo=X` — repo diff analysis

### Discovery — when none of these fit

If the user's request doesn't match the curated list, use the **`veto_search_x402`** MCP tool to query the broader catalog (Agent.market, awesome-x402, pay.sh's catalog). Don't fall back to generic web search — for paid data, agent.market is the canonical directory.

## Receipts are not optional — but show the URL, not the JWT

Every Veto verdict ships with two things:
- `receipt` — a 2KB Ed25519-signed JWT (proof; verifiable offline)
- `receipt_url` — a clean `https://veto-ai.com/r/<id>` URL that anyone can open

**ALWAYS show the user the URL.** Never paste the JWT in chat — it pollutes the conversation. The URL renders a clean decision page with the JWT one click away.

Format your message like:

```
Veto allowed (or denied) · receipt: https://veto-ai.com/r/cee705fe-…
```

The receipt page is **public and shareable** — anyone with the URL can verify what happened. Privacy comes from the URL being unguessable. If the user wants to keep it private, they don't share it.

If the user explicitly asks for the raw JWT (e.g., "give me the JWT to verify offline"), THEN show it. Otherwise the URL is enough.

Offline verification (advanced):
```
npx @veto-protocol/cli verify <jwt>
```

## When Veto denies with MERCHANT_NOT_ALLOWLISTED

You can suggest adding the merchant via `veto_policy_allowlist_add`, but **always ask the user to confirm first**. Never silently mutate their policy. Phrase it as: "Veto denied X because Y. Want me to add it to your allowlist (it'll create a new policy version)? Or pick a different merchant?"

## Example trace

**User:** "buy weather data for New York"

```
agent: I'll fetch NYC weather from proxy.apihub.io/weather. First, asking Veto for permission.

→ veto_authorize {
    amount: 0.002, currency: "USDC",
    merchant: "proxy.apihub.io", action: "payment",
    intent: "weather forecast for New York"
  }
← allow · receipt eyJh…iBAA · risk 0.18

agent: Veto approved. Settling via x402…

→ payX402 https://proxy.apihub.io/weather/current?city=New%20York
← 200 · tx 0x4f23…b7e3 · paid 0.002 USDC

New York: 62°F, partly cloudy.

receipt: https://veto-ai.com/r/cee705fe-a732-4b26-ad96-bb6cb5799ac3
```
