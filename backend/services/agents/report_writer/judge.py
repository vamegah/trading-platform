"""
LLM-as-judge evaluation for the Report Writer.

Scores the markdown report on a 0-100 scale and returns structured
feedback. Used only when a LangFuse client is present so traces can
attach the score.
"""
import logging
import os

from agents import Agent, Runner
from agents.extensions.models.litellm_model import LitellmModel
from pydantic import BaseModel, Field

logger = logging.getLogger()

BEDROCK_MODEL_ID = os.getenv("BEDROCK_MODEL_ID", "us.anthropic.claude-3-7-sonnet-20250219-v1:0")
BEDROCK_REGION = os.getenv("BEDROCK_REGION", "us-west-2")

JUDGE_INSTRUCTIONS = """
You are an Evaluation Agent scoring the quality of a financial report
produced by a Report Writer agent. Given the instructions sent to the
writer and its output, produce a score from 0 to 100 and specific
feedback. Consider factual accuracy, clarity, structure, actionability,
and adherence to the requested sections. Never invent portfolio data.
"""


class Evaluation(BaseModel):
    feedback: str = Field(description="Feedback and rationale for the score")
    score: float = Field(description="Score from 0 to 100", ge=0, le=100)


async def evaluate(original_instructions: str, original_task: str, original_output: str) -> Evaluation:
    os.environ["AWS_REGION_NAME"] = BEDROCK_REGION
    model = LitellmModel(model=f"bedrock/{BEDROCK_MODEL_ID}")

    task = f"""
The Report Writer was given these instructions:

{original_instructions}

It was assigned this task:

{original_task}

Its output was:

{original_output}

Evaluate the output and respond with your comments and score.
"""

    try:
        agent = Agent(
            name="Judge Agent",
            instructions=JUDGE_INSTRUCTIONS,
            model=model,
            output_type=Evaluation,
        )
        result = await Runner.run(agent, input=task, max_turns=3)
        return result.final_output_as(Evaluation)
    except Exception as exc:
        logger.exception("Judge evaluation failed")
        return Evaluation(feedback=f"Judge error: {exc}", score=0)