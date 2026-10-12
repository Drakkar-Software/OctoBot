#  Agent-seed background node pidfile, port checks, and graceful stop.

import os
import pathlib
import re
import signal
import subprocess
import time
import typing

import tools.agent_seed.errors as agent_seed_errors
import tools.agent_seed.operations.base_url_net as agent_seed_base_url_net
import tools.agent_seed.paths as agent_seed_paths

DEFAULT_STOP_TIMEOUT_SECONDS = 30.0
_GRACEFUL_SIGNALS = (signal.SIGINT, signal.SIGTERM)
_PID_FROM_SS_PATTERN = re.compile(r"pid=(\d+)")
_STOP_SHELL_HINT = "bash .cursor/seed-agent.sh --stop"


def read_recorded_pid(pid_file: pathlib.Path) -> typing.Optional[int]:
    if not pid_file.is_file():
        return None
    content = pid_file.read_text(encoding="utf-8").strip()
    if not content:
        return None
    return int(content)


def is_process_running(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


def find_listener_pids(port: int) -> list[int]:
    try:
        completed = subprocess.run(
            ["ss", "-ltnp", f"sport = :{port}"],
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError:
        return []
    pids: list[int] = []
    for match in _PID_FROM_SS_PATTERN.finditer(completed.stdout):
        pids.append(int(match.group(1)))
    return sorted(set(pids))


def _format_port_busy_message(port: int, pids: list[int]) -> str:
    if pids:
        pid_list = ", ".join(str(pid) for pid in pids)
        return f"port {port} is already in use (listener PID {pid_list})"
    return f"port {port} is already in use"


def ensure_port_free_for_start(base_url: str) -> None:
    host, port = agent_seed_base_url_net.parse_host_port(base_url)
    if not agent_seed_base_url_net.is_tcp_port_accepting(host, port):
        return
    pids = find_listener_pids(port)
    busy = _format_port_busy_message(port, pids)
    raise agent_seed_errors.AgentSeedPortInUseError(
        f"Cannot start agent-seed node: {busy}. Stop it with: {_STOP_SHELL_HINT}"
    )


def prepare_node_start(user_folder: pathlib.Path, base_url: str) -> None:
    pid_file = agent_seed_paths.node_pid_file(user_folder)
    recorded_pid = read_recorded_pid(pid_file)
    if recorded_pid is not None:
        if is_process_running(recorded_pid):
            raise agent_seed_errors.AgentSeedPortInUseError(
                "Cannot start agent-seed node: recorded node is still running "
                f"(pid {recorded_pid}). Stop it with: {_STOP_SHELL_HINT}"
            )
        pid_file.unlink(missing_ok=True)
    ensure_port_free_for_start(base_url)


def _wait_process_exit(pid: int, timeout_seconds: float) -> bool:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        if not is_process_running(pid):
            return True
        time.sleep(0.2)
    return not is_process_running(pid)


def _terminate_pid(pid: int, stop_timeout_seconds: float) -> None:
    if not is_process_running(pid):
        return
    per_signal_timeout = max(stop_timeout_seconds / len(_GRACEFUL_SIGNALS), 1.0)
    for sig in _GRACEFUL_SIGNALS:
        try:
            os.kill(pid, sig)
        except ProcessLookupError:
            return
        if _wait_process_exit(pid, per_signal_timeout):
            return
    try:
        os.kill(pid, signal.SIGKILL)
    except ProcessLookupError:
        return
    _wait_process_exit(pid, 5.0)


def stop_recorded_node(
    user_folder: pathlib.Path,
    base_url: str,
    stop_timeout_seconds: float = DEFAULT_STOP_TIMEOUT_SECONDS,
) -> str:
    pid_file = agent_seed_paths.node_pid_file(user_folder)
    host, port = agent_seed_base_url_net.parse_host_port(base_url)
    recorded_pid = read_recorded_pid(pid_file)

    if recorded_pid is None:
        if agent_seed_base_url_net.is_tcp_port_accepting(host, port):
            pids = find_listener_pids(port)
            busy = _format_port_busy_message(port, pids)
            raise agent_seed_errors.AgentSeedNodeStopError(
                f"No agent-seed pidfile at {pid_file}, but {busy}. "
                "Stop the process manually or free the port."
            )
        return f"No agent-seed node recorded (no pidfile at {pid_file})."

    stopped_pid = recorded_pid
    _terminate_pid(stopped_pid, stop_timeout_seconds)
    pid_file.unlink(missing_ok=True)

    if agent_seed_base_url_net.is_tcp_port_accepting(host, port):
        pids = find_listener_pids(port)
        busy = _format_port_busy_message(port, pids)
        raise agent_seed_errors.AgentSeedNodeStopError(
            f"Stopped pid {stopped_pid}, but {busy}. Stop remaining listeners manually."
        )
    return f"Stopped agent-seed node (pid {stopped_pid}). Port {port} is free."
