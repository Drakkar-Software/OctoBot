import typing

import octobot_commons.timestamp_util as timestamp_util
import octobot_protocol.models as protocol_models

REFERENCE_ACCOUNT_SUMMARY_LIMIT = 10


def format_reference_account_summary(reference_account: protocol_models.CopiedAccount) -> str:
    copied_assets = reference_account.copied_assets
    order_list = reference_account.orders or []
    asset_entries = [_format_copied_asset_entry(copied_asset) for copied_asset in copied_assets]
    assets_summary = _format_compact_section("assets", asset_entries, len(copied_assets))
    orders_summary = _format_orders_section(order_list)
    updated_at = _format_reference_account_updated_at(reference_account.updated_at)
    return f"v{reference_account.version}@{updated_at} {assets_summary} {orders_summary}"


def _format_reference_account_updated_at(updated_at: typing.Union[float, int]) -> str:
    formatted_time = timestamp_util.convert_timestamp_to_datetime(
        float(updated_at),
        local_timezone=False,
    )
    return f"{formatted_time} UTC"


def _format_copied_asset_entry(asset: protocol_models.CopiedAsset) -> str:
    ratio_percent = float(asset.ratio) * 100
    return f"{asset.name}:{ratio_percent:.1f}%"


def _format_reference_order_entry(order: protocol_models.Order) -> str:
    return f"{order.side.value} {order.symbol}@{order.price}"


def _format_order_type_label(order: protocol_models.Order) -> str:
    return f"{order.side.value}_{order.type.value}"


def _format_order_type_count_label(orders: list[protocol_models.Order]) -> str:
    if not orders:
        return "0"
    order_type_counts: dict[str, int] = {}
    for order in orders:
        order_type_label = _format_order_type_label(order)
        order_type_counts[order_type_label] = order_type_counts.get(order_type_label, 0) + 1
    return ",".join(
        f"{order_type_counts[order_type_label]} {order_type_label}"
        for order_type_label in sorted(order_type_counts)
    )


def _format_orders_section(order_list: list[protocol_models.Order]) -> str:
    order_type_count_label = _format_order_type_count_label(order_list)
    if not order_list:
        return "orders[0]"
    order_entries = [_format_reference_order_entry(order) for order in order_list]
    content = _format_compact_list(order_entries, len(order_list))
    return f"orders[{order_type_count_label}]:{content}"


def _format_compact_list(entries: list[str], total_count: int) -> str:
    if total_count == 0:
        return ""
    displayed_entries = entries[:REFERENCE_ACCOUNT_SUMMARY_LIMIT]
    content = ",".join(displayed_entries)
    remaining_count = total_count - len(displayed_entries)
    if remaining_count > 0:
        content = f"{content},…+{remaining_count} more"
    return content


def _format_compact_section(section_name: str, entries: list[str], total_count: int) -> str:
    if total_count == 0:
        return f"{section_name}[0]"
    content = _format_compact_list(entries, total_count)
    return f"{section_name}[{total_count}]:{content}"
