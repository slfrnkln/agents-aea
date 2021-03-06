# -*- coding: utf-8 -*-
# ------------------------------------------------------------------------------
#
#   Copyright 2018-2019 Fetch.AI Limited
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
#
# ------------------------------------------------------------------------------

"""This module contains the handler for the 'ml_data_provider' skill."""

import pickle  # nosec
from typing import Optional, cast

from aea.configurations.base import ProtocolId
from aea.protocols.base import Message
from aea.protocols.default.message import DefaultMessage
from aea.skills.base import Handler

from packages.fetchai.protocols.ledger_api.message import LedgerApiMessage
from packages.fetchai.protocols.ml_trade.message import MlTradeMessage
from packages.fetchai.skills.ml_data_provider.dialogues import (
    DefaultDialogues,
    LedgerApiDialogue,
    LedgerApiDialogues,
    MlTradeDialogue,
    MlTradeDialogues,
)
from packages.fetchai.skills.ml_data_provider.strategy import Strategy


class MlTradeHandler(Handler):
    """ML trade handler."""

    SUPPORTED_PROTOCOL = MlTradeMessage.protocol_id

    def setup(self) -> None:
        """Set up the handler."""
        pass

    def handle(self, message: Message) -> None:
        """
        Implement the reaction to a message.

        :param message: the message
        :return: None
        """
        ml_trade_msg = cast(MlTradeMessage, message)

        # recover dialogue
        ml_trade_dialogues = cast(MlTradeDialogues, self.context.ml_trade_dialogues)
        ml_trade_dialogue = cast(
            MlTradeDialogue, ml_trade_dialogues.update(ml_trade_msg)
        )
        if ml_trade_dialogue is None:
            self._handle_unidentified_dialogue(ml_trade_msg)
            return

        # handle message
        if ml_trade_msg.performative == MlTradeMessage.Performative.CFP:
            self._handle_cft(ml_trade_msg, ml_trade_dialogue)
        elif ml_trade_msg.performative == MlTradeMessage.Performative.ACCEPT:
            self._handle_accept(ml_trade_msg, ml_trade_dialogue)
        else:
            self._handle_invalid(ml_trade_msg, ml_trade_dialogue)

    def teardown(self) -> None:
        """
        Teardown the handler.

        :return: None
        """
        pass

    def _handle_unidentified_dialogue(self, ml_trade_msg: MlTradeMessage) -> None:
        """
        Handle an unidentified dialogue.

        :param fipa_msg: the message
        """
        self.context.logger.info(
            "[{}]: received invalid ml_trade message={}, unidentified dialogue.".format(
                self.context.agent_name, ml_trade_msg
            )
        )
        default_dialogues = cast(DefaultDialogues, self.context.default_dialogues)
        default_msg = DefaultMessage(
            performative=DefaultMessage.Performative.ERROR,
            dialogue_reference=default_dialogues.new_self_initiated_dialogue_reference(),
            error_code=DefaultMessage.ErrorCode.INVALID_DIALOGUE,
            error_msg="Invalid dialogue.",
            error_data={"ml_trade_message": ml_trade_msg.encode()},
        )
        default_msg.counterparty = ml_trade_msg.counterparty
        default_dialogues.update(default_msg)
        self.context.outbox.put_message(message=default_msg)

    def _handle_cft(
        self, ml_trade_msg: MlTradeMessage, ml_trade_dialogue: MlTradeDialogue
    ) -> None:
        """
        Handle call for terms.

        :param ml_trade_msg: the ml trade message
        :param ml_trade_dialogue: the dialogue object
        :return: None
        """
        query = ml_trade_msg.query
        self.context.logger.info(
            "Got a Call for Terms from {}.".format(ml_trade_msg.counterparty[-5:])
        )
        strategy = cast(Strategy, self.context.strategy)
        if not strategy.is_matching_supply(query):
            self.context.logger.info(
                "[{}]: query does not match supply.".format(self.context.agent_name)
            )
            return
        terms = strategy.generate_terms()
        self.context.logger.info(
            "[{}]: sending to the address={} a Terms message: {}".format(
                self.context.agent_name, ml_trade_msg.counterparty[-5:], terms.values
            )
        )
        terms_msg = MlTradeMessage(
            performative=MlTradeMessage.Performative.TERMS,
            dialogue_reference=ml_trade_dialogue.dialogue_label.dialogue_reference,
            message_id=ml_trade_msg.message_id + 1,
            target=ml_trade_msg.message_id,
            terms=terms,
        )
        terms_msg.counterparty = ml_trade_msg.counterparty
        ml_trade_dialogue.update(terms_msg)
        self.context.outbox.put_message(message=terms_msg)

    def _handle_accept(
        self, ml_trade_msg: MlTradeMessage, ml_trade_dialogue: MlTradeDialogue
    ) -> None:
        """
        Handle accept.

        :param ml_trade_msg: the ml trade message
        :param ml_trade_dialogue: the dialogue object
        :return: None
        """
        terms = ml_trade_msg.terms
        self.context.logger.info(
            "Got an Accept from {}: {}".format(
                ml_trade_msg.counterparty[-5:], terms.values
            )
        )
        strategy = cast(Strategy, self.context.strategy)
        if not strategy.is_valid_terms(terms):
            self.context.logger.info(
                "[{}]: terms are not valid.".format(self.context.agent_name)
            )
            return
        data = strategy.sample_data(terms.values["batch_size"])
        self.context.logger.info(
            "[{}]: sending to address={} a Data message: shape={}".format(
                self.context.agent_name, ml_trade_msg.counterparty[-5:], data[0].shape
            )
        )
        payload = pickle.dumps(data)  # nosec
        data_msg = MlTradeMessage(
            performative=MlTradeMessage.Performative.DATA,
            dialogue_reference=ml_trade_dialogue.dialogue_label.dialogue_reference,
            message_id=ml_trade_msg.message_id + 1,
            target=ml_trade_msg.message_id,
            terms=terms,
            payload=payload,
        )
        data_msg.counterparty = ml_trade_msg.counterparty
        ml_trade_dialogue.update(data_msg)
        self.context.outbox.put_message(message=data_msg)

    def _handle_invalid(
        self, ml_trade_msg: MlTradeMessage, ml_trade_dialogue: MlTradeDialogue
    ) -> None:
        """
        Handle a fipa message of invalid performative.

        :param ml_trade_msg: the message
        :param ml_trade_dialogue: the dialogue object
        :return: None
        """
        self.context.logger.warning(
            "[{}]: cannot handle ml_trade message of performative={} in dialogue={}.".format(
                self.context.agent_name, ml_trade_msg.performative, ml_trade_dialogue
            )
        )


class LedgerApiHandler(Handler):
    """Implement the ledger handler."""

    SUPPORTED_PROTOCOL = LedgerApiMessage.protocol_id  # type: Optional[ProtocolId]

    def setup(self) -> None:
        """Implement the setup for the handler."""
        pass

    def handle(self, message: Message) -> None:
        """
        Implement the reaction to a message.

        :param message: the message
        :return: None
        """
        ledger_api_msg = cast(LedgerApiMessage, message)

        # recover dialogue
        ledger_api_dialogues = cast(
            LedgerApiDialogues, self.context.ledger_api_dialogues
        )
        ledger_api_dialogue = cast(
            Optional[LedgerApiDialogue], ledger_api_dialogues.update(ledger_api_msg)
        )
        if ledger_api_dialogue is None:
            self._handle_unidentified_dialogue(ledger_api_msg)
            return

        # handle message
        if ledger_api_msg.performative is LedgerApiMessage.Performative.BALANCE:
            self._handle_balance(ledger_api_msg, ledger_api_dialogue)
        elif ledger_api_msg.performative == LedgerApiMessage.Performative.ERROR:
            self._handle_error(ledger_api_msg, ledger_api_dialogue)
        else:
            self._handle_invalid(ledger_api_msg, ledger_api_dialogue)

    def teardown(self) -> None:
        """
        Implement the handler teardown.

        :return: None
        """
        pass

    def _handle_unidentified_dialogue(self, ledger_api_msg: LedgerApiMessage) -> None:
        """
        Handle an unidentified dialogue.

        :param msg: the message
        """
        self.context.logger.info(
            "[{}]: received invalid ledger_api message={}, unidentified dialogue.".format(
                self.context.agent_name, ledger_api_msg
            )
        )

    def _handle_balance(
        self, ledger_api_msg: LedgerApiMessage, ledger_api_dialogue: LedgerApiDialogue
    ) -> None:
        """
        Handle a message of balance performative.

        :param ledger_api_message: the ledger api message
        :param ledger_api_dialogue: the ledger api dialogue
        """
        self.context.logger.info(
            "[{}]: starting balance on {} ledger={}.".format(
                self.context.agent_name,
                ledger_api_msg.ledger_id,
                ledger_api_msg.balance,
            )
        )

    def _handle_error(
        self, ledger_api_msg: LedgerApiMessage, ledger_api_dialogue: LedgerApiDialogue
    ) -> None:
        """
        Handle a message of error performative.

        :param ledger_api_message: the ledger api message
        :param ledger_api_dialogue: the ledger api dialogue
        """
        self.context.logger.info(
            "[{}]: received ledger_api error message={} in dialogue={}.".format(
                self.context.agent_name, ledger_api_msg, ledger_api_dialogue
            )
        )

    def _handle_invalid(
        self, ledger_api_msg: LedgerApiMessage, ledger_api_dialogue: LedgerApiDialogue
    ) -> None:
        """
        Handle a message of invalid performative.

        :param ledger_api_message: the ledger api message
        :param ledger_api_dialogue: the ledger api dialogue
        """
        self.context.logger.warning(
            "[{}]: cannot handle ledger_api message of performative={} in dialogue={}.".format(
                self.context.agent_name,
                ledger_api_msg.performative,
                ledger_api_dialogue,
            )
        )
