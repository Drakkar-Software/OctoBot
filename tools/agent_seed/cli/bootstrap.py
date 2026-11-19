#  Bootstrap subcommand CLI.

import argparse
import typing

import tools.agent_seed.enums as agent_seed_enums
import tools.agent_seed.operations.bootstrap_grid as agent_seed_bootstrap_grid
import tools.agent_seed.operations.bootstrap_scenarios as agent_seed_bootstrap_scenarios

EMIT_SIGNALS_HELP = (
    "Create each seeded automation with signal emitting turned on (default: off). "
    "A copy follower needs the leader to finish one iteration with signals on"
)


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Bootstrap demo agent-seed grid automation")
    parser.add_argument(
        "--base-url",
        default="http://127.0.0.1:8000",
        help="Node API base URL",
    )
    parser.add_argument(
        "--poll-interval",
        type=float,
        default=agent_seed_bootstrap_grid.DEFAULT_POLL_INTERVAL_SECONDS,
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=agent_seed_bootstrap_grid.DEFAULT_TIMEOUT_SECONDS,
    )
    parser.add_argument(
        "--scenario",
        action="append",
        choices=[scenario.value for scenario in agent_seed_enums.BootstrapScenario],
        default=None,
        help="Scenario to run, repeatable (default: grid). all = grid, index, completed, lifecycle",
    )
    parser.add_argument("--emit-signals", action="store_true", help=EMIT_SIGNALS_HELP)
    return parser


def main(argv: typing.Optional[list[str]] = None) -> int:
    arguments = build_arg_parser().parse_args(argv)
    agent_seed_bootstrap_scenarios.run_scenarios(
        base_url=arguments.base_url,
        scenarios=[agent_seed_enums.BootstrapScenario(value) for value in arguments.scenario or []],
        poll_interval_seconds=arguments.poll_interval,
        timeout_seconds=arguments.timeout,
        emit_signals=arguments.emit_signals,
    )
    return 0


def run_from_namespace(arguments: argparse.Namespace) -> int:
    bootstrap_argv = ["--base-url", arguments.base_url]
    if arguments.poll_interval is not None:
        bootstrap_argv.extend(["--poll-interval", str(arguments.poll_interval)])
    if arguments.timeout is not None:
        bootstrap_argv.extend(["--timeout", str(arguments.timeout)])
    for scenario in arguments.scenario or []:
        bootstrap_argv.extend(["--scenario", scenario])
    if arguments.emit_signals:
        bootstrap_argv.append("--emit-signals")
    return main(bootstrap_argv)
