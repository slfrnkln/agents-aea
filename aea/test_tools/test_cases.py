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

"""This module contains test case classes based on pytest for AEA end-to-end testing."""

import os
import shutil
import subprocess  # nosec
import sys
import tempfile
from typing import Any, List

import pytest

from aea.cli import cli
from aea.cli_gui import DEFAULT_AUTHOR
from aea.configurations.constants import DEFAULT_REGISTRY_PATH
from aea.test_tools.click_testing import CliRunner
from aea.test_tools.exceptions import AEATestingException

CLI_LOG_OPTION = ["-v", "OFF"]


class AEATestCase:
    """Test case for AEA end-to-end tests."""

    author: str  # author name
    cwd: str  # current working directory path
    runner: CliRunner  # CLI runner
    subprocesses: List  # list of launched subprocesses
    t: str  # temporary directory path

    @classmethod
    def setup_class(cls, packages_dir_path=DEFAULT_REGISTRY_PATH):
        """Set up the test class."""
        cls.runner = CliRunner()
        cls.cwd = os.getcwd()
        cls.t = tempfile.mkdtemp()

        # add packages folder
        packages_src = os.path.join(cls.cwd, packages_dir_path)
        packages_dst = os.path.join(cls.t, packages_dir_path)
        shutil.copytree(packages_src, packages_dst)

        cls.subprocesses = []
        cls.author = DEFAULT_AUTHOR

        os.chdir(cls.t)

    @classmethod
    def teardown_class(cls):
        """Teardown the test."""
        cls._terminate_subprocesses()

        os.chdir(cls.cwd)
        try:
            shutil.rmtree(cls.t)
        except (OSError, IOError):
            pass

    @classmethod
    def _terminate_subprocesses(cls):
        """Terminate all launched subprocesses."""
        for process in cls.subprocesses:
            if not process.returncode == 0:
                poll = process.poll()
                if poll is None:
                    process.terminate()
                    process.wait(2)

    def set_config(self, dotted_path: str, value: Any) -> None:
        """
        Set a config.
        Run from agent's directory.

        :param dotted_path: str dotted path to config param.
        :param value: a new value to set.

        :return: None
        """
        self.run_cli_command("config", "set", dotted_path, str(value))

    def disable_ledger_tx(self, author: str, item_type: str, item_name: str) -> None:
        """
        Disable ledger tx by modifying item yaml settings.
        Run from agent's directory and only for item with present strategy is_ledger_tx setting.

        :param author: str author name (equals to a vendor folder name).
        :param item_type: str item type.
        :param item_name: str item name.

        :return: None
        """
        dotted_path = "vendor.{}.{}s.{}.models.strategy.args.is_ledger_tx".format(
            author, item_type, item_name
        )
        self.set_config(dotted_path, False)

    def disable_aea_logging(self):
        """
        Disable AEA logging of specific agent.
        Run from agent's directory.

        :return: None
        """
        config_update_dict = {
            "agent.logging_config.disable_existing_loggers": "False",
            "agent.logging_config.version": "1",
        }
        for path, value in config_update_dict.items():
            self.run_cli_command("config", "set", path, value)

    def run_cli_command(self, *args: str) -> None:
        """
        Run AEA CLI command.

        :param args: CLI args
        :raises AEATestingException: if command fails.

        :return: None
        """
        result = self.runner.invoke(
            cli, [*CLI_LOG_OPTION, *args], standalone_mode=False
        )
        if result.exit_code != 0:
            raise AEATestingException(
                "Failed to execute AEA CLI command with args {}.\n"
                "Exit code: {}\nException: {}".format(
                    args, result.exit_code, result.exception
                )
            )

    def _run_python_subprocess(self, *args: str) -> subprocess.Popen:
        """
        Run python with args as subprocess.

        :param *args: CLI args

        :return: subprocess object.
        """
        process = subprocess.Popen(  # nosec
            [sys.executable, *args], stdout=subprocess.PIPE, env=os.environ.copy(),
        )
        self.subprocesses.append(process)
        return process

    def run_agent(self, *args: str) -> subprocess.Popen:
        """
        Run agent as subprocess.
        Run from agent's directory.

        :param *args: CLI args

        :return: subprocess object.
        """
        return self._run_python_subprocess("-m", "aea.cli", "run", *args)

    def initialize_aea(self, author=None) -> None:
        """
        Initialize AEA locally with author name.

        :return: None
        """
        if author is None:
            author = self.author
        self.run_cli_command("init", "--local", "--author", author)

    def create_agents(self, *agents_names: str) -> None:
        """
        Create agents in current working directory.

        :param *agents_names: str agent names.

        :return: None
        """
        for name in agents_names:
            self.run_cli_command("create", "--local", name, "--author", self.author)

    def delete_agents(self, *agents_names: str) -> None:
        """
        Delete agents in current working directory.

        :param *agents_names: str agent names.

        :return: None
        """
        for name in agents_names:
            self.run_cli_command("delete", name)

    def add_item(self, item_type: str, public_id: str) -> None:
        """
        Add an item to the agent.
        Run from agent's directory.

        :param item_type: str item type.
        :param item_type: str item type.

        :return: None
        """
        self.run_cli_command("add", "--local", item_type, public_id)

    def run_install(self):
        """
        Execute AEA CLI install command.
        Run from agent's directory.

        :return: None
        """
        self.run_cli_command("install")


class AEAWithOefTestCase(AEATestCase):
    @pytest.fixture(autouse=True)
    def _start_oef_node(self, network_node):
        """Start an oef node."""

    def run_agent_with_oef(self) -> subprocess.Popen:
        """
        Run agent with OEF connection as subprocess.
        Run from agent's directory.

        :param *args: CLI args

        :return: subprocess object.
        """
        return self.run_agent("--connections", "fetchai/oef:0.1.0")