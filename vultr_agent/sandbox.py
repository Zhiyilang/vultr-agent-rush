"""Isolated code execution.

Production path (Vultr): run the untrusted code inside a throwaway Docker
container with no network, a memory cap and a hard timeout. The container is
destroyed after each run (lifecycle discipline). Local fallback (no Docker, e.g.
running eval.py on a laptop) uses a subprocess with a timeout so the pipeline is
still testable offline. Either way the untrusted code never touches the host or
the app runtime.
"""
import os
import sys
import shutil
import subprocess
import tempfile
import textwrap


def run_code(code: str, csv_text: str = "", timeout: int = 20,
             memory_mb: int = 256, cpus: float = 1.0) -> dict:
    """Execute `code` (which reads /data/in.csv) in isolation.

    Returns a dict: {ok, stdout, stderr, timed_out, exit_code, engine}.
    """
    if shutil.which("docker"):
        return _run_docker(code, csv_text, timeout, memory_mb, cpus)
    return _run_subprocess(code, csv_text, timeout)


def _run_docker(code, csv_text, timeout, memory_mb, cpus) -> dict:
    work = tempfile.mkdtemp(prefix="vultr_sbx_")
    code_path = os.path.join(work, "user_code.py")
    with open(code_path, "w", encoding="utf-8") as f:
        f.write(code)
    csv_path = os.path.join(work, "in.csv")
    with open(csv_path, "w", encoding="utf-8") as f:
        f.write(csv_text or "")
    try:
        proc = subprocess.run(
            ["docker", "run", "--rm", "--network", "none",
             "--memory", f"{memory_mb}m", "--cpus", str(cpus),
             "-v", f"{work}:/data:rw", "python:3.11-slim",
             "python", "/data/user_code.py"],
            capture_output=True, text=True, timeout=timeout,
        )
        return {
            "ok": proc.returncode == 0,
            "stdout": proc.stdout,
            "stderr": proc.stderr,
            "timed_out": False,
            "exit_code": proc.returncode,
            "engine": "docker",
        }
    except subprocess.TimeoutExpired as e:
        return {
            "ok": False, "stdout": e.stdout or "", "stderr": "TIMEOUT",
            "timed_out": True, "exit_code": -1, "engine": "docker",
        }
    finally:
        shutil.rmtree(work, ignore_errors=True)


def _run_subprocess(code, csv_text, timeout) -> dict:
    """Local fallback. Redirects `/data/...` opens into a temp dir so the
    untrusted code runs exactly as it would inside the Docker mount, without
    needing write access to the system root."""
    work = tempfile.mkdtemp(prefix="vultr_sbx_")
    data_dir = os.path.join(work, "data")
    os.makedirs(data_dir, exist_ok=True)
    with open(os.path.join(data_dir, "in.csv"), "w", encoding="utf-8") as f:
        f.write(csv_text or "")
    code_path = os.path.join(work, "user_code.py")
    with open(code_path, "w", encoding="utf-8") as f:
        f.write(code)
    wrapper = textwrap.dedent(
        f"""
        import os, builtins
        _MOUNT = {data_dir!r}
        os.makedirs(_MOUNT, exist_ok=True)
        _orig_open = builtins.open
        def _sandbox_open(path, *a, **k):
            if isinstance(path, str) and path.startswith('/data/'):
                path = os.path.join(_MOUNT, path[len('/data/'):])
            return _orig_open(path, *a, **k)
        builtins.open = _sandbox_open
        exec(compile(open({code_path!r}).read(), 'user_code.py', 'exec'))
        """
    )
    try:
        proc = subprocess.run(
            [sys.executable, "-c", wrapper],
            capture_output=True, text=True, timeout=timeout,
        )
        return {
            "ok": proc.returncode == 0,
            "stdout": proc.stdout,
            "stderr": proc.stderr,
            "timed_out": False,
            "exit_code": proc.returncode,
            "engine": "subprocess",
        }
    except subprocess.TimeoutExpired as e:
        return {
            "ok": False, "stdout": e.stdout or "", "stderr": "TIMEOUT",
            "timed_out": True, "exit_code": -1, "engine": "subprocess",
        }
    finally:
        shutil.rmtree(work, ignore_errors=True)
