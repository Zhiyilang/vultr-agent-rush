"""Vultr Agent Rush — Blast Radius Zero (Pattern A: sandboxed code execution).

A web-based agent that takes a natural-language request + an uploaded dataset,
asks an LLM (Vultr Serverless Inference, OpenAI-compatible) to write analysis
code, runs that code inside an isolated sandbox (Docker on Vultr, subprocess
fallback locally), and returns verifiable output plus a tamper-evident audit
log. Containment-first: the untrusted code never touches the host or app
runtime.

Zero hard dependencies for the core logic; Flask only for the optional web UI.
"""
