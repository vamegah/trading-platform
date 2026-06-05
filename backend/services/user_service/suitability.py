from dataclasses import dataclass

from backend.services.user_service.profile_questionnaire import compute_risk_score


@dataclass(frozen=True)
class SuitabilityDecision:
    completed: bool
    risk_score: int
    risk_tolerance: str
    automation_allowed: bool
    restricted_strategies: list[str]
    max_position_weight: float
    reasons: list[str]
    allowed_trading_modes: list[str]
    manual_review_required: bool
    required_acknowledgements: list[str]


RESTRICTED_FOR_LOW_RISK = ["options", "futures", "crypto_leverage", "automated_trading"]
RESTRICTED_FOR_BEGINNER = ["automated_trading", "short_selling", "margin"]


def evaluate_suitability(answers: dict[str, str] | None, requested_strategy: str = "automated_trading") -> SuitabilityDecision:
    if not answers:
        return SuitabilityDecision(
            completed=False,
            risk_score=0,
            risk_tolerance="unknown",
            automation_allowed=False,
            restricted_strategies=["automated_trading", "margin", "options", "futures"],
            max_position_weight=0.0,
            reasons=["Suitability questionnaire is required before automated trading."],
            allowed_trading_modes=["research"],
            manual_review_required=True,
            required_acknowledgements=["complete_suitability_questionnaire"],
        )

    profile = compute_risk_score(answers)
    restricted: set[str] = set()
    reasons: list[str] = []
    experience = answers.get("investment_experience", "none")
    tolerance = profile["risk_tolerance"]

    if tolerance == "low":
        restricted.update(RESTRICTED_FOR_LOW_RISK)
        reasons.append("Low risk tolerance restricts leveraged, derivative, and automated strategies.")
    if experience in {"none", "beginner"}:
        restricted.update(RESTRICTED_FOR_BEGINNER)
        reasons.append("Beginner experience restricts fully automated trading until education and paper trading are complete.")
    if answers.get("investment_horizon") == "short":
        restricted.add("illiquid_strategies")
        reasons.append("Short horizon restricts illiquid or long lock-up strategies.")

    automation_allowed = requested_strategy not in restricted and profile["risk_score"] >= 9
    max_weight = 0.04 if tolerance == "low" else 0.08 if tolerance == "medium" else 0.14
    allowed_modes = ["research", "paper_trading"]
    if automation_allowed:
        allowed_modes.append("automated_trading")
    required_acknowledgements = []
    if requested_strategy in restricted:
        required_acknowledgements.append("strategy_restricted_by_profile")
    if automation_allowed:
        required_acknowledgements.append("automation_risk_acknowledgement")
    return SuitabilityDecision(
        completed=True,
        risk_score=int(profile["risk_score"]),
        risk_tolerance=tolerance,
        automation_allowed=automation_allowed,
        restricted_strategies=sorted(restricted),
        max_position_weight=max_weight,
        reasons=reasons or ["Profile supports the requested strategy within configured risk limits."],
        allowed_trading_modes=allowed_modes,
        manual_review_required=not automation_allowed and requested_strategy == "automated_trading",
        required_acknowledgements=required_acknowledgements,
    )
