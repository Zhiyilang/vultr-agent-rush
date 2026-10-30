"""Offline, zero-dependency verification of the Vultr Agent Rush pipeline.

Runs in mock mode (no VULTR_API_KEY needed): proves the full path
  NL request -> code generation -> sandboxed execution -> verifiable output
plus the containment moment (a hostile/runaway snippet is absorbed, not fatal)
and the tamper-evident audit chain. Judges can rerun this with no keys.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

import vultr_agent.core as core
import vultr_agent.sandbox as sandbox
import vultr_agent.audit as audit
import vultr_agent.agent as agent

if os.path.exists(core.AUDIT_PATH):
    os.remove(core.AUDIT_PATH)

fails = []
def check(name, cond, detail=""):
    status = "PASS" if cond else "FAIL"
    print(f"[{status}] {name}" + (f"  -> {detail}" if (detail and not cond) else ""))
    if not cond:
        fails.append(name)

CSV = "sales,price\n10,5\n20,3\n30,7\n"

# 1. CSV Analyst happy path (mock mode, stdlib only)
r = core.analyze("total sales", CSV)
check("analyze total_sales ok", r["ok"], r.get("raw_stderr"))
check("result has total_sales", bool(r["result"]) and r["result"].get("metric") == "total_sales", str(r["result"]))
check("audit intact after run", r["audit_intact"], r["audit_note"])

# 2. count rows
r2 = core.analyze("count rows", CSV)
check("count rows == 3", r2["ok"] and r2["result"].get("metric") == "row_count" and r2["result"].get("value") == 3, str(r2["result"]))

# 3. containment moment: hostile/runaway snippet absorbed by the sandbox
c = core.containment_demo()
check("containment absorbed hostile code", c["absorbed"], str(c))
check("containment timed_out (not fatal)", c["timed_out"], str(c))

# 4. bad code fails cleanly via sandbox directly
bad = sandbox.run_code("raise ValueError('boom')", "", timeout=10)
check("bad code -> ok False", not bad["ok"], bad["stderr"])

# 5. self-healing: first attempt fails, second succeeds
state = {"n": 0}
_orig = agent.generate_code
def _fake(q, cols, api_key=None):
    state["n"] += 1
    if state["n"] == 1:
        return "raise RuntimeError('first attempt fails')"
    return "import json\nprint(json.dumps({'metric': 'healed', 'value': 1}))"
agent.generate_code = _fake
rh = core.analyze("heal me", CSV)
agent.generate_code = _orig
check("self-heal retried once", rh["attempts"] == 2, f"attempts={rh['attempts']}")
check("self-heal recovered", rh["ok"], rh.get("raw_stderr"))

# 6. final audit chain integrity
ok_chain, note = audit.verify(core.AUDIT_PATH)
check("final audit chain intact", ok_chain, note)

print(f"\n{len(fails)} FAILED of 12 checks")
if fails:
    print("Failed:", fails)
sys.exit(1 if fails else 0)
