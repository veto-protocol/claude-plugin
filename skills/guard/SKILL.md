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

## When Veto denies — the moment to teach

A deny isn't a wall — it's the user's first guided tour of their own policy. Most users have never opened it. They've just been told an agent is going to spend their money, and now Veto blocked something. They're paying attention. Don't waste it.

**Do this in order, every time:**

1. **Show the verdict + the receipt URL** (`https://veto-ai.com/r/<uuid>`). One line is fine.
2. **Translate the `reason_codes`** into plain English. The user doesn't know what `OVER_PER_MERCHANT_CAP` means — they know "this site was capped at $0.10 and we tried to spend $0.30."
3. **Call `veto_policy_show`** so you can describe what the policy currently allows.
4. **Offer 1–3 concrete next moves**, each tied to the exact MCP tool you'd call. Be specific — show the field, the old value, the new value. Examples:
   - "Add `api.exa.x402.io` to your merchant allowlist → `veto_policy_allowlist_add`"
   - "Raise per-tx cap from `$0.10` to `$1.00` → `veto_policy_set_caps`"
   - "Drop the `finance`-category restriction → `veto_policy_categories_set`"
   - "Loosen the 9–5 time window → `veto_policy_set_time_windows`"
   - "Cap this merchant at $0.50 instead → `veto_policy_per_merchant_cap_set`"
5. **Wait for explicit confirmation** before any policy mutation. After the change, retry `veto_authorize` so the user sees their new policy in action.

This sequence is non-negotiable. Skipping the teach step means the user just sees "denied" and walks away — and the rich, customizable surface Veto offers is invisible to them.

### Reason codes → English (cheat-sheet)

- `MERCHANT_NOT_ALLOWLISTED` → "This merchant isn't on your allowlist. Add it or pick another." (`veto_policy_allowlist_add`)
- `OVER_TX_LIMIT` → "Amount > your per-tx cap." (`veto_policy_set_caps`)
- `OVER_DAILY_LIMIT` / `OVER_MONTHLY_LIMIT` → "You've already spent your daily / monthly budget." (`veto_policy_set_caps`)
- `OVER_PER_MERCHANT_CAP` → "Amount > the cap you set just for this merchant." (`veto_policy_per_merchant_cap_set`)
- `TIME_WINDOW_VIOLATION` → "Outside your allowed time windows." (`veto_policy_set_time_windows`)
- `RATE_LIMITED_HOURLY` / `RATE_LIMITED_DAILY` → "Too many transactions in the window." (`veto_policy_set_rate_limits`)
- `CATEGORY_BLOCKED` → "Merchant's category is on your blocklist." (`veto_policy_categories_set`)
- `CATEGORY_NOT_ALLOWED` → "Merchant's category isn't on your allowlist." (`veto_policy_categories_set`)
- `INTENT_KEYWORD_FORBIDDEN` → "Intent text mentioned a forbidden word." (`veto_policy_intent_keywords_set`)
- `INTENT_KEYWORD_MISSING` → "Intent didn't include any required keywords." (`veto_policy_intent_keywords_set`)
- `KNOWN_FRAUD_MERCHANT` / `TYPOSQUATTING` → "This looks like phishing. Don't override unless you really mean it."
- `KILL_SWITCH` → "Client kill switch is on; nothing will pass until it's flipped off."

Never silently mutate the user's policy. They own it.

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
