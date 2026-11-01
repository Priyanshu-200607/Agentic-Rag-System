"""
Universal Application Launcher ("Jupyter-Style" Local Experience).
Provides single-command or desktop launch, dynamic non-conflicting port allocation,
background daemon orchestration, and automated browser dispatch.
"""

import os
import sys
import time
import socket
import webbrowser
import subprocess
import logging
from app.lifecycle import setup_signal_handlers, register_cleanup_hook

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("rag_launcher")

def find_available_port(start_port: int = 8000, max_attempts: int = 50) -> int:
    """Probes sequential ports until finding an unbound, available TCP port."""
    for port in range(start_port, start_port + max_attempts):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(("127.0.0.1", port))
                return port
            except OSError:
                continue
    raise RuntimeError(f"Unable to find an open port in range {start_port} - {start_port + max_attempts}")

def is_server_ready(host: str, port: int) -> bool:
    """Checks if the backend API is ready to accept HTTP connections."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.5)
        try:
            s.connect((host, port))
            return True
        except (OSError, socket.timeout):
            return False

def main():
    logger.info("==================================================")
    logger.info("🚀 Launching Multi-Department Agentic RAG Platform")
    logger.info("==================================================")

    setup_signal_handlers()

    # 1. Probe available port
    port = find_available_port(start_port=8000)
    host = "127.0.0.1"
    url = f"http://{host}:{port}"
    logger.info(f"[PORT] Allocated non-conflicting port: {port}")

    # 2. Set backend PYTHONPATH
    backend_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "backend")
    env = os.environ.copy()
    existing_pythonpath = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = f"{backend_dir}:{existing_pythonpath}" if existing_pythonpath else backend_dir

    # 3. Start Uvicorn process
    cmd = [
        sys.executable, "-m", "uvicorn",
        "api.main:app",
        "--host", host,
        "--port", str(port),
        "--log-level", "info"
    ]
    logger.info(f"[SERVER] Spawning backend daemon on {url}...")
    proc = subprocess.Popen(cmd, env=env, cwd=backend_dir)
    register_cleanup_hook(lambda: proc.terminate())

    # 4. Wait for server readiness
    logger.info("[HEALTH] Polling for server readiness...")
    attempts = 0
    while attempts < 30:
        if is_server_ready(host, port):
            break
        time.sleep(0.5)
        attempts += 1

    if attempts >= 30:
        logger.error("[ERROR] Server failed to respond within 15 seconds.")
        proc.terminate()
        sys.exit(1)

    logger.info(f"✅ Backend operational at {url}")

    # 5. Automatically dispatch browser
    logger.info(f"[BROWSER] Opening default web browser to {url}...")
    try:
        webbrowser.open(url)
    except Exception as e:
        logger.warning(f"[BROWSER] Could not auto-launch browser: {e}. Please visit {url} manually.")

    # 6. Keep launcher active until interrupted
    try:
        proc.wait()
    except KeyboardInterrupt:
        logger.info("[LAUNCHER] KeyboardInterrupt detected. Stopping server...")
        proc.terminate()
        proc.wait()

if __name__ == "__main__":
    main()
