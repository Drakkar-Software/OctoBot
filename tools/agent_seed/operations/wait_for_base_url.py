#  Poll until the agent-seed node accepts TCP connections on its base URL.

import socket
import time

import tools.agent_seed.errors as agent_seed_errors
import tools.agent_seed.operations.base_url_net as agent_seed_base_url_net

DEFAULT_STARTUP_WAIT_SECONDS = 90.0
DEFAULT_POLL_INTERVAL_SECONDS = 1.0
_CONNECT_TIMEOUT_SECONDS = 2.0


def wait_for_base_url(
    base_url: str,
    timeout_seconds: float = DEFAULT_STARTUP_WAIT_SECONDS,
    poll_interval_seconds: float = DEFAULT_POLL_INTERVAL_SECONDS,
) -> None:
    host, port = agent_seed_base_url_net.parse_host_port(base_url)
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        try:
            with socket.create_connection((host, port), timeout=_CONNECT_TIMEOUT_SECONDS):
                return
        except OSError:
            time.sleep(poll_interval_seconds)
    raise agent_seed_errors.AgentSeedNodeStartupTimeoutError(
        f"Timed out after {int(timeout_seconds)}s waiting for agent-seed node at {base_url}"
    )
