# Vultr Agent Rush — Blast Radius Zero

A web-based agent that performs real work — **writing and running code** — with
every action contained inside an isolated sandbox. Built for the
[Vultr × lablab.ai Agent Rush Hackathon](https://lablab.ai/ai-hackathons/vultr-hackathon)
(challenge *Blast Radius Zero*, Pattern A: sandboxed code execution).

> **Containment-first.** The untrusted code an LLM generates never touches the
> host or the app runtime. On Vultr it runs inside a throwaway Docker container
> with no network, a memory cap and a hard timeout; the container is destroyed
> after each run.

## What it does (use case: CSV Analyst + Self-Healing Runner)

1. User uploads a CSV and asks a question in plain English.
2. An LLM (Vultr Serverless Inference, OpenAI-compatible) writes analysis code.
3. The code runs **inside a sandbox** that reads the dataset and prints JSON.
4. The agent verifies the output; if the first run fails, it feeds the error
   back, regenerates once, and re-runs (self-healing loop).
5. Every execution is written to a **tamper-evident audit log** (hash chain),
   so a judge can cryptographically confirm what actually ran.

A built-in `/api/containment` endpoint demonstrates the containment moment: a
hostile snippet (`rm -rf /` + infinite loop) is absorbed by the sandbox instead
of taking down the host.

## Architecture

```
 Browser ──► Flask app (control layer, on Vultr VM)
                  │
                  ├─► Vultr Serverless Inference (LLM writes code)   [api.vultrinference.com/v1]
                  │
                  └─► Sandbox (isolated execution)
                        ├─ Docker container on Vultr  (production)
                        └─ subprocess + timeout      (local fallback)
                              │
                              └─► tamper-evident audit log (hash chain)
```

The Flask app is the **central control and orchestration system** (required
stack: Vultr VM). All LLM calls go through **Vultr Serverless Inference**.
Untrusted code is dispatched to an **isolated execution environment** and returns
verifiable output — exactly the pattern Vultr asks for.

## Run locally (offline, zero config)

```bash
pip install -r requirements.txt
python app.py                 # http://localhost:8080
```

With no `VULTR_API_KEY` the code *generator* uses a deterministic offline mock,
but the sandbox, execution, verification and audit are all real. Prove it:

```bash
python eval.py               # 12/12 checks pass, no keys, no network
```

## Deploy on Vultr (required for submission)

1. Create a [Vultr](https://www.vultr.com/) account and claim your **$200 hackathon credits**.
2. Deploy a Vultr VM (any Linux, e.g. Ubuntu 22.04). SSH in and:
   ```bash
   sudo apt update && sudo apt install -y docker.io git python3-pip
   sudo systemctl enable --now docker
   git clone <this-repo> && cd vultr_agent
   pip3 install -r requirements.txt
   echo "VULTR_API_KEY=<your Vultr Serverless Inference key>" >> .env
   docker build -t vultr-agent . && docker run -d --restart unless-stopped \
        -p 8080:8080 --env-file .env vultr-agent
   ```
3. Point your public demo URL at the VM's IP:8080 and submit on LabLab.

The app auto-detects Docker and switches the sandbox to container isolation,
satisfying the "sandbox on Vultr, never inside the app process" requirement.

## API

| Method | Path | Body | Returns |
|--------|------|------|---------|
| GET | `/` | — | single-page demo |
| GET | `/healthz` | — | `{"ok": true}` |
| POST | `/api/analyze` | `{query, csv}` | full receipt (code, result, audit) |
| POST | `/api/containment` | — | hostile-snippet absorption demo |

## Files

- `vultr_agent/agent.py` — Vultr Serverless Inference client + offline mock
- `vultr_agent/sandbox.py` — Docker (prod) / subprocess (local) isolation
- `vultr_agent/audit.py` — tamper-evident hash-chain log
- `vultr_agent/core.py` — orchestration + self-healing
- `app.py` — Flask web UI
- `eval.py` — offline, zero-dependency verification
- `Dockerfile` — app packaging for the Vultr VM

MIT licensed.

---

## 💝 赞助 / 打赏

如果这个项目对你有帮助，欢迎通过 **爱发电** 请我喝杯咖啡 ☕  
👉 https://afdian.com/a/Zhiyilang

> GitHub Sponsors 在中国大陆暂不支持个人账号，赞助统一走爱发电。

---
## 📚 我的实战课程
**《影刀RPA到AI Agent工程师：大专生的实战转型笔记》** —— 5 课可直接抄的作业（含可复制代码模板 + 真实接单复盘）。
在 **小报童 / 小红书** 搜索「支一郎」即可购买；完整大纲见 [GitHub Pages](https://Zhiyilang.github.io/#course)。
