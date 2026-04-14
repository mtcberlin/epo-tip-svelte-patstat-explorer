"""
Patent Navigator — Bootstrap & Launch

Handles everything: npm install, build, sidecar, app server.
Designed to be called from a Jupyter notebook cell via %run.
"""

import subprocess
import os
import sys
import time
import socket
import shutil

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
MCP_PORT = 8082
SIDECAR_PORT = 52081
APP_PORT = 52080

REFERENCE_DB_DIR = os.path.join(PROJECT_DIR, "data")
REFERENCE_DB_PATH = os.path.join(REFERENCE_DB_DIR, "reference.db")
REFERENCE_DB_URL = "https://raw.githubusercontent.com/mtcberlin/mtc-patstat-mcp-lite/main/data/reference.db.gz"

try:
    from IPython.display import display, HTML, clear_output
    IN_NOTEBOOK = True
except ImportError:
    IN_NOTEBOOK = False


def _log(msg):
    if IN_NOTEBOOK:
        clear_output(wait=True)
        display(HTML(f"""
        <div style="font-family: system-ui, sans-serif; padding: 20px;
                    background: #f8fafc; border-left: 4px solid #0779bf;
                    border-radius: 8px;">
            <div style="font-size: 15px; color: #334155;">⏳ {msg}</div>
        </div>"""))
    else:
        print(f"  {msg}")


def _port_in_use(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(("127.0.0.1", port)) == 0


def _wait_for_port(port, timeout=15):
    deadline = time.time() + timeout
    while time.time() < deadline:
        if _port_in_use(port):
            return True
        time.sleep(0.3)
    return False


def _run(cmd, cwd=PROJECT_DIR):
    result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(result.stderr or result.stdout or f"Command failed: {cmd}")
    return result


def _ensure_reference_db():
    """Download and decompress the PATSTAT CPC/IPC reference SQLite database.

    The pip-installed mtc-patstat-mcp-lite package does NOT ship the data/
    directory, so we fetch reference.db.gz directly from the GitHub repo
    on first run. Idempotent: skips work if the .db file already exists.
    """
    if os.path.exists(REFERENCE_DB_PATH):
        return
    os.makedirs(REFERENCE_DB_DIR, exist_ok=True)
    gz_path = REFERENCE_DB_PATH + ".gz"
    if not os.path.exists(gz_path):
        _log("Downloading PATSTAT reference database (~19 MB)...")
        import urllib.request
        with urllib.request.urlopen(REFERENCE_DB_URL, timeout=120) as resp:
            with open(gz_path, "wb") as f:
                shutil.copyfileobj(resp, f)
    _log("Decompressing reference database (~145 MB)...")
    import gzip
    with gzip.open(gz_path, "rb") as gz_in, open(REFERENCE_DB_PATH, "wb") as f_out:
        shutil.copyfileobj(gz_in, f_out)


# ---------------------------------------------------------------------------

_processes = []


def stop():
    """Stop all running Patent Navigator processes."""
    for p in _processes:
        try:
            p.terminate()
            p.wait(timeout=5)
        except Exception:
            try:
                p.kill()
            except Exception:
                pass
    _processes.clear()
    if IN_NOTEBOOK:
        clear_output(wait=True)
        display(HTML("""
        <div style="font-family: system-ui, sans-serif; padding: 20px;
                    background: #fef2f2; border-left: 4px solid #dc2626;
                    border-radius: 8px;">
            <div style="font-size: 15px; color: #991b1b;">Patent Navigator gestoppt.</div>
        </div>"""))
    else:
        print("Patent Navigator stopped.")


def launch():
    """Full bootstrap: install, build, start sidecar + app."""
    global _processes

    try:
        # 1. Node.js check
        _log("Checking environment...")
        if not shutil.which("node"):
            raise RuntimeError("Node.js not found. Contact your TIP administrator.")
        node_version = subprocess.run(
            ["node", "--version"], capture_output=True, text=True
        ).stdout.strip()

        # 2. Auto-install mtc.berlin PATSTAT MCP + AI Query deps
        _log("Installing EPO TIP PATSTAT helper tools...")
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "--user",
             "git+https://github.com/mtcberlin/mtc-patstat-mcp-lite.git",
             "fastapi>=0.135",
             "anthropic>=0.40"],
            capture_output=True, text=True, check=True,
        )
        # Ensure ~/.local/bin is in PATH (pip --user installs scripts there)
        local_bin = os.path.expanduser("~/.local/bin")
        if local_bin not in os.environ.get("PATH", ""):
            os.environ["PATH"] = local_bin + ":" + os.environ["PATH"]

        # 2b. Procure CPC/IPC reference database (not shipped with the pip package)
        _ensure_reference_db()

        # 3. npm install (only if needed)
        marker = os.path.join(PROJECT_DIR, "node_modules", ".package-lock.json")
        if not os.path.exists(marker):
            _log("Installing dependencies (first run, ~30s)...")
            _run(["npm", "install", "--prefer-offline"])

        # 4. Build (only if needed)
        build_index = os.path.join(PROJECT_DIR, "build", "index.js")
        needs_build = not os.path.exists(build_index)
        if not needs_build:
            build_mtime = os.path.getmtime(build_index)
            for root, _, files in os.walk(os.path.join(PROJECT_DIR, "src")):
                if any(os.path.getmtime(os.path.join(root, f)) > build_mtime for f in files):
                    needs_build = True
                    break

        if needs_build:
            _log("Building app...")
            _run(["npm", "run", "build"])

        # 5. Start MCP server (or skip if already running)
        if _port_in_use(MCP_PORT):
            _log(f"PATSTAT MCP already running on port {MCP_PORT}")
        else:
            _log("Starting the PATSTAT MCP server...")
            mcp_proc = subprocess.Popen(
                [sys.executable, "-m", "patstat_mcp.server", "--http", "--port", str(MCP_PORT)],
                env={
                    **os.environ,
                    "PATSTAT_REFERENCE_DB": REFERENCE_DB_PATH,
                },
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            _processes.append(mcp_proc)
            if not _wait_for_port(MCP_PORT, timeout=15):
                raise RuntimeError("The PATSTAT MCP server failed to start.")

        # 6. Start sidecar (or skip if already running)
        if _port_in_use(SIDECAR_PORT):
            _log(f"PATSTAT data service already running on port {SIDECAR_PORT}")
        else:
            _log("Starting PATSTAT data service...")
            sidecar = subprocess.Popen(
                [sys.executable, os.path.join(PROJECT_DIR, "sidecar.py")],
                env={
                    **os.environ,
                    "PORT": str(SIDECAR_PORT),
                    "MCP_URL": f"http://127.0.0.1:{MCP_PORT}/mcp",
                    "REFERENCE_DB_PATH": REFERENCE_DB_PATH,
                },
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            _processes.append(sidecar)
            if not _wait_for_port(SIDECAR_PORT, timeout=15):
                raise RuntimeError("PATSTAT data service failed to start.")

        # 7. Start app (or skip if already running)
        if _port_in_use(APP_PORT):
            _log(f"PATSTAT Explorer already running on port {APP_PORT}")
        else:
            _log("Starting PATSTAT Explorer...")
            app = subprocess.Popen(
                ["node", os.path.join(PROJECT_DIR, "build")],
                env={
                    **os.environ,
                    "PORT": str(APP_PORT),
                    "PATSTAT_API": f"http://127.0.0.1:{SIDECAR_PORT}",
                },
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            _processes.append(app)
            if not _wait_for_port(APP_PORT, timeout=10):
                raise RuntimeError("App server failed to start.")

        # 7. Done — show link
        base = os.environ.get("JUPYTERHUB_SERVICE_PREFIX", "/")
        url = f"{base}proxy/{APP_PORT}/"

        if IN_NOTEBOOK:
            clear_output(wait=True)
            display(HTML(f"""
            <div style="font-family: system-ui, sans-serif; text-align: center; padding: 32px;">
                <div style="font-size: 15px; color: #059669; font-weight: 600; margin-bottom: 16px;">
                    ✅ PATSTAT Explorer is running
                </div>
                <a href="{url}" target="_blank"
                   style="display: inline-block; padding: 14px 32px;
                          background: #be0f05;
                          color: white; border-radius: 8px; text-decoration: none;
                          font-size: 16px; font-weight: 600;
                          box-shadow: 0 2px 8px rgba(190, 15, 5, 0.3);">
                    PATSTAT Explorer open &rarr;
                </a>
                <div style="margin-top: 12px; font-size: 12px; color: #9ca3af;">
                    Node {node_version} &middot; Port {APP_PORT}
                </div>
            </div>"""))
        else:
            print(f"\nPatent Navigator is running!\nOpen: {url}")

    except Exception as e:
        if _processes:
            stop()
        if IN_NOTEBOOK:
            clear_output(wait=True)
            display(HTML(f"""
            <div style="font-family: system-ui, sans-serif; padding: 20px;
                        background: #fef2f2; border-left: 4px solid #dc2626;
                        border-radius: 8px;">
                <div style="font-size: 15px; font-weight: 600; color: #991b1b;">Start fehlgeschlagen</div>
                <div style="font-size: 13px; color: #7f1d1d; margin-top: 4px;">{e}</div>
            </div>"""))
        else:
            print(f"ERROR: {e}")


# Auto-launch
launch()
