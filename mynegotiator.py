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
    """A simple LLM-based negotiator using Ollama.

    This negotiator uses a local Ollama instance to make negotiation decisions.
    It inherits all the LLM-based negotiation capabilities from OllamaNegotiator
    and can be customized through various prompts and parameters.
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

        super().__init__(
            temperature=temperature,
            max_tokens=max_tokens,
            use_structured_output=use_structured_output,
            llm_kwargs=llm_kwargs,
            system_prompt=SYSTEM_PROMPT,
            preferences_prompt=PREFERENCES_PROMPT,
            preferences_changed_prompt=PREFERENCES_CHANGED_PROMPT,
            negotiation_start_prompt=NEGOTIATION_START_PROMPT,
            round_prompt=ROUND_PROMPT,
            **kwargs,
        )
