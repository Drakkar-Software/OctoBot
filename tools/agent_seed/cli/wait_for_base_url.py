#  wait-for-base-url subcommand CLI.

import argparse
import os
import sys
import typing

import tools.agent_seed.errors as agent_seed_errors
import tools.agent_seed.operations.wait_for_base_url as agent_seed_wait_for_base_url


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Wait until the agent-seed node accepts TCP connections on its base URL",
    )
    parser.add_argument(
        "--base-url",
        default=os.environ.get("AGENT_SEED_BASE_URL", "http://127.0.0.1:8000"),
        help="Node API base URL (default: AGENT_SEED_BASE_URL or http://127.0.0.1:8000)",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=None,
        help=(
            "Seconds to wait (default: AGENT_SEED_STARTUP_WAIT_SEC or "
            f"{agent_seed_wait_for_base_url.DEFAULT_STARTUP_WAIT_SECONDS:g})"
        ),
    )
    parser.add_argument(
        "--poll-interval",
        type=float,
        default=None,
        help=(
            "Seconds between connection attempts "
            f"(default: {agent_seed_wait_for_base_url.DEFAULT_POLL_INTERVAL_SECONDS:g})"
        ),
    )
    return parser


def _resolve_timeout_seconds(timeout: typing.Optional[float]) -> float:
    if timeout is not None:
        return timeout
    env_value = os.environ.get("AGENT_SEED_STARTUP_WAIT_SEC")
    if env_value is not None:
        return float(env_value)
    return agent_seed_wait_for_base_url.DEFAULT_STARTUP_WAIT_SECONDS


def main(argv: typing.Optional[list[str]] = None) -> int:
    arguments = build_arg_parser().parse_args(argv)
    poll_interval_seconds = arguments.poll_interval
    if poll_interval_seconds is None:
        poll_interval_seconds = agent_seed_wait_for_base_url.DEFAULT_POLL_INTERVAL_SECONDS
    try:
        agent_seed_wait_for_base_url.wait_for_base_url(
            base_url=arguments.base_url,
            timeout_seconds=_resolve_timeout_seconds(arguments.timeout),
            poll_interval_seconds=poll_interval_seconds,
        )
    except agent_seed_errors.AgentSeedNodeStartupTimeoutError as error:
        print(error, file=sys.stderr)
        return 1
    return 0


def run_from_namespace(arguments: argparse.Namespace) -> int:
    wait_argv = ["--base-url", arguments.base_url]
    if arguments.timeout is not None:
        wait_argv.extend(["--timeout", str(arguments.timeout)])
    if arguments.poll_interval is not None:
        wait_argv.extend(["--poll-interval", str(arguments.poll_interval)])
    return main(wait_argv)
