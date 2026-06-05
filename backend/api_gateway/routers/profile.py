from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List, Dict
from backend.shared.database import get_db
from backend.shared.models import User, RiskProfile
from backend.api_gateway.dependencies import get_current_active_user
from backend.services.user_service.profile_questionnaire import (
    QUESTIONNAIRE,
    compute_risk_score,
)
from backend.services.user_service.suitability import evaluate_suitability

router = APIRouter()


class RiskProfileSubmit(BaseModel):
    answers: Dict[str, str]  # question_id -> answer


class RiskProfileOut(BaseModel):
    completed: bool
    investment_experience: Optional[str]
    risk_tolerance: Optional[str]
    annual_income: Optional[str]
    net_worth: Optional[str]
    investment_horizon: Optional[str]
    loss_tolerance_percent: Optional[float]
    risk_score: Optional[int]
    raw_answers: Optional[dict]


class SuitabilityRequest(BaseModel):
    answers: Dict[str, str] | None = None
    requested_strategy: str = "automated_trading"


@router.get("/questionnaire", response_model=List[dict])
def get_questionnaire(current_user: User = Depends(get_current_active_user)):
    return QUESTIONNAIRE


@router.post("/questionnaire", response_model=RiskProfileOut)
def submit_questionnaire(
    submission: RiskProfileSubmit,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    # Compute risk profile
    profile_data = compute_risk_score(submission.answers)
    # Save or update risk profile
    profile = (
        db.query(RiskProfile).filter(RiskProfile.user_id == current_user.id).first()
    )
    if not profile:
        profile = RiskProfile(user_id=current_user.id)
        db.add(profile)
    profile.investment_experience = profile_data["investment_experience"]
    profile.risk_tolerance = profile_data["risk_tolerance"]
    profile.annual_income = profile_data.get("annual_income")
    profile.net_worth = profile_data.get("net_worth")
    profile.investment_horizon = profile_data.get("investment_horizon")
    profile.loss_tolerance_percent = profile_data.get("loss_tolerance_percent")
    profile.risk_score = profile_data["risk_score"]
    profile.questionnaire_answers = submission.answers
    current_user.risk_profile_completed = True
    db.commit()
    db.refresh(profile)
    return {
        "completed": True,
        "investment_experience": profile.investment_experience,
        "risk_tolerance": profile.risk_tolerance,
        "annual_income": profile.annual_income,
        "net_worth": profile.net_worth,
        "investment_horizon": profile.investment_horizon,
        "loss_tolerance_percent": profile.loss_tolerance_percent,
        "risk_score": profile.risk_score,
        "raw_answers": profile.questionnaire_answers,
    }


@router.get("/me/risk-profile", response_model=RiskProfileOut)
def get_my_risk_profile(
    db: Session = Depends(get_db), current_user: User = Depends(get_current_active_user)
):
    profile = (
        db.query(RiskProfile).filter(RiskProfile.user_id == current_user.id).first()
    )
    if not profile:
        return {
            "completed": False,
            "investment_experience": None,
            "risk_tolerance": None,
            "annual_income": None,
            "net_worth": None,
            "investment_horizon": None,
            "loss_tolerance_percent": None,
            "risk_score": None,
            "raw_answers": None,
        }
    return {
        "completed": True,
        "investment_experience": profile.investment_experience,
        "risk_tolerance": profile.risk_tolerance,
        "annual_income": profile.annual_income,
        "net_worth": profile.net_worth,
        "investment_horizon": profile.investment_horizon,
        "loss_tolerance_percent": profile.loss_tolerance_percent,
        "risk_score": profile.risk_score,
        "raw_answers": profile.questionnaire_answers,
    }


@router.post("/suitability/evaluate")
def evaluate_profile_suitability(request: SuitabilityRequest) -> dict[str, object]:
    return evaluate_suitability(request.answers, request.requested_strategy).__dict__


@router.post("/suitability/guard")
def guard_automated_strategy(request: SuitabilityRequest) -> dict[str, object]:
    decision = evaluate_suitability(request.answers, request.requested_strategy)
    return {
        **decision.__dict__,
        "allowed": decision.automation_allowed,
        "requested_strategy": request.requested_strategy,
    }
