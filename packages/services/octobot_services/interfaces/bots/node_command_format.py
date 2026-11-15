#  Drakkar-Software OctoBot-Services
#  Copyright (c) Drakkar-Software, All rights reserved.

import octobot_commons.pretty_printer as pretty_printer
import octobot_services.interfaces as interfaces


NODE_NO_AUTOMATIONS_MESSAGE = (
    "No automations on this node yet. Start a bot from the Node interface."
)
NODE_COMMAND_UNAVAILABLE_MESSAGE = (
    "This command is not available on an OctoBot node host. "
    "Use the Node web interface or a process bot."
)


def automation_title(views, view) -> str:
    title = view.display_name
    if sum(1 for candidate in views if candidate.display_name == title) > 1:
        wallet_hint = view.user_id if len(view.user_id) <= 12 else f"{view.user_id[:8]}…"
        return f"{title} ({wallet_hint})"
    return title


def format_portfolio_message(views, view, markdown: bool = True) -> str:
    _, bold, code = pretty_printer.get_markers(markdown)
    title = automation_title(views, view)
    header = f"{bold}{title}{bold}{interfaces.EOL}"
    asset_groups = view.automation.assets
    if not asset_groups:
        return f"{header}{code}No portfolio data.{code}"
    lines = [header]
    for asset_group in asset_groups:
        if asset_group.assets:
            for asset in asset_group.assets:
                lines.append(
                    f"{code}{asset.symbol}: {asset.total} (available {asset.available}){code}"
                    f"{interfaces.EOL}"
                )
    if len(lines) == 1:
        return f"{header}{code}No portfolio data.{code}"
    return "".join(lines)


def format_open_orders_message(views, view, markdown: bool = True) -> str:
    _, bold, code = pretty_printer.get_markers(markdown)
    title = automation_title(views, view)
    header = f"{bold}{title}{bold} {code}Open orders:{code}{interfaces.EOL}"
    if not view.orders:
        return f"{header}{code}No open order yet.{code}"
    exchange_name = (view.automation.exchanges or ["exchange"])[0].capitalize()
    lines = [header]
    for order in view.orders:
        lines.append(
            f"{code}{exchange_name} {order.symbol} {order.side.value} "
            f"{order.quantity} @ {order.price}{code}{interfaces.EOL}"
        )
    return "".join(lines)


def format_trades_history_message(views, view, markdown: bool = True) -> str:
    _, bold, code = pretty_printer.get_markers(markdown)
    title = automation_title(views, view)
    header = f"{bold}{title}{bold} {code}Trades:{code}{interfaces.EOL}"
    if not view.trades:
        return f"{header}{code}No trade yet.{code}"
    lines = [header]
    for trade in view.trades:
        lines.append(
            f"{code}{trade.symbol} {trade.side.value} {trade.quantity} @ {trade.price}{code}"
            f"{interfaces.EOL}"
        )
    return "".join(lines)


def format_fees_message(views, view, markdown: bool = True) -> str:
    _, bold, _ = pretty_printer.get_markers(markdown)
    title = automation_title(views, view)
    header = f"{bold}{title}{bold}{interfaces.EOL}"
    if not view.fees_by_currency:
        return f"{header}No paid fees recorded for this automation."
    return (
        f"{header}Paid fees: "
        f"{pretty_printer.pretty_print_dict(view.fees_by_currency, markdown=markdown)}"
    )