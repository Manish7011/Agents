"""
start_servers.py
Start or stop all EduManage AI servers.

Usage:
    python start_servers.py          # start all servers + block
    python start_servers.py --stop   # stop all running servers
"""

import argparse
import logging
import os
import signal
import socket
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  [EduServers]  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

SERVERS = [
    {"name": "Student Registration Agent", "module": "mcp_servers.registration_server", "port": 8001},
    {"name": "Course Management Agent", "module": "mcp_servers.course_server", "port": 8002},
    {"name": "Enrollment Agent", "module": "mcp_servers.enrollment_server", "port": 8003},
    {"name": "Grade & Transcript Agent", "module": "mcp_servers.grade_server", "port": 8004},
    {"name": "Academic Advising Agent", "module": "mcp_servers.advising_server", "port": 8005},
    {"name": "Fee & Scholarship Agent", "module": "mcp_servers.fee_server", "port": 8006},
    {"name": "Timetable & Scheduling Agent", "module": "mcp_servers.timetable_server", "port": 8007},
    {"name": "Supervisor Agent", "module": "supervisor.supervisor_server", "port": 9001},
]

_processes: list[subprocess.Popen] = []
_log_files: list = []
_reported_dead: set[int] = set()


def _wait_for_port(port: int, timeout_s: float = 12.0) -> bool:
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(0.6)
            if s.connect_ex(("127.0.0.1", port)) == 0:
                return True
        time.sleep(0.25)
    return False


def _launch(server: dict) -> subprocess.Popen | None:
    try:
        base_dir = Path(os.path.dirname(os.path.abspath(__file__)))
        logs_dir = base_dir / "logs"
        logs_dir.mkdir(exist_ok=True)
        log_path = logs_dir / f"{server['module'].split('.')[-1]}.log"

        log_fp = open(log_path, "a", encoding="utf-8")
        _log_files.append(log_fp)

        p = subprocess.Popen(
            [sys.executable, "-m", server["module"]],
            cwd=str(base_dir),
            stdout=log_fp,
            stderr=log_fp,
        )

        if _wait_for_port(server["port"], timeout_s=12.0):
            log.info("OK  %-35s  port %-5d  PID %d", server["name"], server["port"], p.pid)
        else:
            log.error("FAIL %-35s  port %-5d did not open. See %s", server["name"], server["port"], log_path)
        return p
    except Exception as exc:
        log.error("Failed to start %s: %s", server["name"], exc)
        return None


def _stop_all() -> None:
    log.info("Stopping %d server(s)...", len(_processes))
    for p in _processes:
        try:
            p.terminate()
        except Exception:
            pass
    time.sleep(1.2)
    for p in _processes:
        try:
            if p.poll() is None:
                p.kill()
        except Exception:
            pass
    for fp in _log_files:
        try:
            fp.close()
        except Exception:
            pass
    log.info("All servers stopped.")


def _sig(_sig_num, _frame) -> None:
    log.info("Shutting down...")
    _stop_all()
    sys.exit(0)


def start() -> None:
    from database.db import init_db

    log.info("Initialising database...")
    init_db()
    log.info("Starting %d servers...", len(SERVERS))

    for srv in SERVERS[:-1]:
        p = _launch(srv)
        if p:
            _processes.append(p)
        time.sleep(0.25)

    log.info("Waiting for specialist agents...")
    time.sleep(1.0)

    p = _launch(SERVERS[-1])
    if p:
        _processes.append(p)

    log.info(
        "\nEduManage AI server manager is running.\n"
        "UI: http://localhost:8501\n"
        "Supervisor: http://127.0.0.1:9001/mcp\n"
        "Logs directory: ./logs\n"
        "Press Ctrl-C to stop all servers."
    )

    signal.signal(signal.SIGINT, _sig)
    signal.signal(signal.SIGTERM, _sig)

    while True:
        time.sleep(5)
        for srv, proc in zip(SERVERS, _processes):
            if proc.poll() is not None and proc.pid not in _reported_dead:
                _reported_dead.add(proc.pid)
                log.warning("Server '%s' (port %d) exited. Check logs/%s.log", srv["name"], srv["port"], srv["module"].split(".")[-1])


def stop() -> None:
    try:
        import psutil
    except ImportError:
        log.error("psutil not installed. Run: pip install psutil")
        return

    ports = {s["port"] for s in SERVERS}
    killed = 0
    for proc in psutil.process_iter(["pid"]):
        try:
            for conn in proc.net_connections(kind="inet"):
                if conn.laddr.port in ports:
                    proc.terminate()
                    log.info("Stopped PID %d on port %d", proc.pid, conn.laddr.port)
                    killed += 1
                    break
        except Exception:
            pass

    if not killed:
        log.info("No EduManage servers found running.")
    else:
        log.info("Stopped %d server(s).", killed)


def main() -> None:
    parser = argparse.ArgumentParser(description="EduManage AI - Server Manager")
    parser.add_argument("--stop", action="store_true", help="Stop all running servers")
    args = parser.parse_args()
    stop() if args.stop else start()


if __name__ == "__main__":
    main()
