#!/usr/bin/env python3
"""
Veto PreToolUse hook for Claude Code.

Reads the tool call JSON from stdin. If the tool call looks like a payment
(MCP transfer/send/pay/swap, or a Bash command that smells like an
on-chain transfer or paid HTTP call), routes it through Veto authorize
before letting it execute. Allows, denies, or escalates per Veto's verdict.

Fails open on parse errors — better to let an unparseable call through
than to block legitimate work. Real payment paths should use the Veto MCP
server directly, where the args are structured.

stdin shape (per Claude Code docs):
  {
    "tool_name":  "Bash" | "mcp__<server>__<tool>",
    "tool_input": { ...tool-specific args... },
    "cwd":        "/path",
    ...
  }

stdout shape (back to Claude Code):
  {
    "hookSpecificOutput": {
      "hookEventName": "PreToolUse",
      "permissionDecision": "allow" | "deny" | "ask",
      "permissionDecisionReason": "..."
    }
  }
"""
from __future__ import annotations

import json
import os
import re
import sys
import urllib.error
import urllib.request


VETO_BASE_URL = os.environ.get("VETO_BASE_URL", "https://veto-ai.com").rstrip("/")
VETO_API_KEY  = os.environ.get("VETO_API_KEY", "")
VETO_AGENT_ID = os.environ.get("VETO_AGENT_ID", "")

# Bash patterns we treat as payment-shaped. Heuristic — false positives mean
# extra prompts, which is fine; false negatives mean missed enforcement.
BASH_PAYMENT_PATTERNS = [
    r"\bcast\s+send\b",                                 # foundry on-chain send
    r"\banchor\s+(?:run|deploy)\b",                     # Solana program ops
    r"\bsolana\s+transfer\b",
    r"\bsolana\s+pay\b",
    r"\bnpx\s+@veto-protocol/pay\b",                    # our own demo
    r"\bcurl[^\n]*(?:402|x-payment)",                   # x402 paid endpoints
    r"\bstripe\s+(?:payments|charges|payment_intents)\b",
]
BASH_PAYMENT_RE = re.compile("|".join(BASH_PAYMENT_PATTERNS), re.IGNORECASE)


def respond(decision: str, reason: str = "", *, exit_code: int = 0) -> "None":
    """Emit the hook output JSON and exit."""
    out = {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": decision,
        }
    }
    if reason:
        out["hookSpecificOutput"]["permissionDecisionReason"] = reason
    print(json.dumps(out))
    sys.exit(exit_code)


def looks_like_payment(tool_name: str, tool_input: dict) -> bool:
    """Decide whether this tool call deserves a Veto check."""
    if tool_name.startswith("mcp__"):
        # Already filtered by the matcher in hooks.json. Always intercept.
        return True
    if tool_name == "Bash":
        cmd = (tool_input.get("command") or "").strip()
        if not cmd:
            return False
        return bool(BASH_PAYMENT_RE.search(cmd))
    return False


def extract_amount_and_target(tool_name: str, tool_input: dict) -> tuple[float | None, str | None, str]:
    """Best-effort extraction of (amount, merchant_or_recipient, action).

    Returns (None, None, action) when we can't parse — the caller fails open.
    """
    if tool_name.startswith("mcp__"):
        # MCP tools have structured args. Look for common keys.
        amount = (
            tool_input.get("amount")
            or tool_input.get("value")
            or tool_input.get("max_amount")
            or tool_input.get("maxAmount")
        )
        target = (
            tool_input.get("recipient")
            or tool_input.get("to")
            or tool_input.get("to_address")
            or tool_input.get("merchant")
            or tool_input.get("address")
            or tool_input.get("destination")
        )
        try:
            amount_f = float(str(amount).replace("$", "").strip()) if amount is not None else None
        except (TypeError, ValueError):
            amount_f = None
        action = "crypto_transfer" if "transfer" in tool_name else "payment"
        return amount_f, str(target) if target else None, action

    if tool_name == "Bash":
        cmd = (tool_input.get("command") or "").strip()
        # Try to pull numeric amounts ($5, 0.05, 100) and a target (0x..., base58, host).
        amt_match = re.search(r"(?<![A-Za-z0-9])\$?(\d+(?:\.\d+)?)", cmd)
        amt = float(amt_match.group(1)) if amt_match else None
        target = None
        # EVM address
        m = re.search(r"0x[a-fA-F0-9]{40}", cmd)
        if m:
            target = m.group(0)
        else:
            # Hostname after curl/wget/http
            m = re.search(r"https?://([a-zA-Z0-9.-]+)", cmd)
            if m:
                target = m.group(1)
        action = "crypto_transfer" if target and target.startswith("0x") else "payment"
        return amt, target, action

    return None, None, "payment"


def call_veto_authorize(amount: float, target: str, action: str, tool_name: str) -> dict | None:
    """Call Veto's authorize endpoint. Returns the response dict or None on error."""
    if not (VETO_API_KEY and VETO_AGENT_ID):
        return None

    payload = {
        "agent_id": VETO_AGENT_ID,
        "amount": amount,
        "currency": "USD",
        "merchant": target if not target.startswith("0x") else "",
        "to_address": target if target.startswith("0x") else "",
        "action": action,
        "decision_only": True,
        "context": {
            "source":     "claude-code-plugin",
            "tool_name":  tool_name,
        },
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        f"{VETO_BASE_URL}/api/v1/authorize/",
        data=data,
        method="POST",
        headers={
            "Content-Type":   "application/json",
            "X-Veto-API-Key": VETO_API_KEY,
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, urllib.error.HTTPError, json.JSONDecodeError, TimeoutError):
        return None


def main() -> None:
    try:
        payload = json.loads(sys.stdin.read())
    except (json.JSONDecodeError, ValueError):
        respond("allow", "veto: hook input was not valid JSON, passing through")

    tool_name = payload.get("tool_name") or ""
    tool_input = payload.get("tool_input") or {}

    if not looks_like_payment(tool_name, tool_input):
        # Bash matcher fires for every shell command — most aren't payments.
        respond("allow")

    amount, target, action = extract_amount_and_target(tool_name, tool_input)

    if amount is None or not target:
        # Can't extract enough to authorize. Fail open with a stderr breadcrumb
        # so the user knows Veto saw the call but couldn't parse it.
        sys.stderr.write(
            f"[veto] saw {tool_name}; couldn't extract amount/target — passing through\n"
        )
        respond("allow", "veto: amount/target not parseable from tool args")

    verdict = call_veto_authorize(amount, target, action, tool_name)
    if verdict is None:
        # Veto unreachable or unconfigured. Tell the user and fail open.
        if not (VETO_API_KEY and VETO_AGENT_ID):
            reason = (
                "veto: VETO_API_KEY or VETO_AGENT_ID not set — "
                "skipping authorize. Run `veto agent init` to set them."
            )
        else:
            reason = "veto: authorize endpoint unreachable, passing through"
        sys.stderr.write(f"[veto] {reason}\n")
        respond("allow", reason)

    decision = (verdict.get("decision") or verdict.get("status") or "").lower()
    receipt  = verdict.get("receipt") or ""
    reasons  = ", ".join(verdict.get("reason_codes") or []) or "no reason codes"

    if decision == "deny":
        respond(
            "deny",
            f"Veto denied: {action} {amount} to {target} — {reasons}. Receipt: {receipt[:32]}…",
        )
    if decision == "escalate":
        respond(
            "ask",
            f"Veto escalated this spend for human review: {amount} to {target} — {reasons}. "
            f"Confirm before proceeding. Receipt: {receipt[:32]}…",
        )

    # decision == "allow" or anything else conservative
    respond("allow", f"Veto approved · receipt {receipt[:32]}…" if receipt else "")


if __name__ == "__main__":
    main()
