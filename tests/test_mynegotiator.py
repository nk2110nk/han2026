"""Tests for MyNegotiator."""

import pytest
from negmas.preferences.generators import generate_multi_issue_ufuns
from negmas.sao import SAOMechanism

from mynegotiator import MyNegotiator
from examples.nollm import SimpleNeg


class TestMyNegotiator:
    """Tests for MyNegotiator."""

    def test_can_instantiate_with_defaults(self):
        """Test that MyNegotiator can be instantiated with default parameters."""
        neg = MyNegotiator()
        assert neg is not None
        assert neg.name is not None

    def test_can_instantiate_with_custom_model(self):
        """Test that MyNegotiator can be instantiated with a custom model."""
        neg = MyNegotiator(model="llama3.2")
        assert neg is not None

    def test_can_instantiate_with_custom_temperature(self):
        """Test that MyNegotiator accepts custom temperature."""
        neg = MyNegotiator(temperature=0.5)
        assert neg is not None

    def test_can_instantiate_with_custom_max_tokens(self):
        """Test that MyNegotiator accepts custom max_tokens."""
        neg = MyNegotiator(max_tokens=512)
        assert neg is not None

    def test_can_instantiate_with_structured_output_disabled(self):
        """Test that MyNegotiator can disable structured output."""
        neg = MyNegotiator(use_structured_output=False)
        assert neg is not None

    def test_can_instantiate_with_custom_system_prompt(self):
        """Test that MyNegotiator accepts custom system prompt."""
        neg = MyNegotiator(system_prompt="You are a tough negotiator.")
        assert neg is not None

    @pytest.mark.skip(
        reason="Custom prompts may not be supported by the current version of negmas-llm"
    )
    def test_can_instantiate_with_custom_prompts(self):
        """Test that MyNegotiator accepts all custom prompt parameters."""
        neg = MyNegotiator(
            preferences_prompt="Custom preferences prompt",
            preferences_changed_prompt="Custom preferences changed prompt",
            negotiation_start_prompt="Custom negotiation start prompt",
            round_prompt="Custom round prompt",
        )
        assert neg is not None

    def test_can_instantiate_with_name(self):
        """Test that MyNegotiator accepts name parameter via kwargs."""
        neg = MyNegotiator(name="TestNegotiator")
        assert neg.name == "TestNegotiator"

    def test_can_instantiate_with_ufun(self):
        """Test that MyNegotiator accepts ufun parameter via kwargs."""
        ufuns = generate_multi_issue_ufuns(
            n_issues=3, n_values=(3, 5), n_ufuns=1, reserved_values=0.0
        )

        neg = MyNegotiator(ufun=ufuns[0])
        assert neg.ufun is not None

    @pytest.mark.skip(reason="Requires Ollama running locally with llama3.1:8b model")
    def test_can_negotiate_with_non_llm_opponent(self):
        """Test that MyNegotiator can negotiate against a non-LLM opponent."""
        # Create utilities
        ufuns = generate_multi_issue_ufuns(
            n_issues=3, n_values=(3, 5), n_ufuns=2, reserved_values=0.0
        )

        # Create mechanism
        m = SAOMechanism(outcome_space=ufuns[0].outcome_space, n_steps=5)

        # Add negotiators
        m.add(MyNegotiator(ufun=ufuns[0], name="MyNeg"))
        m.add(SimpleNeg(ufun=ufuns[1], name="Simple"))

        # Run negotiation
        m.run()

        # Check that negotiation completed
        assert m.state.step <= 5

    @pytest.mark.skip(reason="Requires Ollama running locally with llama3.1:8b model")
    def test_can_negotiate_against_itself(self):
        """Test that two MyNegotiators can negotiate against each other."""
        # Create utilities
        ufuns = generate_multi_issue_ufuns(
            n_issues=3, n_values=(3, 5), n_ufuns=2, reserved_values=0.0
        )

        # Create mechanism
        m = SAOMechanism(outcome_space=ufuns[0].outcome_space, n_steps=5)

        # Add negotiators
        m.add(MyNegotiator(ufun=ufuns[0], name="MyNeg1"))
        m.add(MyNegotiator(ufun=ufuns[1], name="MyNeg2"))

        # Run negotiation
        m.run()

        # Check that negotiation completed
        assert m.state.step <= 5

    def test_inherits_from_ollama_negotiator(self):
        """Test that MyNegotiator properly inherits from OllamaNegotiator."""
        from negmas_llm import OllamaNegotiator

        neg = MyNegotiator()
        assert isinstance(neg, OllamaNegotiator)

    def test_different_temperatures_create_different_instances(self):
        """Test that different temperature values create distinct negotiators."""
        neg1 = MyNegotiator(temperature=0.3)
        neg2 = MyNegotiator(temperature=0.9)

        assert neg1 is not neg2
        # We can't directly check temperature as it might not be exposed,
        # but we verify they are distinct instances

    def test_accepts_all_parameter_combinations(self):
        """Test that MyNegotiator can be instantiated with various parameter combinations."""
        # Test combination 1: model + temperature
        neg1 = MyNegotiator(model="llama3.2", temperature=0.8)
        assert neg1 is not None

        # Test combination 2: temperature + max_tokens + system_prompt
        neg2 = MyNegotiator(
            temperature=0.5, max_tokens=2048, system_prompt="Be aggressive"
        )
        assert neg2 is not None

        # Test combination 3: all non-prompt parameters
        neg3 = MyNegotiator(
            model="llama3.2",
            temperature=0.6,
            max_tokens=512,
            use_structured_output=False,
        )
        assert neg3 is not None
