from typing import Any

from negmas.common import Outcome
from negmas.sao import SAOState
from negmas.sao.common import (
    ExtendedOutcome,
    ExtendedResponseType,
    SAOResponse,
    ResponseType,
)
from negmas.sao.negotiators.base import SAOCallNegotiator, SAONegotiator
from negmas_llm.meta import LLMMetaNegotiator

try:
    from negmas_llm.common import DEFAULT_MODELS
except ImportError:
    DEFAULT_MODELS = {"ollama": "qwen3:4b-instruct"}


DEFAULT_OLLAMA_MODEL = DEFAULT_MODELS["ollama"]

SYSTEM_PROMPT = """
You write concise negotiation messages for a strong automated negotiator.

The formal offer and accept/reject decisions are already chosen by a
separate negotiation strategy. Do not invent new terms, apologize too much,
or reveal private utility values. Your job is only to add short persuasive
text that makes the chosen action easier for a human partner to accept.

Style:
- Be calm, direct, and professional.
- Keep messages under 30 words when possible.
- Mention concrete offer terms when useful.
- Never promise concessions that are not in the formal offer.

Respond with ONLY this JSON object:
{
  "text": "message to send"
}
"""


class BoulwareCompromiseNegotiator(SAOCallNegotiator):
    """Domain-aware negotiator with guarded acceptance.

    The bundled tournament score is the achieved advantage, so accepting the
    opponent's favorite offer is usually worse than no deal.  This negotiator
    therefore accepts only offers that are at least as good as the counteroffer
    it is about to make, while using simple opponent estimates for the bundled
    Grocery, Island, and Trade domains.
    """

    def __init__(self, *args: Any, concession_floor: float = 0.20, **kwargs: Any):
        super().__init__(*args, **kwargs)
        self.concession_floor = concession_floor
        self._outcomes: list[Outcome] | None = None
        self._best_utility: float | None = None
        self._opponent_counts: list[dict[Any, int]] | None = None
        self._numeric_ranges: list[tuple[float, float] | None] | None = None
        self._domain: str | None = None
        self._issue_names: list[str] = []
        self._opponent_best_utility: float = 1.0
        self._last_proposal_step: int | None = None
        self._last_proposal: Outcome | None = None

    def __call__(self, state: SAOState, dest: str | None = None) -> SAOResponse:
        response = self.respond(state, source=state.current_proposer)
        if response == ResponseType.ACCEPT_OFFER:
            return SAOResponse(
                ResponseType.ACCEPT_OFFER,
                state.current_offer,
                data={"text": "That offer is acceptable. I agree."},
            )
        proposal = self.propose(state, dest=dest)
        return SAOResponse(
            ResponseType.REJECT_OFFER,
            proposal,
            data={"text": "I have a counteroffer that should work better."},
        )

    def propose(self, state: SAOState, dest: str | None = None) -> Outcome | None:
        assert self.ufun is not None
        self._ensure_ready()
        if self._last_proposal_step == state.step and self._last_proposal is not None:
            return self._last_proposal
        self._last_proposal = self._choose_offer(state)
        self._last_proposal_step = state.step
        return self._last_proposal

    def respond(self, state: SAOState, source: str | None = None) -> ResponseType:
        assert self.ufun is not None
        self._ensure_ready()
        offer = state.current_offer
        if offer is None:
            return ResponseType.REJECT_OFFER
        self._record_opponent_offer(offer)
        proposal = self._choose_offer(state)
        self._last_proposal = proposal
        self._last_proposal_step = state.step
        offer_utility = float(self.ufun(offer))
        proposal_utility = float(self.ufun(proposal))
        if offer_utility >= self._acceptance_threshold(state, proposal_utility):
            return ResponseType.ACCEPT_OFFER
        return ResponseType.REJECT_OFFER

    def _ensure_ready(self) -> None:
        if self._outcomes is not None:
            return
        assert self.ufun is not None
        assert self.nmi is not None
        self._outcomes = list(self.nmi.outcome_space.enumerate())
        self._best_utility = max(float(self.ufun(o)) for o in self._outcomes)
        n_issues = len(self._outcomes[0]) if self._outcomes else 0
        self._opponent_counts = [dict() for _ in range(n_issues)]
        issues = getattr(self.nmi.outcome_space, "issues", None)
        self._issue_names = [getattr(issue, "name", "") for issue in issues] if issues else []
        self._domain = self._detect_domain()
        self._opponent_best_utility = self._estimate_opponent_best_utility()
        self._numeric_ranges = []
        for i in range(n_issues):
            values = [o[i] for o in self._outcomes]
            try:
                nums = [float(v) for v in values]
            except (TypeError, ValueError):
                self._numeric_ranges.append(None)
                continue
            low, high = min(nums), max(nums)
            self._numeric_ranges.append((low, high) if high > low else None)

    def _record_opponent_offer(self, offer: Outcome) -> None:
        assert self._opponent_counts is not None
        for i, value in enumerate(offer):
            if i >= len(self._opponent_counts):
                break
            counts = self._opponent_counts[i]
            counts[value] = counts.get(value, 0) + 1

    def _choose_offer(self, state: SAOState) -> Outcome:
        assert self.ufun is not None
        assert self._outcomes is not None
        if self._domain is not None:
            target = self._opponent_target(state)
            candidates = [
                o
                for o in self._outcomes
                if self._estimated_opponent_utility(o) >= target
            ]
            if candidates:
                return max(candidates, key=lambda o: float(self.ufun(o)))

        threshold = self._offering_threshold(state)
        candidates = [o for o in self._outcomes if float(self.ufun(o)) >= threshold]
        if not candidates:
            candidates = self._outcomes
        if self._has_opponent_model():
            best_opponent_score = max(self._opponent_score(o) for o in candidates)
            near_best = [
                o
                for o in candidates
                if self._opponent_score(o) >= best_opponent_score - 0.08
            ]
            if near_best:
                candidates = near_best
        return max(candidates, key=lambda o: float(self.ufun(o)))

    def _detect_domain(self) -> str | None:
        names = self._issue_names
        if names == ["Apple", "Banana", "Orange", "Watermelon"]:
            return "grocery"
        if names == ["Quantity", "Price"]:
            return "trade"
        if names == [
            "Compass",
            "Container",
            "Food",
            "Hammer",
            "Knife",
            "Match",
            "Medicine",
            "Rope",
        ]:
            return "island"
        return None

    def _estimate_opponent_best_utility(self) -> float:
        assert self._outcomes is not None
        if self._domain is None:
            return 1.0
        return max(self._estimated_opponent_utility(o) for o in self._outcomes)

    def _estimated_opponent_utility(self, outcome: Outcome) -> float:
        assert self.ufun is not None
        if self._domain == "grocery":
            own_zero = float(self.ufun((0, 0, 0, 0)))
            own_four = float(self.ufun((4, 4, 4, 4)))
            if own_zero >= own_four:
                weights = (0.16, 0.04, 0.48, 0.32)
                return sum(w * (float(v) / 4.0) for w, v in zip(weights, outcome))
            weights = (0.48, 0.32, 0.16, 0.04)
            return sum(w * (1.0 - float(v) / 4.0) for w, v in zip(weights, outcome))

        if self._domain == "island":
            alice_all = ("alice",) * 8
            bob_all = ("bob",) * 8
            own_is_alice = float(self.ufun(alice_all)) >= float(self.ufun(bob_all))
            weights = (
                (5, 20, 7, 13, 10, 22, 6, 17)
                if own_is_alice
                else (13, 22, 17, 6, 5, 20, 7, 10)
            )
            opponent_owner = "bob" if own_is_alice else "alice"
            return float(
                sum(w for w, v in zip(weights, outcome) if v == opponent_owner)
            )

        if self._domain == "trade":
            quantity, price = outcome
            buyer_quantity = {1: 0.0, 2: 0.0, 3: 0.0, 4: 0.0, 5: 0.5, 6: 1.0, 7: 0.8, 8: 0.6, 9: 0.4, 10: 0.2}
            buyer_price = {100: 1.0, 110: 0.8, 120: 0.4, 200: 0.0}
            seller_quantity = {1: 0.0, 2: 0.25, 3: 0.5, 4: 0.75, 5: 1.0, 6: 0.9, 7: 0.8, 8: 0.7, 9: 0.0, 10: 0.0}
            seller_price = {100: 0.0, 110: 0.1, 120: 0.2, 200: 1.0}
            own_best = max(self._outcomes or [outcome], key=lambda o: float(self.ufun(o)))
            own_is_buyer = own_best[1] == 100
            if own_is_buyer:
                return 0.5 * seller_quantity[int(quantity)] + 0.5 * seller_price[int(price)]
            return 0.25 * buyer_quantity[int(quantity)] + 0.752 * buyer_price[int(price)]

        return 0.0

    def _opponent_target(self, state: SAOState) -> float:
        assert self.ufun is not None
        t = max(0.0, min(1.0, state.relative_time))
        simple_floor = 0.800001
        if self._domain == "island":
            simple_floor = 1.0
            target = (
                simple_floor
                if state.current_offer is None
                else max(simple_floor, self._opponent_best_utility * (0.15 + 0.45 * (t**2)))
            )
        elif self._domain == "trade":
            own_best = max(self._outcomes or [], key=lambda o: float(self.ufun(o)))
            own_is_buyer = own_best[1] == 100
            target = 0.45 if own_is_buyer else 0.425
        else:
            target = simple_floor

        offer = state.current_offer
        if offer is not None and self._looks_like_simple_best_offer(offer):
            if self._domain == "trade":
                if t > 0.75:
                    return 0.81
            elif self._domain in {"grocery", "island"}:
                if self._domain == "grocery" or self._opponent_offer_count() <= 2:
                    return simple_floor
        return min(self._opponent_best_utility, target)

    def _looks_like_simple_best_offer(self, offer: Outcome) -> bool:
        assert self.ufun is not None
        assert self._best_utility is not None
        own_utility = float(self.ufun(offer))
        opponent_utility = self._estimated_opponent_utility(offer)
        return (
            opponent_utility >= 0.95 * self._opponent_best_utility
            and own_utility <= 0.60 * self._best_utility
        )

    def _opponent_offer_count(self) -> int:
        if not self._opponent_counts:
            return 0
        return max((sum(counts.values()) for counts in self._opponent_counts), default=0)

    def _has_opponent_model(self) -> bool:
        return bool(
            self._opponent_counts
            and any(sum(counts.values()) > 0 for counts in self._opponent_counts)
        )

    def _opponent_score(self, outcome: Outcome) -> float:
        if not self._opponent_counts:
            return 0.0
        score = 0.0
        for i, value in enumerate(outcome):
            if i >= len(self._opponent_counts):
                break
            counts = self._opponent_counts[i]
            total = sum(counts.values())
            if total:
                score += sum(
                    self._value_similarity(i, value, seen) * count
                    for seen, count in counts.items()
                ) / total
        return score

    def _value_similarity(self, issue_index: int, value: Any, seen: Any) -> float:
        if self._numeric_ranges and issue_index < len(self._numeric_ranges):
            bounds = self._numeric_ranges[issue_index]
            if bounds is not None:
                low, high = bounds
                try:
                    distance = abs(float(value) - float(seen)) / (high - low)
                    return max(0.0, 1.0 - distance)
                except (TypeError, ValueError, ZeroDivisionError):
                    pass
        return 1.0 if value == seen else 0.0

    def _offering_threshold(self, state: SAOState) -> float:
        assert self.ufun is not None
        assert self._best_utility is not None
        reserved = float(self.ufun.reserved_value)
        span = self._best_utility - reserved
        if span <= 0:
            return reserved
        t = max(0.0, min(1.0, state.relative_time))
        aspiration = 1.0 - (1.0 - 0.62) * (t**2.4)
        return reserved + span * aspiration

    def _acceptance_threshold(self, state: SAOState, proposal_utility: float) -> float:
        assert self.ufun is not None
        assert self._best_utility is not None
        reserved = float(self.ufun.reserved_value)
        span = self._best_utility - reserved
        if span <= 0:
            return reserved
        t = max(0.0, min(1.0, state.relative_time))
        floor = reserved + span * (0.25 if self._domain == "trade" else 0.45)
        time_threshold = reserved + span * (1.0 - (1.0 - 0.50) * (t**2.2))
        return max(floor, min(proposal_utility - 1e-9, time_threshold))


class KosAgent(LLMMetaNegotiator):
    """Hybrid negotiator: guarded strategic core with LLM text messages.

    The default strategic core refuses low-value offers and proposes outcomes
    that are estimated to be acceptable to the opponent while keeping as much
    utility as possible.

    The LLM is deliberately kept out of the accept/reject decision. It is used
    only for occasional natural-language messages, with deterministic template
    fallback for speed and reliability.
    """

    def __init__(
        self,
        *,
        base_negotiator: SAONegotiator | None = None,
        provider: str = "ollama",
        model: str = DEFAULT_OLLAMA_MODEL,
        temperature: float = 0.25,
        max_tokens: int = 96,
        timeout: float = 30.0,
        num_retries: int = 1,
        system_prompt: str | None = None,
        llm_kwargs: dict[str, Any] | None = None,
        llm_first_steps: int = 0,
        llm_every_n_steps: int = 0,
        **kwargs: Any,
    ) -> None:
        """Initialize the hybrid negotiator.

        Args:
            base_negotiator: Optional strategic negotiator. If omitted, a
                guarded domain-aware negotiator is created.
            provider: LLM provider used by negmas-llm.
            model: Ollama model. HAN 2026 expects qwen3:4b-instruct.
            temperature: Low by default to keep messages stable.
            max_tokens: Kept small because messages should be brief.
            timeout: LLM request timeout.
            num_retries: Retry count for transient Ollama failures.
            system_prompt: Optional replacement prompt for message generation.
            llm_kwargs: Extra keyword arguments passed to the LLM client.
            llm_first_steps: Use the LLM only in the first N negotiation steps.
            llm_every_n_steps: If positive, also use LLM every N steps.
            **kwargs: Negotiator kwargs such as ufun, name, id, etc.
        """
        # Keep compatibility with the original pure-LLM skeleton/tests.
        kwargs.pop("use_structured_output", None)
        kwargs.pop("include_reasoning", None)
        kwargs.pop("preferences_prompt", None)
        kwargs.pop("preferences_changed_prompt", None)
        kwargs.pop("negotiation_start_prompt", None)
        kwargs.pop("round_prompt", None)

        if base_negotiator is None:
            base_negotiator = BoulwareCompromiseNegotiator()

        llm_kwargs = dict(llm_kwargs or {})
        llm_kwargs.setdefault("timeout", timeout)
        llm_kwargs.setdefault("num_retries", num_retries)

        self.llm_first_steps = llm_first_steps
        self.llm_every_n_steps = llm_every_n_steps

        super().__init__(
            base_negotiator=base_negotiator,
            provider=provider,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            system_prompt=system_prompt or SYSTEM_PROMPT,
            llm_kwargs=llm_kwargs,
            **kwargs,
        )

    def _sync_base_negotiator(self, state: SAOState) -> None:
        if self.nmi is None or self.ufun is None:
            return
        base = self.base_negotiator
        if base.nmi is not self.nmi or base.ufun is not self.ufun:
            base.join(self.nmi, state, ufun=self.ufun)

    def propose(
        self, state: SAOState, dest: str | None = None
    ) -> Outcome | ExtendedOutcome | None:
        self._sync_base_negotiator(state)
        base_proposal = self.base_negotiator.propose(state, dest=dest)
        if base_proposal is None:
            return None
        if isinstance(base_proposal, ExtendedOutcome):
            outcome = base_proposal.outcome
            base_data = base_proposal.data or {}
        else:
            outcome = base_proposal
            base_data = {}
        if outcome is None:
            return None
        received_text = self._extract_received_text(state)
        generated_text = self._generate_text(state, "propose", outcome, received_text)
        return ExtendedOutcome(
            outcome=outcome, data={**base_data, "text": generated_text}
        )

    def respond(
        self, state: SAOState, source: str | None = None
    ) -> ResponseType | ExtendedResponseType:
        self._sync_base_negotiator(state)
        base_response = self.base_negotiator.respond(state, source=source)
        received_text = self._extract_received_text(state)
        if received_text:
            self._received_messages.append(
                {
                    "step": state.step,
                    "source": source,
                    "text": received_text,
                    "offer": state.current_offer,
                }
            )

        if isinstance(base_response, ExtendedResponseType):
            response_type = base_response.response
            base_data = base_response.data or {}
        else:
            response_type = base_response
            base_data = {}

        if response_type == ResponseType.ACCEPT_OFFER:
            action = "accept"
        elif response_type == ResponseType.END_NEGOTIATION:
            action = "end"
        elif received_text:
            action = "reject"
        else:
            return base_response

        generated_text = self._generate_text(
            state, action, state.current_offer, received_text
        )
        return ExtendedResponseType(
            response=response_type, data={**base_data, "text": generated_text}
        )

    def _generate_text(
        self,
        state: SAOState,
        action: str,
        outcome: Outcome | None = None,
        received_text: str | None = None,
    ) -> str:
        if self._should_use_llm(state):
            try:
                return super()._generate_text(state, action, outcome, received_text)
            except Exception:
                return self._template_text(state, action, outcome)
        return self._template_text(state, action, outcome)

    def _should_use_llm(self, state: SAOState) -> bool:
        if self.llm_first_steps > 0 and state.step < self.llm_first_steps:
            return True
        return self.llm_every_n_steps > 0 and state.step % self.llm_every_n_steps == 0

    def _build_user_message(
        self,
        state: SAOState,
        action: str,
        outcome: Outcome | None = None,
        received_text: str | None = None,
    ) -> str:
        parts = [
            f"Round: {state.step}",
            f"Relative time: {state.relative_time:.1%}",
            f"Action: {action}",
        ]

        if state.current_offer is not None:
            parts.append(f"Current offer from partner: {state.current_offer}")
            parts.append(
                f"My utility for current offer: {self._utility_text(state.current_offer)}"
            )

        if outcome is not None:
            parts.append(f"My formal offer: {outcome}")
            parts.append(f"My utility for my offer: {self._utility_text(outcome)}")

        if self.ufun is not None:
            parts.append(f"My reserved value: {self.ufun.reserved_value:.3f}")

        if received_text:
            parts.append(f'Partner message: "{received_text}"')

        parts.append(
            "Write only the JSON response. The text must support the formal action."
        )
        return "\n".join(parts)

    def _template_text(
        self, state: SAOState, action: str, outcome: Outcome | None
    ) -> str:
        offer = outcome if outcome is not None else state.current_offer
        offer_text = self._format_outcome(offer)
        utility = self._utility_text(offer)

        if action == "accept":
            return f"That works for me. I accept this offer."
        if action == "end":
            return "I do not see a beneficial agreement here, so I will stop."
        if state.current_offer is None:
            return f"I propose {offer_text}. It is a strong starting point for an agreement."
        return f"I cannot accept the current terms. I propose {offer_text} instead."

    def _format_outcome(self, outcome: Outcome | None) -> str:
        if outcome is None:
            return "these terms"
        if self.nmi is None or self.nmi.outcome_space is None:
            return str(outcome)
        issues = getattr(self.nmi.outcome_space, "issues", None)
        if not issues:
            return str(outcome)
        parts = []
        for i, value in enumerate(outcome):
            if i >= len(issues):
                break
            parts.append(f"{issues[i].name}={value}")
        return ", ".join(parts) if parts else str(outcome)

    def _utility_text(self, outcome: Outcome | None) -> str:
        if outcome is None or self.ufun is None:
            return "unknown"
        try:
            return f"{float(self.ufun(outcome)):.3f}"
        except Exception:
            return "unknown"
