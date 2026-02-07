#  This file is part of OctoBot Node (https://github.com/Drakkar-Software/OctoBot-Node)
#  Copyright (c) 2025 Drakkar-Software, All rights reserved.
#
#  OctoBot is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either
#  version 3.0 of the License, or (at your option) any later version.
#
#  OctoBot is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#  General Public License for more details.
#
#  You should have received a copy of the GNU General Public
#  License along with OctoBot. If not, see <https://www.gnu.org/licenses/>.
import argparse
import sys
import logging

try:
    import uvicorn
except ImportError:
    print(
        "Error importing uvicorn, please install OctoBot-Node with all dependencies. "
        "Example: \"pip install -U octobot-node\" "
        "(Error: uvicorn not found)", file=sys.stderr
    )
    sys.exit(-1)

from octobot_node import PROJECT_NAME, LONG_VERSION


def start_server(args):
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)-8s %(name)-24s %(message)s")
    port = args.port or 8000
    
    # This must be done before the scheduler module is imported
    from tentacles.Services.Interfaces.node_api.core.config import settings
    
    if args.master:
        settings.IS_MASTER_MODE = True
    settings.SCHEDULER_WORKERS = args.consumers

    # Check that the node is either a master node or has consumers enabled
    if not settings.IS_MASTER_MODE and settings.SCHEDULER_WORKERS <= 0:
        print(
            "Error: Node must be either a master node (--master) or have consumers enabled (--consumers N).\n"
            "  - Use --master to enable master node mode (schedules tasks)\n"
            "  - Use --consumers N to enable consumer workers (processes tasks)\n"
            "  - Use both --master --consumers N to enable both modes",
            file=sys.stderr
        )
        sys.exit(1)

    from octobot_node.scheduler import CONSUMER
    
    if args.environment is not None:
        settings.ENVIRONMENT = args.environment
    
    if args.admin_username is not None:
        settings.ADMIN_USERNAME = args.admin_username
    
    if args.admin_password is not None:
        settings.ADMIN_PASSWORD = args.admin_password
    
    # If not master mode, bind to localhost only
    if args.host is not None:
        host = args.host
    elif settings.IS_MASTER_MODE and settings.ENVIRONMENT == "production":
        host = "0.0.0.0"
    else:
        host = "127.0.0.1"

    # Ensure settings are loaded
    from tentacles.Services.Interfaces.node_api.node_api_interface import NodeApiInterface
    
    uvicorn.run(
        NodeApiInterface.create_app(),
        host=host,
        port=port,
        log_level="info",
        access_log=args.verbose,
    )


def octobot_node_parser(parser):
    """Configure argument parser for OctoBot-Node CLI."""
    parser.add_argument(
        '-v', '--version',
        help='Show OctoBot-Node current version.',
        action='store_true'
    )
    parser.add_argument(
        '--host',
        help='Host to bind the server to (default: 0.0.0.0).',
        type=str,
        default=None
    )
    parser.add_argument(
        '--port',
        help='Port to bind the server to (default: 8000).',
        type=int,
        default=None
    )
    parser.add_argument(
        '--master',
        help='Enable master node mode (schedules tasks, UI enabled by default).',
        action='store_true'
    )
    parser.add_argument(
        '--consumers',
        help='Number of consumer worker threads (0 disables consumers, default: 0). Can be used with --master.',
        type=int,
        default=0
    )
    parser.add_argument(
        '--environment',
        help='Environment mode: local or production (default: from ENVIRONMENT environment variable). Auto-reload is enabled when environment is local.',
        type=str,
        choices=['local', 'production'],
        default=None
    )
    parser.add_argument(
        '--admin-username',
        help='Admin username (email format). Default: from ADMIN_USERNAME environment variable.',
        type=str,
        default=None
    )
    parser.add_argument(
        '--admin-password',
        help='Admin password. Default: from ADMIN_PASSWORD environment variable.',
        type=str,
        default=None
    )
    parser.add_argument(
        '--verbose',
        help='Enable verbose logging, including HTTP access logs.',
        action='store_true'
    )
    parser.set_defaults(func=start_octobot_node)


def start_octobot_node(args):
    if args.version:
        print(LONG_VERSION)
        return
    
    start_server(args)


def main(args=None):
    if not args:
        args = sys.argv[1:]
    
    parser = argparse.ArgumentParser(
        description=PROJECT_NAME,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    octobot_node_parser(parser)
    
    parsed_args = parser.parse_args(args)
    parsed_args.func(parsed_args)
