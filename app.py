"""Flask web UI for the Vultr Agent Rush submission.

Zero-config locally: run with no VULTR_API_KEY and it uses the offline mock
(core.analyze still executes real code in a real sandbox, just the *generator*
is mocked). On Vultr, set VULTR_API_KEY and the app calls Vultr Serverless
Inference; with Docker present, untrusted code runs in a throwaway container.

Routes:
  GET  /                 single-page demo
  GET  /healthz          liveness probe
  POST /api/analyze      {query, csv} -> full receipt JSON
  POST /api/containment  run the hostile-snippet absorption demo
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from flask import Flask, request, jsonify, Response
from vultr_agent import core

app = Flask(__name__)

INDEX = """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Vultr Agent Rush - Blast Radius Zero</title>
<style>
:root{--bg:#0e1116;--panel:#161b22;--ink:#e6edf3;--muted:#9da7b3;--line:#2a313a;
--accent:#58a6ff;--good:#3fb950;--bad:#f85149;--warn:#d29922}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);
font:15px/1.55 -apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif}
.wrap{max-width:980px;margin:0 auto;padding:28px 20px 60px}
h1{font-size:30px;margin:0 0 4px}.sub{color:var(--muted);margin-bottom:22px}
.card{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:16px 18px;margin-bottom:16px}
label{display:block;color:var(--accent);font-weight:600;margin-bottom:6px;font-size:13px}
textarea,input[type=text]{width:100%;background:#0b0e13;color:var(--ink);border:1px solid var(--line);
border-radius:8px;padding:10px;font-family:ui-monospace,Consolas,monospace;font-size:13px}
button{cursor:pointer;border-radius:8px;border:1px solid var(--line);background:#1c2330;color:var(--ink);
padding:9px 16px;font-weight:600;margin-top:10px}
button:hover{border-color:var(--accent)}
pre{background:#0b0e13;border:1px solid var(--line);border-radius:8px;padding:12px;overflow:auto;
font-size:12.5px;white-space:pre-wrap}
.tag{display:inline-block;padding:2px 8px;border-radius:999px;font-size:12px;font-weight:600}
.ok{background:rgba(63,185,80,.15);color:var(--good)}.no{background:rgba(248,81,73,.15);color:var(--bad)}
</style></head>
<body><div class="wrap">
<h1>Blast Radius Zero</h1>
<div class="sub">A web agent that writes & runs code in an isolated sandbox on Vultr. Untrusted code never touches the host.</div>

<div class="card">
  <label>1. Upload a CSV dataset</label>
  <input type="file" id="csv" accept=".csv">
  <label style="margin-top:12px">2. Ask in plain English</label>
  <input type="text" id="query" placeholder="e.g. what is the total sales?" value="what is the total sales?">
  <button onclick="runAnalyze()">Run in sandbox</button>
</div>

<div class="card" id="out" style="display:none">
  <label>Generated code (executed in sandbox)</label><pre id="code"></pre>
  <label>Verifiable result</label><pre id="result"></pre>
  <label>Audit</label><pre id="audit"></pre>
</div>

<div class="card">
  <label>Containment moment</label>
  <button onclick="runContainment()">Run hostile snippet (rm -rf / + infinite loop)</button>
  <pre id="containment"></pre>
</div>
</div>

<script>
async function runAnalyze(){
  const f=document.getElementById('csv').files[0];
  const csv=f?await f.text():'sales,price\\n10,5\\n20,3\\n30,7\\n';
  const q=document.getElementById('query').value;
  const r=await fetch('/api/analyze',{method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({query:q,csv})});
  const d=await r.json();
  document.getElementById('out').style.display='block';
  document.getElementById('code').textContent=(d.attempts?d.attempts:1)>1?'[self-healed] ':'';
  document.getElementById('code').textContent+= (d.attempts&&d.attempts>1?d.attempts:'') ;
  document.getElementById('code').textContent=(d.raw_stderr&&!d.ok?'': '') + JSON.stringify(d,null,2);
  document.getElementById('result').textContent=JSON.stringify(d.result,null,2);
  document.getElementById('audit').textContent='engine='+d.engine+'  attempts='+d.attempts+'  audit_intact='+d.audit_intact;
}
async function runContainment(){
  const r=await fetch('/api/containment',{method:'POST'});
  const d=await r.json();
  document.getElementById('containment').textContent=JSON.stringify(d,null,2);
}
</script></body></html>"""


@app.route("/")
def index():
    return Response(INDEX, mimetype="text/html")


@app.route("/healthz")
def healthz():
    return jsonify({"ok": True})


@app.route("/api/analyze", methods=["POST"])
def analyze():
    data = request.get_json(force=True, silent=True) or {}
    query = (data.get("query") or "").strip()
    csv_text = data.get("csv") or ""
    if not query:
        return jsonify({"ok": False, "error": "missing query"}), 400
    res = core.analyze(query, csv_text, api_key=os.environ.get("VULTR_API_KEY"))
    return jsonify(res)


@app.route("/api/containment", methods=["POST"])
def containment():
    return jsonify(core.containment_demo())


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
