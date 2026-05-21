from negmas.sao.common import SAOResponse, SAOState, ResponseType
from negmas.sao.negotiators.base import SAOCallNegotiator
from negmas.sao.negotiators.modular import BOANegotiator
from negmas.sao.components.offering import TimeBasedOfferingPolicy
from negmas.sao.components.acceptance import ACNext
from negmas.gb.components.genius.models import GSmithFrequencyModel


class BOANeg(BOANegotiator):
    """A simple negotiator that uses the BOA archiecture without natural text."""

    def __init__(self, *args, **kwargs):
        offering = TimeBasedOfferingPolicy()
        kwargs |= dict(
            acceptance=ACNext(offering),
            offering=offering,
            model=GSmithFrequencyModel(),
        )
        super().__init__(*args, **kwargs)


class SimpleNeg(SAOCallNegotiator):
    """A simple negotiator that uses the SAO architecture with minimal natural text."""

    def __call__(self, state: SAOState, dest: str | None = None) -> SAOResponse:
        assert self.ufun is not None
        offer = state.current_offer
        if self.ufun(offer) > 0.8:
            return SAOResponse(
                ResponseType.ACCEPT_OFFER,
                outcome=offer,
                data=dict(text="Thank you for this great offer. I accept it"),
            )
        return SAOResponse(
            ResponseType.REJECT_OFFER,
            self.ufun.best(),
            data=dict(
                text="I am sorry, but I cannot accept this offer. I will make a counteroffer."
            ),
        )
