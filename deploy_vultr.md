# Deploy on Vultr (submission requirement)

Vultr Agent Rush requires the backend on a **Vultr VM** with LLM calls through
**Vultr Serverless Inference**, and sandboxing on Vultr (Docker). This guide gets
there in ~10 minutes.

## 1. Account + credits
- Sign up at https://www.vultr.com/ and join the hackathon on LabLab + its Discord.
- Claim the **$200 hackathon credits** (see the Vultr credits walkthrough on the
  hackathon page).

## 2. Serverless Inference key
- In the Vultr customer portal, create an API key for **Serverless Inference**
  (base URL `https://api.vultrinference.com/v1`, OpenAI-compatible, vision-capable
  models available).
- This becomes `VULTR_API_KEY` used by `vultr_agent/agent.py`.

## 3. VM + Docker
```bash
# on the Vultr VM (Ubuntu 22.04)
sudo apt update && sudo apt install -y docker.io git python3-pip
sudo systemctl enable --now docker
sudo usermod -aG docker $USER   # re-login after
```

## 4. Run
```bash
git clone <this-repo> && cd vultr_agent
pip3 install -r requirements.txt
printf 'VULTR_API_KEY=<paste-key>\n' > .env
docker build -t vultr-agent .
docker run -d --restart unless-stopped -p 8080:8080 --env-file .env vultr-agent
```
The app detects Docker and isolates untrusted code inside a container
(`--network none`, memory cap, timeout) — meeting the containment requirement.

## 5. Expose + submit
- Open port 8080 in the Vultr firewall, point your public demo URL at
  `http://<vm-ip>:8080`.
- Record a demo video that shows **one containment moment** (click
  "Run hostile snippet" — the sandbox absorbs `rm -rf /` + infinite loop).
- Submit on LabLab with the public GitHub repo, demo URL and video.

> Local fallback: without Docker the app still runs (subprocess + timeout), so
> you can develop and verify `eval.py` on any laptop before deploying.
