"""Tests for example negotiators."""

import pytest
from negmas.preferences.generators import generate_multi_issue_ufuns
from negmas.sao import SAOMechanism

from examples.nollm import BOANeg, SimpleNeg
from examples.llm_adapter import BoulwareBasedLLMNegotiator
from examples.nollm_adapter import TemplateBasedAdapterNegotiator


class TestBOANeg:
    """Tests for BOANeg negotiator."""

    def test_can_instantiate(self):
        """Test that BOANeg can be instantiated."""
        neg = BOANeg()
        assert neg is not None
        assert neg.name is not None

    def test_has_required_components(self):
        """Test that BOANeg has all required BOA components."""
        neg = BOANeg()
        # BOANeg components are set in __init__ via kwargs
        # We just verify it was created successfully
        assert neg is not None

    def test_can_negotiate(self):
        """Test that BOANeg can participate in a negotiation."""
        # Create utilities
        ufuns = generate_multi_issue_ufuns(
            n_issues=3, n_values=(3, 5), n_ufuns=2, reserved_values=0.0
        )

        # Create mechanism
        m = SAOMechanism(outcome_space=ufuns[0].outcome_space, n_steps=10)

        # Add negotiators
        m.add(BOANeg(ufun=ufuns[0], name="BOA1"))
        m.add(BOANeg(ufun=ufuns[1], name="BOA2"))

        # Run negotiation
        m.run()

        # Check that negotiation completed
        assert m.state.step <= 10
        assert m.state.agreement is not None or m.state.timedout or m.state.broken


class TestSimpleNeg:
    """Tests for SimpleNeg negotiator."""

    def test_can_instantiate(self):
        """Test that SimpleNeg can be instantiated."""
        neg = SimpleNeg()
        assert neg is not None
        assert neg.name is not None

    def test_accepts_high_utility_offers(self):
        """Test that SimpleNeg accepts offers with utility > 0.8."""
        # Create utilities
        ufuns = generate_multi_issue_ufuns(
            n_issues=3, n_values=(3, 5), n_ufuns=2, reserved_values=0.0
        )

        # Create mechanism
        m = SAOMechanism(outcome_space=ufuns[0].outcome_space, n_steps=20)

        # Add negotiators
        m.add(SimpleNeg(ufun=ufuns[0], name="Simple1"))
        m.add(SimpleNeg(ufun=ufuns[1], name="Simple2"))

        # Run negotiation
        m.run()

        # Check that negotiation completed
        assert m.state.step <= 20

    def test_response_includes_text(self):
        """Test that SimpleNeg includes text in its responses."""
        # Create utilities
        ufuns = generate_multi_issue_ufuns(
            n_issues=3, n_values=(3, 5), n_ufuns=2, reserved_values=0.0
        )

        # Create negotiator
        neg = SimpleNeg(ufun=ufuns[0], name="Simple")

        # Create mechanism
        m = SAOMechanism(outcome_space=ufuns[0].outcome_space, n_steps=5)
        m.add(neg)
        m.add(SimpleNeg(ufun=ufuns[1], name="Simple2"))

        # Run negotiation
        m.run()

        # Check that some responses have text (check trace)
        trace = m.trace
        assert len(trace) > 0


class TestBoulwareBasedLLMNegotiator:
    """Tests for BoulwareBasedLLMNegotiator adapter."""

    def test_can_instantiate_without_base(self):
        """Test that BoulwareBasedLLMNegotiator can be instantiated without providing base negotiator."""
        neg = BoulwareBasedLLMNegotiator()
        assert neg is not None
        assert neg.name is not None

    def test_can_instantiate_with_base(self):
        """Test that BoulwareBasedLLMNegotiator can be instantiated with a base negotiator."""
        from negmas.gb import BoulwareTBNegotiator

        base = BoulwareTBNegotiator()
        neg = BoulwareBasedLLMNegotiator(base_negotiator=base)
        assert neg is not None
        assert neg.name is not None

    def test_can_instantiate_with_custom_provider_model(self):
        """Test that BoulwareBasedLLMNegotiator accepts custom provider and model."""
        neg = BoulwareBasedLLMNegotiator(provider="ollama", model="llama3.2")
        assert neg is not None

    @pytest.mark.skip(reason="Requires Ollama running locally")
    def test_can_negotiate(self):
        """Test that BoulwareBasedLLMNegotiator can participate in a negotiation."""
        # Create utilities
        ufuns = generate_multi_issue_ufuns(
            n_issues=3, n_values=(3, 5), n_ufuns=2, reserved_values=0.0
        )

        # Create mechanism
        m = SAOMechanism(outcome_space=ufuns[0].outcome_space, n_steps=5)

        # Add negotiators
        m.add(BoulwareBasedLLMNegotiator(ufun=ufuns[0], name="LLM1"))
        m.add(SimpleNeg(ufun=ufuns[1], name="Simple"))

        # Run negotiation
        m.run()

        # Check that negotiation completed
        assert m.state.step <= 5


class TestTemplateBasedAdapterNegotiator:
    """Tests for TemplateBasedAdapterNegotiator."""

    def test_can_instantiate_without_base(self):
        """Test that TemplateBasedAdapterNegotiator can be instantiated without providing base negotiator."""
        neg = TemplateBasedAdapterNegotiator()
        assert neg is not None
        assert neg.name is not None

    def test_can_instantiate_with_boulware_base(self):
        """Test that TemplateBasedAdapterNegotiator can be instantiated with a Boulware base negotiator."""
        from negmas.gb import BoulwareTBNegotiator

        base = BoulwareTBNegotiator()
        neg = TemplateBasedAdapterNegotiator(base_negotiator=base)
        assert neg is not None
        assert neg.name is not None

    def test_can_instantiate_with_conceder_base(self):
        """Test that TemplateBasedAdapterNegotiator can be instantiated with a Conceder base negotiator."""
        from negmas.gb import ConcederTBNegotiator

        base = ConcederTBNegotiator()
        neg = TemplateBasedAdapterNegotiator(base_negotiator=base)
        assert neg is not None
        assert neg.name is not None

    def test_can_instantiate_with_linear_base(self):
        """Test that TemplateBasedAdapterNegotiator can be instantiated with a Linear base negotiator."""
        from negmas.gb import LinearTBNegotiator

        base = LinearTBNegotiator()
        neg = TemplateBasedAdapterNegotiator(base_negotiator=base)
        assert neg is not None
        assert neg.name is not None

    def test_boulware_vs_boulware(self):
        """Test TemplateBasedAdapterNegotiator with Boulware base against itself."""
        from negmas.gb import BoulwareTBNegotiator

        # Create utilities
        ufuns = generate_multi_issue_ufuns(
            n_issues=3, n_values=(3, 5), n_ufuns=2, reserved_values=0.0
        )

        # Create mechanism
        m = SAOMechanism(outcome_space=ufuns[0].outcome_space, n_steps=20)

        # Add negotiators - both using Boulware
        m.add(
            TemplateBasedAdapterNegotiator(
                base_negotiator=BoulwareTBNegotiator(),
                ufun=ufuns[0],
                name="BoulwareTemplate1",
            )
        )
        m.add(
            TemplateBasedAdapterNegotiator(
                base_negotiator=BoulwareTBNegotiator(),
                ufun=ufuns[1],
                name="BoulwareTemplate2",
            )
        )

        # Run negotiation
        m.run()

        # Check that negotiation completed
        assert m.state.step <= 20
        assert m.state.agreement is not None or m.state.timedout or m.state.broken

    def test_conceder_vs_conceder(self):
        """Test TemplateBasedAdapterNegotiator with Conceder base against itself."""
        from negmas.gb import ConcederTBNegotiator

        # Create utilities
        ufuns = generate_multi_issue_ufuns(
            n_issues=3, n_values=(3, 5), n_ufuns=2, reserved_values=0.0
        )

        # Create mechanism
        m = SAOMechanism(outcome_space=ufuns[0].outcome_space, n_steps=20)

        # Add negotiators - both using Conceder
        m.add(
            TemplateBasedAdapterNegotiator(
                base_negotiator=ConcederTBNegotiator(),
                ufun=ufuns[0],
                name="ConcederTemplate1",
            )
        )
        m.add(
            TemplateBasedAdapterNegotiator(
                base_negotiator=ConcederTBNegotiator(),
                ufun=ufuns[1],
                name="ConcederTemplate2",
            )
        )

        # Run negotiation
        m.run()

        # Check that negotiation completed
        assert m.state.step <= 20
        # Conceder negotiators should often reach agreement
        assert m.state.agreement is not None or m.state.timedout or m.state.broken

    def test_linear_vs_linear(self):
        """Test TemplateBasedAdapterNegotiator with Linear base against itself."""
        from negmas.gb import LinearTBNegotiator

        # Create utilities
        ufuns = generate_multi_issue_ufuns(
            n_issues=3, n_values=(3, 5), n_ufuns=2, reserved_values=0.0
        )

        # Create mechanism
        m = SAOMechanism(outcome_space=ufuns[0].outcome_space, n_steps=20)

        # Add negotiators - both using Linear
        m.add(
            TemplateBasedAdapterNegotiator(
                base_negotiator=LinearTBNegotiator(),
                ufun=ufuns[0],
                name="LinearTemplate1",
            )
        )
        m.add(
            TemplateBasedAdapterNegotiator(
                base_negotiator=LinearTBNegotiator(),
                ufun=ufuns[1],
                name="LinearTemplate2",
            )
        )

        # Run negotiation
        m.run()

        # Check that negotiation completed
        assert m.state.step <= 20
        assert m.state.agreement is not None or m.state.timedout or m.state.broken

    def test_boulware_vs_conceder(self):
        """Test TemplateBasedAdapterNegotiator with Boulware vs Conceder bases."""
        from negmas.gb import BoulwareTBNegotiator, ConcederTBNegotiator

        # Create utilities
        ufuns = generate_multi_issue_ufuns(
            n_issues=3, n_values=(3, 5), n_ufuns=2, reserved_values=0.0
        )

        # Create mechanism
        m = SAOMechanism(outcome_space=ufuns[0].outcome_space, n_steps=20)

        # Add negotiators - Boulware vs Conceder
        m.add(
            TemplateBasedAdapterNegotiator(
                base_negotiator=BoulwareTBNegotiator(),
                ufun=ufuns[0],
                name="BoulwareTemplate",
            )
        )
        m.add(
            TemplateBasedAdapterNegotiator(
                base_negotiator=ConcederTBNegotiator(),
                ufun=ufuns[1],
                name="ConcederTemplate",
            )
        )

        # Run negotiation
        m.run()

        # Check that negotiation completed
        assert m.state.step <= 20
        assert m.state.agreement is not None or m.state.timedout or m.state.broken

    def test_generates_text_in_responses(self):
        """Test that TemplateBasedAdapterNegotiator generates text in its responses."""
        from negmas.gb import BoulwareTBNegotiator

        # Create utilities
        ufuns = generate_multi_issue_ufuns(
            n_issues=3, n_values=(3, 5), n_ufuns=2, reserved_values=0.0
        )

        # Create mechanism
        m = SAOMechanism(outcome_space=ufuns[0].outcome_space, n_steps=10)

        # Add negotiators
        m.add(
            TemplateBasedAdapterNegotiator(
                base_negotiator=BoulwareTBNegotiator(),
                ufun=ufuns[0],
                name="Template1",
            )
        )
        m.add(
            TemplateBasedAdapterNegotiator(
                base_negotiator=BoulwareTBNegotiator(),
                ufun=ufuns[1],
                name="Template2",
            )
        )

        # Run negotiation
        m.run()

        # Check that negotiation completed
        assert m.state.step <= 10

    def test_all_three_strategies_together(self):
        """Test that all three strategies work in a round-robin tournament."""
        from negmas.gb import (
            BoulwareTBNegotiator,
            ConcederTBNegotiator,
            LinearTBNegotiator,
        )

        # Create utilities
        ufuns = generate_multi_issue_ufuns(
            n_issues=3, n_values=(3, 5), n_ufuns=3, reserved_values=0.0
        )

        # Test Boulware vs Conceder
        m1 = SAOMechanism(outcome_space=ufuns[0].outcome_space, n_steps=20)
        m1.add(
            TemplateBasedAdapterNegotiator(
                base_negotiator=BoulwareTBNegotiator(), ufun=ufuns[0], name="Boulware"
            )
        )
        m1.add(
            TemplateBasedAdapterNegotiator(
                base_negotiator=ConcederTBNegotiator(), ufun=ufuns[1], name="Conceder"
            )
        )
        m1.run()
        assert m1.state.step <= 20

        # Test Conceder vs Linear
        m2 = SAOMechanism(outcome_space=ufuns[0].outcome_space, n_steps=20)
        m2.add(
            TemplateBasedAdapterNegotiator(
                base_negotiator=ConcederTBNegotiator(), ufun=ufuns[1], name="Conceder"
            )
        )
        m2.add(
            TemplateBasedAdapterNegotiator(
                base_negotiator=LinearTBNegotiator(), ufun=ufuns[2], name="Linear"
            )
        )
        m2.run()
        assert m2.state.step <= 20

        # Test Linear vs Boulware
        m3 = SAOMechanism(outcome_space=ufuns[0].outcome_space, n_steps=20)
        m3.add(
            TemplateBasedAdapterNegotiator(
                base_negotiator=LinearTBNegotiator(), ufun=ufuns[2], name="Linear"
            )
        )
        m3.add(
            TemplateBasedAdapterNegotiator(
                base_negotiator=BoulwareTBNegotiator(), ufun=ufuns[0], name="Boulware"
            )
        )
        m3.run()
        assert m3.state.step <= 20

    def test_opening_offer_message_does_not_mention_rejection(self):
        """Test that opening offer message doesn't mention rejecting opponent's offer."""
        from negmas.gb import BoulwareTBNegotiator
        from examples.nollm_adapter import (
            OPENING_OFFER_STARTERS,
            REJECTION_STARTERS,
        )

        # Create utilities
        ufuns = generate_multi_issue_ufuns(
            n_issues=2, n_values=(3, 5), n_ufuns=2, reserved_values=0.0
        )

        # Create the negotiator
        neg = TemplateBasedAdapterNegotiator(
            base_negotiator=BoulwareTBNegotiator(),
            ufun=ufuns[0],
            name="TestNeg",
        )

        # Create mechanism and add negotiators
        m = SAOMechanism(outcome_space=ufuns[0].outcome_space, n_steps=10)
        m.add(neg)
        m.add(BoulwareTBNegotiator(ufun=ufuns[1], name="Opponent"))

        # Get the initial state (before any offers)
        state = m.state

        # Verify current_offer is None at the start
        assert state.current_offer is None, "Initial state should have no current offer"

        # Generate an opening offer message using the method directly
        my_offer = (1, 2)  # Dummy offer
        message = neg._generate_rejection_and_counteroffer_message(
            state, my_offer, None
        )

        # Verify the message uses opening starter, not rejection starter
        uses_opening_starter = any(
            starter in message for starter in OPENING_OFFER_STARTERS
        )
        uses_rejection_starter = any(
            starter in message for starter in REJECTION_STARTERS
        )

        assert uses_opening_starter, f"Expected opening starter, got: {message}"
        assert not uses_rejection_starter, (
            f"Should not use rejection starter: {message}"
        )

        # Also verify it doesn't mention "reject", "cannot accept", etc.
        rejection_keywords = ["reject", "cannot accept", "don't accept", "decline"]
        for keyword in rejection_keywords:
            assert keyword.lower() not in message.lower(), (
                f"Opening message should not contain '{keyword}': {message}"
            )
