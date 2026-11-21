from typing import Literal

from apps.backend.schemas.base import Form


class PortfolioReviewRequest(Form):
    send_to_provider: Literal[True]
