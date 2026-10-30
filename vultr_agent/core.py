"""Orchestration: natural language -> generated code -> sandboxed run -> verify.

Implements the Blast Radius Zero "CSV Analyst" use case with a lightweight
self-healing loop: if the first run fails (or times out), regenerate once with
the error fed back, then re-run. Demonstrates multi-step agentic execution with
real, verifiable output and a containment moment (the sandbox absorbs a runaway
or hostile snippet instead of crashing the host).
"""
import os
import json
from . import agent, sandbox, audit

AUDIT_PATH = os.environ.get("AUDIT_PATH", "audit_log.json")


def _columns_from_csv(csv_text: str) -> list:
    if not csv_text:
        return []
    return csv_text.splitlines()[0].split(",")


def analyze(nl_query: str, csv_text: str, api_key=None, timeout: int = 20) -> dict:
    cols = _columns_from_csv(csv_text)
    code = agent.generate_code(nl_query, cols, api_key=api_key)
    result = sandbox.run_code(code, csv_text, timeout=timeout)
    attempts = [{"code": code, **result}]

    # Self-healing: one retry with the error appended to the prompt.
    if not result["ok"]:
        feedback = (result["stderr"] or "timeout")[:400]
        code2 = agent.generate_code(
            f"{nl_query} (previous attempt failed: {feedback})", cols, api_key=api_key)
        result2 = sandbox.run_code(code2, csv_text, timeout=timeout)
        attempts.append({"code": code2, **result2})
        result = result2

    audit.append(AUDIT_PATH, {
        "query": nl_query, "columns": cols,
        "code": attempts[-1]["code"], "stdout": result["stdout"],
        "stderr": result["stderr"], "ok": result["ok"],
        "timed_out": result["timed_out"], "engine": result["engine"],
    })
    ok_chain, note = audit.verify(AUDIT_PATH)
    parsed = None
    if result["ok"]:
        for line in result["stdout"].splitlines():
            try:
                parsed = json.loads(line)
                break
            except Exception:
                continue
    return {
        "query": nl_query,
        "ok": result["ok"],
        "result": parsed,
        "raw_stdout": result["stdout"],
        "raw_stderr": result["stderr"],
        "timed_out": result["timed_out"],
        "engine": result["engine"],
        "attempts": len(attempts),
        "audit_intact": ok_chain,
        "audit_note": note,
    }


def containment_demo() -> dict:
    """Show the sandbox absorbing a hostile/runaway snippet (the containment moment)."""
    hostile = "import os\nos.system('rm -rf /')\nwhile True:\n    pass\n"
    res = sandbox.run_code(hostile, "", timeout=8)
    audit.append(AUDIT_PATH, {
        "query": "<containment-demo>", "code": hostile,
        "stdout": res["stdout"], "stderr": res["stderr"],
        "ok": res["ok"], "timed_out": res["timed_out"], "engine": res["engine"],
    })
    return {"absorbed": (not res["ok"]), "timed_out": res["timed_out"],
            "engine": res["engine"]}
