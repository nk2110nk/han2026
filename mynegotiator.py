from negmas.gb.common import ExtendedResponseType, ResponseType
from negmas.outcomes import Outcome
from negmas.outcomes.common import ExtendedOutcome
from negmas.sao.common import SAOResponse, SAOState
from negmas_llm import OllamaNegotiator

# =============================================================================
# Default Prompts (copied from negmas_llm, customize as needed)
# =============================================================================

# System prompt for MyNegotiator
SYSTEM_PROMPT = """
You are an expert negotiator participating in an automated negotiation.
Negotiate effectively to achieve good outcomes for yourself while finding mutually acceptable agreements when possible.
"""

# Prompt sent when preferences are first set
PREFERENCES_PROMPT = """
Negotiation Setup.

You are about to participate in a negotiation. The setup is described below.
{{nmi:text}}

The negotiation outcome space defines the possible agreements.
{{outcome-space:text}}

A utility function maps outcomes to real numbers representing your preference.

Higher values mean more preferred outcomes.

reserved_value is the utility of no agreement and represents your walk-away point.

You must never accept an outcome with utility less than reserved_value.

{{utility-function:text}}

Your reserved value (utility of no agreement) is {{reserved-value}}.
"""

# Prompt sent when preferences change during negotiation
PREFERENCES_CHANGED_PROMPT = """
Preferences Changed.

Your preferences have changed. The change types are {change_types}. Your new utility function is shown below.

{{utility-function:text}}

Your reserved value (utility of no agreement) is {{reserved-value}}.
"""

# Prompt sent when negotiation starts
NEGOTIATION_START_PROMPT = """
Negotiation Started.

The negotiation has now started. For each round, you will be asked to analyze the current state and any offer received, decide whether to ACCEPT, REJECT with a counter-offer, or END, and optionally provide persuasive text for the other party.

Respond in this JSON format for each decision:
```json
{
    "response_type": "accept" | "reject" | "end" | "wait",
    "outcome": [value1, value2, ...] | null,
    "text": "optional persuasive message to send to your opponent",
    "reasoning": "brief explanation of your decision (not sent to opponent)"
}
```

Where accept is to accept the current offer on the table, reject is to reject and provide a counter-offer in outcome, end is to end the negotiation without agreement, and wait is to wait without making an offer (only if allowed by the mechanism). outcome is your counter-offer as a list matching issue order, or null. text is a message that is actually delivered to your opponent. reasoning is your internal reasoning and is not sent to the opponent.

You may occasionally send only text with a null outcome to persuade the opponent, but this should be rare and strategic. Usually include an outcome.

Ready to begin.
"""

# Prompt sent each negotiation round
ROUND_PROMPT = """
Step is {step}, relative time is {relative_time:.1%}, and running status is {running}.

The offer information is shown below.
{offer_info}

What is your decision? Respond with JSON.
"""


class MyNegotiator(OllamaNegotiator):
    """A negotiation agent with an agreement-first fallback strategy.

    The class still inherits from ``OllamaNegotiator`` so it remains compatible
    with the provided template, but its main decision loop is deterministic.
    This keeps local tests fast and prevents the agent from ending negotiations
    without making acceptable concessions.
    """

    def __init__(
        self,
        temperature: float = 0.7,
        max_tokens: int = 1024,
        use_structured_output: bool = True,
        timeout: float = 120.0,
        num_retries: int = 3,
        **kwargs,
    ):
        """Initialize the MyNegotiator with Ollama.

        Args:
            model: The Ollama model to use (default: "llama3.1:8b").
                Common options: "llama3.1:8b", "llama3.2", "mistral", "qwen2.5:7b"
            temperature: Sampling temperature for the LLM (default: 0.7).
                Higher values (e.g., 1.0) make output more random, lower values (e.g., 0.3) make it more deterministic.
            max_tokens: Maximum tokens in the LLM response (default: 1024).
                Controls the length of generated responses.
            use_structured_output: If True, use structured output/JSON mode when supported (default: True).
                Guarantees valid JSON responses from the LLM.
            timeout: Timeout in seconds for LLM API calls (default: 120.0).
                Increase this if you experience timeout issues with slower models.
            num_retries: Number of retries for failed LLM API calls (default: 3).
                Helps handle transient connection issues with Ollama.
            **kwargs: Additional arguments passed to OllamaNegotiator parent class.
                May include: api_base (Ollama API URL), preferences (Preferences object),
                ufun (utility function), name (negotiator name), can_propose (bool), etc.
                Also supports prompt customization: system_prompt, preferences_prompt,
                preferences_changed_prompt, negotiation_start_prompt, round_prompt.
        """
        # Merge user-provided llm_kwargs with timeout/retry settings
        llm_kwargs = kwargs.pop("llm_kwargs", {})
        llm_kwargs.setdefault("timeout", timeout)
        llm_kwargs.setdefault("num_retries", num_retries)
        system_prompt = kwargs.pop("system_prompt", SYSTEM_PROMPT)
        preferences_prompt = kwargs.pop("preferences_prompt", PREFERENCES_PROMPT)
        preferences_changed_prompt = kwargs.pop(
            "preferences_changed_prompt", PREFERENCES_CHANGED_PROMPT
        )
        negotiation_start_prompt = kwargs.pop(
            "negotiation_start_prompt", NEGOTIATION_START_PROMPT
        )
        round_prompt = kwargs.pop("round_prompt", ROUND_PROMPT)

        super().__init__(
            temperature=temperature,
            max_tokens=max_tokens,
            use_structured_output=use_structured_output,
            llm_kwargs=llm_kwargs,
            system_prompt=system_prompt,
            preferences_prompt=preferences_prompt,
            preferences_changed_prompt=preferences_changed_prompt,
            negotiation_start_prompt=negotiation_start_prompt,
            round_prompt=round_prompt,
            **kwargs,
        )

    def on_preferences_changed(self, changes) -> None:
        """Skip the parent LLM notification for faster deterministic behavior."""
        _ = changes

    def on_negotiation_start(self, state) -> None:
        """Skip the parent LLM negotiation-start notification."""
        _ = state

    def __call__(self, state: SAOState, dest: str | None = None) -> SAOResponse:
        """Return an accept/reject decision with a concrete counteroffer.

        The default LLM-only policy can fail to reach agreement because it may
        end early or produce offers the opponent will never accept. This policy
        instead uses a simple concession strategy:

        - accept offers that are good enough for us;
        - otherwise propose an outcome that balances our utility with closeness
          to the opponent's latest offer;
        - after several failed exchanges, accept any offer that is at least as
          good as our reserved value to avoid needless disagreement.
        """
        offer = state.current_offer
        if offer is not None:
            response = self.respond(state, source=state.current_proposer)
            if isinstance(response, ExtendedResponseType):
                response_type = response.response
                data = response.data
            else:
                response_type = response
                data = None

            if response_type != ResponseType.REJECT_OFFER:
                return SAOResponse(response_type, offer, data=data)

        proposal = self.propose(state, dest=dest)
        if isinstance(proposal, ExtendedOutcome):
            return SAOResponse(
                ResponseType.REJECT_OFFER,
                proposal.outcome,
                data=proposal.data,
            )
        return SAOResponse(
            ResponseType.REJECT_OFFER,
            proposal,
            data={"text": "I cannot accept that yet, but here is a counteroffer."},
        )

    def respond(
        self, state: SAOState, source: str | None = None
    ) -> ResponseType | ExtendedResponseType:
        """Accept offers once they are good enough or time is running out."""
        _ = source
        offer = state.current_offer
        if offer is None or self.ufun is None:
            return ResponseType.REJECT_OFFER

        utility = float(self.ufun(offer))
        reserved = float(self.reserved_value or 0.0)
        best = self._best_utility()

        # Concede from a high aspiration toward the reserved value.
        progress = min(max(float(state.relative_time or 0.0), 0.0), 1.0)
        aspiration = reserved + (best - reserved) * (0.82 - 0.55 * progress)

        if utility >= max(reserved, aspiration):
            return ExtendedResponseType(
                ResponseType.ACCEPT_OFFER,
                data={
                    "text": (
                        "This offer is good enough for me, so I am happy to "
                        "accept and conclude the negotiation."
                    )
                },
            )

        # If we have already failed to find agreement for a few rounds, avoid a
        # no-deal outcome as long as the offer is not below our walk-away point.
        if state.step >= 6 and utility >= reserved:
            return ExtendedResponseType(
                ResponseType.ACCEPT_OFFER,
                data={
                    "text": (
                        "To avoid missing an agreement, I can accept this "
                        "proposal."
                    )
                },
            )

        return ResponseType.REJECT_OFFER

    def propose(
        self, state: SAOState, dest: str | None = None
    ) -> Outcome | ExtendedOutcome | None:
        """Propose a high-utility offer that is also plausible for the opponent."""
        _ = dest
        if self.ufun is None:
            return None

        opponent_offer = state.current_offer
        outcome = self._balanced_offer(opponent_offer, state)
        if outcome is None:
            outcome = self.ufun.best()

        return ExtendedOutcome(
            outcome=outcome,
            data={"text": self._offer_text(outcome, opponent_offer)},
        )

    def _outcomes(self) -> list[Outcome]:
        if self.nmi is None or self.nmi.outcome_space is None:
            return []
        return list(self.nmi.outcome_space.enumerate())

    def _best_utility(self) -> float:
        if self.ufun is None:
            return 1.0
        outcomes = self._outcomes()
        if not outcomes:
            best = self.ufun.best()
            return float(self.ufun(best)) if best is not None else 1.0
        return max(float(self.ufun(o)) for o in outcomes)

    def _balanced_offer(
        self, opponent_offer: Outcome | None, state: SAOState
    ) -> Outcome | None:
        """Pick an offer using our utility and a simple opponent-acceptance guess."""
        if self.ufun is None:
            return None
        outcomes = self._outcomes()
        if not outcomes:
            return self.ufun.best()

        reserved = float(self.reserved_value or 0.0)
        utilities = [float(self.ufun(o)) for o in outcomes]
        min_u, max_u = min(utilities), max(utilities)
        span = max(max_u - min_u, 1e-9)

        progress = min(max(float(state.relative_time or 0.0), 0.0), 1.0)
        concession_power = 2.0 + progress

        best_score = float("-inf")
        best_outcome: Outcome | None = None
        for outcome, utility in zip(outcomes, utilities):
            if utility < reserved:
                continue
            my_score = (utility - min_u) / span
            opponent_score = self._estimated_opponent_score(outcome, opponent_offer)
            score = my_score * (opponent_score**concession_power)
            if score > best_score:
                best_score = score
                best_outcome = outcome

        return best_outcome or max(outcomes, key=lambda o: float(self.ufun(o)))

    def _estimated_opponent_score(
        self, outcome: Outcome, opponent_offer: Outcome | None
    ) -> float:
        """Estimate opponent satisfaction from closeness to their latest offer."""
        if opponent_offer is None:
            return 1.0

        ranges = self._issue_ranges()
        scores: list[float] = []
        for i, value in enumerate(outcome):
            if i >= len(opponent_offer):
                continue
            target = opponent_offer[i]
            try:
                v = float(value)
                t = float(target)
                lo, hi = ranges.get(i, (min(v, t), max(v, t)))
                width = max(float(hi) - float(lo), 1e-9)
                scores.append(max(0.0, 1.0 - abs(v - t) / width))
            except (TypeError, ValueError):
                scores.append(1.0 if value == target else 0.0)

        if not scores:
            return 0.5
        return sum(scores) / len(scores)

    def _issue_ranges(self) -> dict[int, tuple[float, float]]:
        outcomes = self._outcomes()
        ranges: dict[int, tuple[float, float]] = {}
        if not outcomes:
            return ranges

        n = len(outcomes[0])
        for i in range(n):
            values: list[float] = []
            for outcome in outcomes:
                try:
                    values.append(float(outcome[i]))
                except (TypeError, ValueError):
                    values = []
                    break
            if values:
                ranges[i] = (min(values), max(values))
        return ranges

    def _offer_text(
        self, outcome: Outcome | None, opponent_offer: Outcome | None
    ) -> str:
        if outcome is None:
            return "I cannot accept that yet, but I am still looking for agreement."
        if opponent_offer is None:
            return (
                "Let me start with an offer that protects my priorities while "
                "leaving room for agreement."
            )

        changed = self._changed_issue_names(outcome, opponent_offer)
        if changed:
            return (
                f"I adjusted {', '.join(changed[:2])} from your proposal while "
                "trying to keep the overall deal acceptable for both sides."
            )
        return "I can repeat this proposal as a concrete path to agreement."

    def _changed_issue_names(
        self, outcome: Outcome, opponent_offer: Outcome
    ) -> list[str]:
        issues = getattr(getattr(self.nmi, "outcome_space", None), "issues", None)
        names: list[str] = []
        for i, value in enumerate(outcome):
            if i >= len(opponent_offer) or value == opponent_offer[i]:
                continue
            if issues and i < len(issues):
                names.append(str(getattr(issues[i], "name", f"issue {i + 1}")))
            else:
                names.append(f"issue {i + 1}")
        return names
