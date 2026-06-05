from backend.services.stress_test_service.scenarios import get_scenario


class StressTestEngine:
    def run_portfolio_stress(
        self,
        portfolio: list[dict],
        scenario_name: str,
        custom_shocks: dict[str, float] | None = None,
    ) -> dict[str, object]:
        scenario = (
            {
                "label": scenario_name.replace("_", " ").title(),
                "severity": "custom",
                "description": "User-defined custom stress scenario.",
                "shocks": custom_shocks or {},
            }
            if custom_shocks is not None
            else get_scenario(scenario_name)
        )
        shocks = scenario["shocks"]
        positions = []
        total_before = 0.0
        total_after = 0.0
        factor_contributions = {factor: 0.0 for factor in shocks}

        for position in portfolio:
            symbol = position["symbol"].upper()
            market_value = float(position["market_value"])
            betas = position.get("factor_betas", {"market": 1.0})
            shock_contributions = {
                factor: float(betas.get(factor, 0.0)) * float(shock)
                for factor, shock in shocks.items()
            }
            stressed_return = sum(shock_contributions.values())
            stressed_value = market_value * (1 + stressed_return)
            total_before += market_value
            total_after += stressed_value
            for factor, contribution in shock_contributions.items():
                factor_contributions[factor] = factor_contributions.get(factor, 0.0) + market_value * contribution
            largest_loss_driver = min(shock_contributions.items(), key=lambda item: item[1], default=(None, 0.0))
            positions.append(
                {
                    "symbol": symbol,
                    "current_value": round(market_value, 2),
                    "stressed_value": round(stressed_value, 2),
                    "pnl": round(stressed_value - market_value, 2),
                    "pnl_percent": round(stressed_return * 100, 2),
                    "shock_contributions": {
                        factor: round(contribution * 100, 2)
                        for factor, contribution in shock_contributions.items()
                    },
                    "largest_loss_driver": largest_loss_driver[0],
                    "threshold_breach": stressed_return <= -0.15,
                }
            )

        total_pnl = total_after - total_before
        total_pnl_percent = (total_pnl / total_before) * 100 if total_before else 0.0
        risk_breach = total_pnl_percent <= -15 or any(position["threshold_breach"] for position in positions)
        recommended_actions = []
        if total_pnl_percent <= -20:
            recommended_actions.append("reduce_gross_exposure")
        if total_pnl_percent <= -10:
            recommended_actions.append("review_hedges")
        if any(position["threshold_breach"] for position in positions):
            recommended_actions.append("inspect_position_concentration")
        return {
            "scenario": scenario_name,
            "scenario_label": scenario.get("label", scenario_name),
            "scenario_severity": scenario.get("severity", "custom"),
            "scenario_description": scenario.get("description"),
            "custom_scenario": custom_shocks is not None,
            "shocks": shocks,
            "portfolio_value_before": round(total_before, 2),
            "portfolio_value_after": round(total_after, 2),
            "total_pnl": round(total_pnl, 2),
            "total_pnl_percent": round(total_pnl_percent, 2),
            "risk_breach": risk_breach,
            "loss_thresholds": {"review_pct": -10.0, "breach_pct": -15.0, "critical_pct": -20.0},
            "recommended_actions": recommended_actions or ["portfolio_within_stress_limits"],
            "factor_contributions": {
                factor: round(contribution, 2)
                for factor, contribution in sorted(factor_contributions.items())
            },
            "positions": sorted(positions, key=lambda item: item["pnl"]),
        }
