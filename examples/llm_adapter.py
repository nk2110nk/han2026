from negmas.common import Outcome
from negmas.gb import BoulwareTBNegotiator
from negmas.sao import SAOState
from negmas_llm.meta import LLMMetaNegotiator

try:
    from negmas_llm.common import DEFAULT_MODELS
except ImportError:
    DEFAULT_MODELS = dict(ollama="qwen3:4b-instruct")

DEFAULT_OLLAMA_MODEL = DEFAULT_MODELS["ollama"]

# =============================================================================
# Default Prompt (copied from negmas_llm, customize as needed)
# =============================================================================

# System prompt for text generation in LLMMetaNegotiator
SYSTEM_PROMPT = """
You are assisting a negotiator by generating persuasive text to
accompany offers.

Your role is to:
1. Generate natural, persuasive messages that explain or justify the offer
2. Consider any messages received from the other party
3. Build rapport while advancing the negotiation
4. Keep messages concise but impactful

You will receive:
- The offer being made (or acceptance/rejection decision)
- Any text received from the other party in their last offer
- Context about the negotiation state

Respond with ONLY a JSON object:
{
    "text": "Your message to accompany the offer"
}

Keep messages brief (1-3 sentences) and professional.
"""


class BoulwareBasedLLMNegotiator(LLMMetaNegotiator):
    """A simple LLM-based negotiator that adapts an existing negotiator to use LLM."""

    def __init__(
        self,
        base_negotiator: BoulwareTBNegotiator | None = None,
        provider: str = "ollama",
        model: str = DEFAULT_OLLAMA_MODEL,
        **kwargs,
    ) -> None:
        """Initialize the BolwareBasedLLMNegotiator.

        Args:
            base_negotiator: The base negotiator to adapt. If None, creates a BoulwareTBNegotiator.
            provider: The LLM provider to use (default: "ollama").
            model: The LLM model to use (default: "llama3.1:8b").
            **kwargs: Additional arguments passed to LLMMetaNegotiator.
                Also supports prompt customization via system_prompt parameter.
        """
        if base_negotiator is None:
            base_negotiator = BoulwareTBNegotiator()
        super().__init__(
            base_negotiator=base_negotiator,  # type: ignore
            provider=provider,
            model=model,
            system_prompt=SYSTEM_PROMPT,
            **kwargs,
        )

    def _build_system_prompt(self) -> str:
        """Build the system prompt for text generation.

        Returns:
            The system prompt string.
        """
        return super()._build_system_prompt()

    def _build_user_message(
        self,
        state: SAOState,
        action: str,
        outcome: Outcome | None = None,
        received_text: str | None = None,
    ) -> str:
        """Build the user message for the LLM.

        Args:
            state: The current negotiation state.
            action: The action being taken ("propose", "accept", "reject", "end").
            outcome: The outcome being proposed (if any).
            received_text: Text received from the other party (if any).

        Returns:
            The user message string.
        """
        return super()._build_user_message(state, action, outcome, received_text)

    def _generate_text(
        self,
        state: SAOState,
        action: str,
        outcome: Outcome | None = None,
        received_text: str | None = None,
    ) -> str:
        """Generate text to accompany an offer or response.

        Args:
            state: The current negotiation state.
            action: The action being taken.
            outcome: The outcome being proposed (if any).
            received_text: Text received from the other party (if any).

        Returns:
            The generated text message.
        """
        return super()._generate_text(state, action, outcome, received_text)
