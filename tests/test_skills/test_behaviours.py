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

"""This module contains the tests for the behaviours."""
from collections import Counter

import pytest

from aea.skills.behaviours import (
    FSMBehaviour,
    OneShotBehaviour,
    SequenceBehaviour,
    State,
)


def test_sequence_behaviour():
    """Test the sequence behaviour."""
    outputs = []

    class MySequenceBehaviour(SequenceBehaviour):
        def setup(self) -> None:
            pass

        def teardown(self) -> None:
            pass

    class SimpleOneShotBehaviour(OneShotBehaviour):
        def __init__(self, name, **kwargs):
            super().__init__(name=name, **kwargs)

        def setup(self) -> None:
            pass

        def teardown(self) -> None:
            pass

        def act(self) -> None:
            outputs.append(self.name)

    # TODO let the initialization of a behaviour action from constructor
    a = SimpleOneShotBehaviour("a", skill_context=object())
    b = SimpleOneShotBehaviour("b", skill_context=object())
    c = SimpleOneShotBehaviour("c", skill_context=object())
    sequence = MySequenceBehaviour([a, b, c], name="abc", skill_context=object())

    max_iterations = 10
    i = 0
    while not sequence.is_done() and i < max_iterations:
        sequence.act()
        i += 1

    assert outputs == ["a", "b", "c"]


def test_act_parameter():
    """Test the 'act' parameter."""
    counter = Counter(i=0)

    def increment_counter(counter=counter):
        counter += Counter(i=1)

    assert counter["i"] == 0

    one_shot_behaviour = OneShotBehaviour(
        act=lambda: increment_counter(), skill_context=object(), name="my_behaviour"
    )
    one_shot_behaviour.act()
    assert counter["i"] == 1


class SimpleFSMBehaviour(FSMBehaviour):
    """A Finite-State Machine behaviour for testing purposes."""

    def setup(self) -> None:
        pass

    def teardown(self) -> None:
        pass


class SimpleStateBehaviour(State):
    """A simple state behaviour to be added in a FSMBehaviour."""

    def __init__(self, shared_list, event_to_trigger=None, **kwargs):
        super().__init__(**kwargs)
        self.shared_list = shared_list
        self.event_to_trigger = event_to_trigger
        self.executed = False

    def setup(self) -> None:
        pass

    def teardown(self) -> None:
        pass

    def act(self) -> None:
        self.shared_list.append(self.name)
        self.executed = True
        self._event = self.event_to_trigger

    def is_done(self) -> bool:
        return self.executed


def test_fms_behaviour():
    """Test the finite-state machine behaviour."""
    outputs = []

    a = SimpleStateBehaviour(
        outputs, name="a", event_to_trigger="move_to_b", skill_context=object()
    )
    b = SimpleStateBehaviour(
        outputs, name="b", event_to_trigger="move_to_c", skill_context=object()
    )
    c = SimpleStateBehaviour(outputs, name="c", skill_context=object())
    fsm = SimpleFSMBehaviour(name="abc", skill_context=object())
    fsm.register_state(str(a.name), a, initial=True)
    fsm.register_state(str(b.name), b)
    fsm.register_final_state(str(c.name), c)
    fsm.register_transition("a", "b", "move_to_b")
    fsm.register_transition("b", "c", "move_to_c")

    max_iterations = 10
    i = 0
    while not fsm.is_done() and i < max_iterations:
        fsm.act()
        i += 1

    assert outputs == ["a", "b", "c"]


class TestFSMBehaviourCreation:
    @classmethod
    def setup_class(cls):
        """Set the test up."""
        cls.fsm_behaviour = SimpleFSMBehaviour(name="fsm", skill_context=object())
        cls.outputs = []
        cls.a = SimpleStateBehaviour(cls.outputs, name="a", skill_context=object())
        cls.b = SimpleStateBehaviour(cls.outputs, name="b", skill_context=object())
        cls.c = SimpleStateBehaviour(cls.outputs, name="c", skill_context=object())

    def test_initial_state_is_none(self):
        """Test that the initial state is None."""
        assert self.fsm_behaviour.initial_state is None

    def test_states_is_empty(self):
        """Test that the states is an empty set."""
        assert self.fsm_behaviour.states == set()

    def test_final_states_is_empty(self):
        """Test that the final states is an empty set."""
        assert self.fsm_behaviour.final_states == set()

    def test_add_and_remove_state(self):
        """Test that adding and removing a state works correctly."""
        assert self.fsm_behaviour.states == set()
        self.fsm_behaviour.register_state("a", self.a)
        assert self.fsm_behaviour.states == {"a"}
        self.fsm_behaviour.unregister_state("a")
        assert self.fsm_behaviour.states == set()

    def test_add_and_remove_initial_state(self):
        """Test that adding and removing an initial state works correctly."""
        assert self.fsm_behaviour.states == set()
        self.fsm_behaviour.register_state("a", self.a, initial=True)
        assert self.fsm_behaviour.states == {"a"}
        assert self.fsm_behaviour.initial_state == "a"
        assert self.fsm_behaviour.final_states == set()
        self.fsm_behaviour.unregister_state("a")
        assert self.fsm_behaviour.states == set()
        assert self.fsm_behaviour.initial_state is None
        assert self.fsm_behaviour.final_states == set()

    def test_add_and_remove_final_state(self):
        """Test that adding and removing final states works correctly."""
        assert self.fsm_behaviour.states == set()
        self.fsm_behaviour.register_final_state("a", self.a)
        assert self.fsm_behaviour.states == {"a"}
        assert self.fsm_behaviour.initial_state is None
        assert self.fsm_behaviour.final_states == {"a"}
        self.fsm_behaviour.unregister_state("a")
        assert self.fsm_behaviour.states == set()
        assert self.fsm_behaviour.initial_state is None
        assert self.fsm_behaviour.final_states == set()

    def test_register_initial_state_twice(self):
        """Test that the register state with initial=True works correctly when called twice."""
        assert self.fsm_behaviour.initial_state is None
        self.fsm_behaviour.register_state("a", self.a, initial=True)
        assert self.fsm_behaviour.initial_state == "a"
        self.fsm_behaviour.register_state("b", self.b, initial=True)
        assert self.fsm_behaviour.initial_state == "b"
        self.fsm_behaviour.unregister_state("a")
        self.fsm_behaviour.unregister_state("b")
        assert self.fsm_behaviour.initial_state is None

    def test_register_twice_same_state(self):
        """Test that registering twice a state with the same name raises an error."""
        self.fsm_behaviour.register_state("a", self.a)
        with pytest.raises(ValueError, match="State name already existing."):
            self.fsm_behaviour.register_state("a", self.a)
        self.fsm_behaviour.unregister_state("a")

    def test_register_transition(self):
        """Test register transition."""
        self.fsm_behaviour.register_transition("state_1", "state_2")
        self.fsm_behaviour.register_transition("state_1", "state_2", "an_event")
        assert self.fsm_behaviour.transitions == {
            "state_1": {None: "state_2", "an_event": "state_2"}
        }
        self.fsm_behaviour.unregister_transition("state_1", "state_2", None)
        self.fsm_behaviour.unregister_transition("state_1", "state_2", "an_event")
        assert self.fsm_behaviour.transitions == dict()

    def test_register_same_transition_twice(self):
        """Test that when we try to register twice the same transition we raise an error."""
        self.fsm_behaviour.register_transition("state_1", "state_2")
        with pytest.raises(ValueError, match="Transition already registered."):
            self.fsm_behaviour.register_transition("state_1", "state_2")
        self.fsm_behaviour.unregister_transition("state_1", "state_2")

        self.fsm_behaviour.register_transition("state_1", "state_2", "an_event")
        with pytest.raises(ValueError, match="Transition already registered."):
            self.fsm_behaviour.register_transition("state_1", "state_2", "an_event")
        self.fsm_behaviour.unregister_transition("state_1", "state_2", "an_event")
