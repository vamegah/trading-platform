QUESTIONNAIRE = [
    {
        "id": "investment_experience",
        "question": "How would you describe your investment experience?",
        "type": "single_choice",
        "options": [
            {"value": "none", "label": "No experience"},
            {"value": "beginner", "label": "Less than 1 year"},
            {"value": "intermediate", "label": "1-5 years"},
            {"value": "advanced", "label": "More than 5 years"},
        ],
    },
    {
        "id": "risk_tolerance",
        "question": "What is your risk tolerance?",
        "type": "single_choice",
        "options": [
            {"value": "low", "label": "I prefer minimal risk"},
            {"value": "medium", "label": "I can tolerate moderate fluctuations"},
            {"value": "high", "label": "I am comfortable with significant risk"},
        ],
    },
    {
        "id": "annual_income",
        "question": "What is your annual income range?",
        "type": "single_choice",
        "options": [
            {"value": "below_50k", "label": "Below $50,000"},
            {"value": "50k_100k", "label": "$50,000 - $100,000"},
            {"value": "100k_250k", "label": "$100,000 - $250,000"},
            {"value": "above_250k", "label": "Above $250,000"},
        ],
    },
    {
        "id": "net_worth",
        "question": "What is your approximate net worth (excluding primary residence)?",
        "type": "single_choice",
        "options": [
            {"value": "below_50k", "label": "Below $50,000"},
            {"value": "50k_250k", "label": "$50,000 - $250,000"},
            {"value": "250k_1m", "label": "$250,000 - $1,000,000"},
            {"value": "above_1m", "label": "Above $1,000,000"},
        ],
    },
    {
        "id": "investment_horizon",
        "question": "When do you expect to need the majority of your invested funds?",
        "type": "single_choice",
        "options": [
            {"value": "short", "label": "Less than 2 years"},
            {"value": "medium", "label": "2-5 years"},
            {"value": "long", "label": "5-10 years"},
            {"value": "very_long", "label": "More than 10 years"},
        ],
    },
    {
        "id": "loss_tolerance",
        "question": "If your portfolio lost 20% of its value in a month, what would you do?",
        "type": "single_choice",
        "options": [
            {"value": "sell_all", "label": "Sell everything"},
            {"value": "sell_some", "label": "Sell some"},
            {"value": "hold", "label": "Hold and wait"},
            {"value": "buy_more", "label": "Buy more"},
        ],
    },
]


def compute_risk_score(answers: dict) -> dict:
    # Simple scoring logic; maps answer values to scores
    experience_score = {"none": 0, "beginner": 1, "intermediate": 2, "advanced": 3}
    risk_score_map = {"low": 0, "medium": 1, "high": 2}
    loss_reaction = {"sell_all": -2, "sell_some": -1, "hold": 1, "buy_more": 2}
    horizon_score = {"short": 0, "medium": 1, "long": 2, "very_long": 3}
    income_score = {"below_50k": 0, "50k_100k": 1, "100k_250k": 2, "above_250k": 3}
    net_worth_score = {"below_50k": 0, "50k_250k": 1, "250k_1m": 2, "above_1m": 3}

    total = 0
    if "investment_experience" in answers:
        total += experience_score.get(answers["investment_experience"], 0)
    if "risk_tolerance" in answers:
        total += risk_score_map.get(answers["risk_tolerance"], 1) * 2  # weight
    if "loss_tolerance" in answers:
        total += loss_reaction.get(answers["loss_tolerance"], 0) * 2
    if "investment_horizon" in answers:
        total += horizon_score.get(answers["investment_horizon"], 1)
    if "annual_income" in answers:
        total += income_score.get(answers["annual_income"], 1)
    if "net_worth" in answers:
        total += net_worth_score.get(answers["net_worth"], 1)

    # Map total to profile
    if total <= 6:
        risk_tolerance = "low"
        loss_tolerance_percent = 10
    elif total <= 12:
        risk_tolerance = "medium"
        loss_tolerance_percent = 20
    else:
        risk_tolerance = "high"
        loss_tolerance_percent = 30

    return {
        "investment_experience": answers.get("investment_experience"),
        "risk_tolerance": risk_tolerance,
        "annual_income": answers.get("annual_income"),
        "net_worth": answers.get("net_worth"),
        "investment_horizon": answers.get("investment_horizon"),
        "loss_tolerance_percent": loss_tolerance_percent,
        "risk_score": total,
    }
