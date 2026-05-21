from typing import Any
from negmas_llm import OllamaNegotiator


class HAN2026LLMNegotiator(OllamaNegotiator):
    """Negotiator that uses the Ollama API to interact with a Qwen3:4b-instruct model."""

    def __init__(
        self,
        temperature: float = 0.7,
        max_tokens: int = 10240,
        use_structured_output: bool = True,
        include_reasoning: bool = False,
        system_prompt: str | None = None,
        preferences_prompt: str | None = None,
        preferences_changed_prompt: str | None = None,
        negotiation_start_prompt: str | None = None,
        round_prompt: str | None = None,
        llm_kwargs: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(
            model="qwen3:4b-instruct",
            temperature=temperature,
            max_tokens=max_tokens,
            use_structured_output=use_structured_output,
            include_reasoning=include_reasoning,
            system_prompt=system_prompt,
            preferences_prompt=preferences_prompt,
            preferences_changed_prompt=preferences_changed_prompt,
            negotiation_start_prompt=negotiation_start_prompt,
            round_prompt=round_prompt,
            llm_kwargs=llm_kwargs,
            **kwargs,
        )
