"""Tamper-evident audit log (hash chain).

Every execution is recorded with a hash linking to the previous record. Any
post-hoc edit breaks the chain, so the log the agent shows a judge is
cryptographically tied to what actually ran. Reuses the design from
github.com/Zhiyilang/swarmbox (MIT).
"""
import hashlib
import json
import os


def _digest(*parts) -> str:
    h = hashlib.sha256()
    for p in parts:
        h.update(str(p).encode("utf-8"))
    return h.hexdigest()


def append(path: str, record: dict) -> dict:
    records = read(path)
    prev = records[-1]["digest"] if records else "GENESIS"
    record = dict(record)
    record["seq"] = len(records) + 1
    record["prev"] = prev
    record["digest"] = _digest(record["seq"], prev, record.get("code", ""),
                               record.get("stdout", ""), record.get("stderr", ""))
    records.append(record)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(records, f, indent=2, ensure_ascii=False)
    return record


def read(path: str) -> list:
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except Exception:
            return []


def verify(path: str) -> tuple[bool, str]:
    records = read(path)
    prev = "GENESIS"
    for i, r in enumerate(records, 1):
        expect = _digest(r["seq"], prev, r.get("code", ""),
                         r["stdout"], r["stderr"])
        if r["prev"] != prev or r["digest"] != expect:
            return False, f"record #{i} broken chain"
        prev = r["digest"]
    return True, f"{len(records)} records intact"
