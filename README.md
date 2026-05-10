# @veto-protocol/claude-plugin

The boundary between Claude Code and money.

This plugin makes Claude Code spend-aware. Three slash commands, an MCP
server with the policy engine attached, and a `PreToolUse` hook that
intercepts payment-like tool calls before they execute.

```
                ┌─────────────────────────────┐
                │   you in Claude Code        │
                └────────────────┬────────────┘
                                 │
                "pay $5 to api.weather.x402.io"
                                 ▼
              ┌──────────────────────────────────┐
              │  /veto:authorize  (this plugin)  │
              └────────────────┬─────────────────┘
                               │
                  ┌────────────▼──────────────┐
                  │  Veto policy engine       │
                  │  • policy + risk + intent │
                  │  • signed receipt         │
                  └────────────┬──────────────┘
                               │
                       allow / deny / escalate
                               │
                               ▼
                       Claude Code proceeds
```

---

## What you get

- `/veto:authorize` — run any spend through Veto before paying
- `/veto:receipts` — list, inspect, verify signed receipts
- `/veto:policy` — show your policy, dry-run a spend without paying
- An MCP server with these tools wired automatically (`veto__authorize`,
  `veto__list_receipts`, `veto__verify_receipt`, `veto__policy_show`,
  `veto__policy_check`)
- A `PreToolUse` hook that intercepts payment-shaped tool calls (MCP
  `transfer`/`send`/`pay` tools, Bash `cast send`, `solana transfer`,
  `npx @veto-protocol/pay`, x402 `curl`s, Stripe API calls, etc.) and
  routes them through Veto

---

## Setup

```bash
# 1. Install the underlying CLI (ships the MCP server)
pip install veto-cli

# 2. Provision an agent + API key
veto agent init my-claude-agent

# 3. Install this plugin in Claude Code
/plugin marketplace add veto-protocol/claude-plugin
/plugin install veto@veto-protocol
/reload-plugins
```

You'll need three env vars accessible to Claude Code (the plugin reads
them at runtime):

```
VETO_API_KEY=vk_...
VETO_AGENT_ID=agt_...
VETO_BASE_URL=https://veto-ai.com   # default
```

`veto agent init` writes them to `~/.veto/config.json`; the MCP server +
hook both pick them up from there if not set in env.

---

## What "payment-shaped" means

The `PreToolUse` hook is heuristic. It intercepts:

| Pattern                                              | Why                          |
|------------------------------------------------------|------------------------------|
| `mcp__*__transfer`, `__send`, `__pay`, `__swap`      | Common wallet/payment MCP tools |
| `cast send …` (Foundry)                              | EVM on-chain sends           |
| `solana transfer …`, `solana pay …`                  | Solana on-chain sends        |
| `npx @veto-protocol/pay …`                           | The Veto demo path           |
| `curl …` containing `402` or `x-payment`             | x402 paid endpoints          |
| `stripe payments …` (API)                            | Stripe charges               |

For each match the hook tries to extract `amount` + `recipient` from the
tool args, calls `/api/v1/authorize/` with `decision_only: true`, and
returns:

- **allow** → tool runs, decision receipt id surfaced
- **deny** → tool blocked with the reason codes
- **escalate** → Claude Code prompts you to confirm (per Claude Code's
  `permissionDecision: "ask"`)

If the hook can't extract `amount`/`recipient` (e.g., complex Bash
pipelines), it **fails open** — passes the call through with a stderr
breadcrumb. Real enforcement should use the MCP tools directly where
args are structured.

---

## Why this matters

Without Veto, Claude Code can spend anything you give it API keys for —
no policy, no audit, no recourse. With Veto installed:

- Every spend has a verdict (allow/deny/escalate) and a signed receipt
- The receipt is verifiable offline against
  `https://veto-ai.com/.well-known/jwks.json`
- For crypto rails, your funds can sit behind `VetoGuardedAccount` —
  the chain itself refuses spends without a fresh Veto mandate
- Eight-stage engine: policy, prompt-injection, merchant-fraud
  (typosquat), crypto-safety (OFAC, drainer index, address poisoning),
  intent verification (LLM-as-judge), anomaly, behavioral baseline,
  aggregate verdict

---

## Local development

```bash
git clone https://github.com/veto-protocol/claude-plugin
cd claude-plugin
claude --plugin-dir .
# inside Claude Code:
/reload-plugins
/veto:authorize $1 to api.weather.x402.io for testing
```

To verify the hook runs:

```bash
echo '{"tool_name":"Bash","tool_input":{"command":"cast send 0xCBbb… --value 0.05"}}' \
  | hooks/pre_payment.py
```

You should see a JSON `permissionDecision` come back.

---

## Repo

- This plugin: <https://github.com/veto-protocol/claude-plugin>
- Veto CLI + MCP server: <https://github.com/veto-protocol/veto-cli>
- Policy engine + on-chain contract: <https://github.com/veto-protocol>
- Docs: <https://veto-ai.com>

MIT. Built by [Investech Global LLC](https://veto-ai.com).
