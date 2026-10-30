"""LLM client for code generation.

Uses Vultr Serverless Inference (OpenAI-compatible) when VULTR_API_KEY is set.
Falls back to a deterministic offline mock so the whole pipeline (and eval.py)
runs with no network and no key — honouring the "claims must be reproducible"
rule.
"""
import os
import json
import urllib.request

VULTR_BASE = "https://api.vultrinference.com/v1"
DEFAULT_MODEL = "openai/gpt-oss-120b"

# --- Offline mock: common CSV-analyst intents, keyed by normalized query.
#     Pure stdlib (csv + json) so eval runs with zero third-party deps. ---
_MOCKS = {
    "total sales": (
        "import csv, json\n"
        "rows = list(csv.DictReader(open('/data/in.csv')))\n"
        "total = sum(float(r.get('sales', 0) or 0) for r in rows)\n"
        "print(json.dumps({'metric': 'total_sales', 'value': total}))\n"
    ),
    "average price": (
        "import csv, json\n"
        "rows = list(csv.DictReader(open('/data/in.csv')))\n"
        "prices = [float(r.get('price', 0) or 0) for r in rows]\n"
        "avg = round(sum(prices) / len(prices), 2) if prices else 0\n"
        "print(json.dumps({'metric': 'avg_price', 'value': avg}))\n"
    ),
    "count rows": (
        "import csv, json\n"
        "rows = list(csv.DictReader(open('/data/in.csv')))\n"
        "print(json.dumps({'metric': 'row_count', 'value': len(rows)}))\n"
    ),
}


def _norm(q: str) -> str:
    return " ".join(q.lower().split())


def _call_vultr(messages, model=DEFAULT_MODEL, api_key=None, max_tokens=900):
    key = api_key or os.environ.get("VULTR_API_KEY")
    if not key:
        return None
    body = json.dumps({
        "model": model,
        "messages": messages,
        "max_tokens": max_tokens,
    }).encode()
    req = urllib.request.Request(
        VULTR_BASE + "/chat/completions",
        data=body,
        headers={
            "Authorization": "Bearer " + key,
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            data = json.loads(r.read().decode())
        return data["choices"][0]["message"]["content"]
    except Exception:
        return None


def _extract_code(text: str) -> str:
    if "```" in text:
        block = text.split("```")[1]
        return block.replace("python", "", 1).strip() if block.startswith("python") else block.strip()
    return text.strip()


def _template(columns, nl_query):
    cols = ", ".join(columns) if columns else "(no columns detected)"
    return (
        "import csv, json\n"
        "rows = list(csv.DictReader(open('/data/in.csv')))\n"
        "summary = {}\n"
        "if rows:\n"
        "    for c in rows[0].keys():\n"
        "        vals = [float(r[c]) for r in rows if r.get(c) not in (None, '', 'NaN')]\n"
        "        summary[c] = round(sum(vals) / len(vals), 2) if vals else None\n"
        "print(json.dumps({'metric': 'auto_summary', 'columns': summary, 'rows': len(rows)}))\n"
    )


def generate_code(nl_query: str, columns, api_key=None) -> str:
    """Return python source. `df` is the uploaded dataset; print a JSON result."""
    key = api_key or os.environ.get("VULTR_API_KEY")
    mock = _MOCKS.get(_norm(nl_query))
    if mock and not key:
        return mock
    if key:
        sys_msg = (
            "You are a data-analyst code generator. The user uploaded a CSV "
            "available at /data/in.csv (already loaded as `df` by pandas). "
            "Write Python that computes the user's request and prints a single "
            "JSON line via print(json.dumps(...)). No plotting libraries unless "
            "asked; never access the network or the filesystem outside /data. "
            "Return only the code."
        )
        out = _call_vultr([
            {"role": "system", "content": sys_msg},
            {"role": "user", "content": f"Columns: {columns}\nRequest: {nl_query}"},
        ], api_key=key)
        if out:
            return _extract_code(out)
    return _template(columns, nl_query)
