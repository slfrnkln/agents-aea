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

"""The base connection package."""
from abc import abstractmethod, ABC
from asyncio import AbstractEventLoop
from typing import TYPE_CHECKING, Optional

from aea.configurations.base import ConnectionConfig

if TYPE_CHECKING:
    from aea.mail.base import Envelope  # pragma: no cover


class ConnectionStatus(object):
    """The connection status class."""

    def __init__(self):
        """Initialize the connection status."""
        self.is_connected = False


class Connection(ABC):
    """Abstract definition of a connection."""

    def __init__(self, connection_id: str):
        """
        Initialize the connection.

        :param connection_id: the connection identifier.
        """
        self._connection_id = connection_id

        self._loop = None  # type: Optional[AbstractEventLoop]
        self._connection_status = ConnectionStatus()

    @property
    def loop(self) -> Optional[AbstractEventLoop]:
        """Get the event loop."""
        return self._loop

    @loop.setter
    def loop(self, loop: AbstractEventLoop) -> None:
        """
        Set the event loop.

        :param loop: the event loop.
        :return: None
        """
        assert self._loop is None or not self._loop.is_running(), "Cannot set the loop while it is running."
        self._loop = loop

    @property
    def connection_id(self) -> str:
        """Get the id of the connection."""
        return self._connection_id

    @property
    def connection_status(self) -> ConnectionStatus:
        """Get the connection status."""
        return self._connection_status

    @abstractmethod
    async def connect(self):
        """Set up the connection."""

    @abstractmethod
    async def disconnect(self):
        """Tear down the connection."""

    @abstractmethod
    async def send(self, envelope: 'Envelope') -> None:
        """
        Send an envelope.

        :param envelope: the envelope to send.
        :return: None
        """

    @abstractmethod
    async def receive(self, *args, **kwargs) -> Optional['Envelope']:
        """
        Receive an envelope.

        :return: the received envelope, or None if an error occurred.
        """

    @classmethod
    @abstractmethod
    def from_config(cls, public_key: str, connection_configuration: ConnectionConfig) -> 'Connection':
        """
        Initialize a connection instance from a configuration.

        :param public_key: the public key of the agent.
        :param connection_configuration: the connection configuration.
        :return: an instance of the concrete connection class.
        """