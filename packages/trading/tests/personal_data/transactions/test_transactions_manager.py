#  Drakkar-Software OctoBot
#  Copyright (c) Drakkar-Software, All rights reserved.
#
#  This library is free software; you can redistribute it and/or
#  modify it under the terms of the GNU Lesser General Public
#  License as published by the Free Software Foundation; either
#  version 3.0 of the License, or (at your option) any later version.
#
#  This library is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#  Lesser General Public License for more details.
#
#  You should have received a copy of the GNU Lesser General Public
#  License along with this library.
import decimal
import uuid

import pytest

import octobot_trading.enums as enums
import octobot_trading.errors as errors
import octobot_trading.constants as constants
import octobot_trading.personal_data.transactions.types as transaction_types

from tests.exchanges import backtesting_trader, backtesting_config, backtesting_exchange_manager, fake_backtesting
from tests import event_loop

# All test coroutines will be treated as marked.
pytestmark = pytest.mark.asyncio

TRANSACTION_SYMBOL = "BTC/USDT"
TRANSACTION_CURRENCY = "BTC"


async def test_initialized(backtesting_trader):
    _, exchange_manager, _ = backtesting_trader
    assert exchange_manager.exchange_personal_data.transactions_manager.is_initialized


async def test_insert_transaction_instance(backtesting_trader):
    _, exchange_manager, _ = backtesting_trader
    assert len(exchange_manager.exchange_personal_data.transactions_manager.transactions) == 0
    t_id = str(uuid.uuid4())
    t_id_2 = str(uuid.uuid4())
    transaction = transaction_types.RealisedPnlTransaction(
        exchange_name=exchange_manager.exchange_name,
        creation_time=exchange_manager.exchange.get_exchange_current_time(),
        transaction_type=enums.TransactionType.REALISED_PNL,
        currency=TRANSACTION_CURRENCY,
        symbol=TRANSACTION_SYMBOL,
        realised_pnl=constants.ZERO,
        closed_quantity=constants.ONE,
        cumulated_closed_quantity=constants.ONE,
        first_entry_time=1,
        average_entry_price=constants.ONE,
        average_exit_price=constants.ONE,
        order_exit_price=constants.ONE,
        leverage=constants.ONE,
        side=enums.PositionSide.SHORT,
        trigger_source=enums.PNLTransactionSource.LIMIT_ORDER)
    transaction.set_transaction_id(t_id)
    transaction_2 = transaction_types.BlockchainTransaction(
        exchange_name=exchange_manager.exchange_name,
        creation_time=exchange_manager.exchange.get_exchange_current_time(),
        currency=TRANSACTION_CURRENCY,
        transaction_type=enums.TransactionType.BLOCKCHAIN_DEPOSIT,
        blockchain_network="Test",
        blockchain_transaction_id=t_id,
        blockchain_transaction_status=enums.BlockchainTransactionStatus.CONFIRMING,
        source_address="0x123456789",
        destination_address=None,
        quantity=decimal.Decimal(50),
        transaction_fee={
            enums.FeePropertyColumns.COST.value: decimal.Decimal(0.1),
            enums.FeePropertyColumns.CURRENCY.value: "BTC"
        }
    )
    transaction_2.set_transaction_id(t_id)

    # succeed to upsert unknown transaction
    assert len(exchange_manager.exchange_personal_data.transactions_manager.transactions) == 0
    exchange_manager.exchange_personal_data.transactions_manager.insert_transaction_instance(transaction)
    assert len(exchange_manager.exchange_personal_data.transactions_manager.transactions) == 1

    # can't add transaction with the same transaction id without replacing it --> DuplicateTransactionIdError
    with pytest.raises(errors.DuplicateTransactionIdError):
        exchange_manager.exchange_personal_data.transactions_manager.insert_transaction_instance(transaction_2)
    assert len(exchange_manager.exchange_personal_data.transactions_manager.transactions) == 1
    assert list(exchange_manager.exchange_personal_data.transactions_manager.transactions.values())[-1] is transaction

    # can replace a transaction with the same transaction id
    exchange_manager.exchange_personal_data.transactions_manager.insert_transaction_instance(transaction_2,
                                                                                             replace_if_exists=True)
    assert len(exchange_manager.exchange_personal_data.transactions_manager.transactions) == 1

    # succeed to upsert a transaction with a new id
    transaction.set_transaction_id(t_id_2)
    exchange_manager.exchange_personal_data.transactions_manager.insert_transaction_instance(transaction)
    assert len(exchange_manager.exchange_personal_data.transactions_manager.transactions) == 2

    # check transaction instances
    assert list(exchange_manager.exchange_personal_data.transactions_manager.transactions.values())[0] is transaction_2
    assert list(exchange_manager.exchange_personal_data.transactions_manager.transactions.values())[-1] is transaction


async def test_get_transaction(backtesting_trader):
    _, exchange_manager, _ = backtesting_trader
    assert len(exchange_manager.exchange_personal_data.transactions_manager.transactions) == 0
    transaction = transaction_types.RealisedPnlTransaction(
        exchange_name=exchange_manager.exchange_name,
        creation_time=exchange_manager.exchange.get_exchange_current_time(),
        transaction_type=enums.TransactionType.REALISED_PNL,
        currency=TRANSACTION_CURRENCY,
        symbol=TRANSACTION_SYMBOL,
        side=enums.PositionSide.BOTH,
        realised_pnl=constants.ZERO,
        closed_quantity=constants.ONE,
        cumulated_closed_quantity=constants.ONE,
        first_entry_time=1,
        average_entry_price=constants.ONE,
        average_exit_price=constants.ONE,
        order_exit_price=constants.ONE,
        leverage=constants.ONE,
        trigger_source=enums.PNLTransactionSource.LIMIT_ORDER)
    transaction_2 = transaction_types.RealisedPnlTransaction(
        exchange_name=exchange_manager.exchange_name,
        creation_time=exchange_manager.exchange.get_exchange_current_time(),
        transaction_type=enums.TransactionType.REALISED_PNL,
        currency=TRANSACTION_CURRENCY,
        symbol=TRANSACTION_SYMBOL,
        side=enums.PositionSide.LONG,
        realised_pnl=constants.ZERO,
        closed_quantity=constants.ONE,
        cumulated_closed_quantity=constants.ONE,
        first_entry_time=1,
        average_entry_price=constants.ONE,
        average_exit_price=constants.ONE,
        order_exit_price=constants.ONE,
        leverage=constants.ONE,
        trigger_source=enums.PNLTransactionSource.LIMIT_ORDER)
    exchange_manager.exchange_personal_data.transactions_manager.insert_transaction_instance(transaction)

    # succeed to return transaction instance
    assert exchange_manager.exchange_personal_data.transactions_manager. \
               get_transaction(transaction.transaction_id) is transaction

    # can't get unknown transaction id
    with pytest.raises(KeyError):
        exchange_manager.exchange_personal_data.transactions_manager.get_transaction(str(uuid.uuid4()))

    # can't get a transaction which has not been added
    with pytest.raises(KeyError):
        exchange_manager.exchange_personal_data.transactions_manager.get_transaction(transaction_2.transaction_id)

    # succeed to return transaction instances
    exchange_manager.exchange_personal_data.transactions_manager.insert_transaction_instance(transaction_2)
    assert exchange_manager.exchange_personal_data.transactions_manager. \
               get_transaction(transaction.transaction_id) is transaction
    assert exchange_manager.exchange_personal_data.transactions_manager. \
               get_transaction(transaction_2.transaction_id) is transaction_2


async def test_update_transaction_id(backtesting_trader):
    _, exchange_manager, _ = backtesting_trader
    t_id = str(uuid.uuid4())
    t_id_2 = str(uuid.uuid4())
    t_id_3 = str(uuid.uuid4())
    t_id_4 = str(uuid.uuid4())
    assert len(exchange_manager.exchange_personal_data.transactions_manager.transactions) == 0
    transaction = transaction_types.RealisedPnlTransaction(
        exchange_name=exchange_manager.exchange_name,
        creation_time=exchange_manager.exchange.get_exchange_current_time(),
        transaction_type=enums.TransactionType.REALISED_PNL,
        currency=TRANSACTION_CURRENCY,
        symbol=TRANSACTION_SYMBOL,
        side=enums.PositionSide.BOTH,
        realised_pnl=constants.ZERO,
        closed_quantity=constants.ONE,
        cumulated_closed_quantity=constants.ONE,
        first_entry_time=1,
        average_entry_price=constants.ONE,
        average_exit_price=constants.ONE,
        order_exit_price=constants.ONE,
        leverage=constants.ONE,
        trigger_source=enums.PNLTransactionSource.LIMIT_ORDER)
    transaction.set_transaction_id(t_id)
    transaction_2 = transaction_types.RealisedPnlTransaction(
        exchange_name=exchange_manager.exchange_name,
        creation_time=exchange_manager.exchange.get_exchange_current_time(),
        transaction_type=enums.TransactionType.REALISED_PNL,
        currency=TRANSACTION_CURRENCY,
        symbol=TRANSACTION_SYMBOL,
        side=enums.PositionSide.SHORT,
        realised_pnl=constants.ZERO,
        closed_quantity=constants.ONE,
        cumulated_closed_quantity=constants.ONE,
        first_entry_time=1,
        average_entry_price=constants.ONE,
        average_exit_price=constants.ONE,
        order_exit_price=constants.ONE,
        leverage=constants.ONE,
        trigger_source=enums.PNLTransactionSource.LIMIT_ORDER)
    transaction_2.set_transaction_id(t_id_2)

    # Add transaction instances to TransactionsManager.transactions
    exchange_manager.exchange_personal_data.transactions_manager.insert_transaction_instance(transaction)
    assert len(exchange_manager.exchange_personal_data.transactions_manager.transactions) == 1
    exchange_manager.exchange_personal_data.transactions_manager.insert_transaction_instance(transaction_2)
    assert len(exchange_manager.exchange_personal_data.transactions_manager.transactions) == 2

    # Update the first transaction id and see if the previous entry was properly deleted
    exchange_manager.exchange_personal_data.transactions_manager.update_transaction_id(t_id, t_id_3)
    assert len(exchange_manager.exchange_personal_data.transactions_manager.transactions) == 2
    assert transaction.transaction_id == t_id_3
    assert list(exchange_manager.exchange_personal_data.transactions_manager.transactions.values())[-1] is transaction
    assert list(exchange_manager.exchange_personal_data.transactions_manager.transactions.values())[-1].transaction_id \
           == t_id_3

    # ensure that the first transaction_id doesn't exist anymore
    with pytest.raises(KeyError):
        exchange_manager.exchange_personal_data.transactions_manager.get_transaction(t_id)

    # try to update with an already used transaction id without replacing it
    with pytest.raises(errors.DuplicateTransactionIdError):
        exchange_manager.exchange_personal_data.transactions_manager.update_transaction_id(t_id_2, t_id_3)

    # check if the transaction keeps its old transaction id
    assert transaction_2.transaction_id == t_id_2

    # check if transaction_2 was not dropped from the list
    assert len(exchange_manager.exchange_personal_data.transactions_manager.transactions) == 2
    exchange_manager.exchange_personal_data.transactions_manager.get_transaction(t_id_2)

    # try to update with an already used transaction id with replacement
    exchange_manager.exchange_personal_data.transactions_manager.update_transaction_id(t_id_2, t_id_3,
                                                                                       replace_if_exists=True)
    assert len(exchange_manager.exchange_personal_data.transactions_manager.transactions) == 1  # transaction replaced by transaction_2
    assert transaction_2.transaction_id == t_id_3
    assert list(exchange_manager.exchange_personal_data.transactions_manager.transactions.values())[-1] is transaction_2
    assert list(exchange_manager.exchange_personal_data.transactions_manager.transactions.values())[
               -1].transaction_id == t_id_3

    # try to update an unknown transaction
    with pytest.raises(KeyError):
        exchange_manager.exchange_personal_data.transactions_manager.update_transaction_id(str(uuid.uuid4()),
                                                                                           str(uuid.uuid4()))
    assert len(exchange_manager.exchange_personal_data.transactions_manager.transactions) == 1

    # restore transaction in list
    transaction.set_transaction_id(t_id_4)
    exchange_manager.exchange_personal_data.transactions_manager.insert_transaction_instance(transaction)
    assert len(exchange_manager.exchange_personal_data.transactions_manager.transactions) == 2
