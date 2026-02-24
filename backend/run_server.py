"""
run_server.py - Robust backend startup with auto-restart on crash
Usage: python run_server.py
"""
import uvicorn
import sys
import os
import time
import socket
import signal
import subprocess

PORT = 8000
HOST = "0.0.0.0"
MAX_RESTARTS = 10
RESTART_DELAY = 3  # seconds between restarts


def is_port_in_use(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(1)
        return s.connect_ex(("127.0.0.1", port)) == 0


def kill_port(port: int):
    """Kill any process using the given port on Windows."""
    try:
        result = subprocess.run(
            ["netstat", "-ano"],
            capture_output=True, text=True, timeout=5
        )
        for line in result.stdout.splitlines():
            if f":{port}" in line and "LISTENING" in line:
                parts = line.strip().split()
                pid = parts[-1]
                if pid.isdigit() and int(pid) != 0:
                    try:
                        subprocess.run(
                            ["taskkill", "/F", "/PID", pid],
                            capture_output=True, timeout=5
                        )
                        print(f"[startup] Killed PID {pid} on port {port}")
                    except Exception:
                        pass
    except Exception as e:
        print(f"[startup] Could not kill port {port}: {e}")


def run():
    os.chdir(os.path.dirname(os.path.abspath(__file__)))

    # Ensure UTF-8 output
    os.environ["PYTHONIOENCODING"] = "utf-8"
    os.environ["PYTHONUTF8"] = "1"

    restart_count = 0

    while restart_count <= MAX_RESTARTS:
        # Kill stale processes on port before starting
        if is_port_in_use(PORT):
            print(f"[startup] Port {PORT} is in use. Killing existing process...")
            kill_port(PORT)
            time.sleep(2)

        if is_port_in_use(PORT):
            print(f"[startup] WARNING: Port {PORT} still in use after kill attempt. Waiting...")
            time.sleep(3)

        print(f"[startup] Starting uvicorn (attempt {restart_count + 1})...")

        try:
            uvicorn.run(
                "main:app",
                host=HOST,
                port=PORT,
                reload=False,         # No reload in production (causes port conflicts)
                workers=1,            # Single worker to avoid port conflicts
                log_level="info",
                access_log=True,
                loop="asyncio",
            )
            # If uvicorn exits cleanly (exit code 0), don't restart
            print("[startup] Server stopped cleanly.")
            break

        except SystemExit as e:
            if e.code == 0:
                print("[startup] Server exited cleanly.")
                break
            print(f"[startup] Server crashed with exit code {e.code}. Restarting in {RESTART_DELAY}s...")

        except KeyboardInterrupt:
            print("\n[startup] Interrupted by user. Stopping.")
            break

        except Exception as e:
            print(f"[startup] Unexpected error: {e}")

        restart_count += 1
        if restart_count <= MAX_RESTARTS:
            print(f"[startup] Restart {restart_count}/{MAX_RESTARTS} in {RESTART_DELAY}s...")
            time.sleep(RESTART_DELAY)
        else:
            print(f"[startup] Max restarts ({MAX_RESTARTS}) reached. Giving up.")
            sys.exit(1)


if __name__ == "__main__":
    run()
