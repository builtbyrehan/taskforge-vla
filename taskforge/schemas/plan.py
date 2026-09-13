from typing import Literal

from pydantic import BaseModel


ActorType = Literal[
    "left_arm",
    "right_arm",
]

ActionType = Literal[
    "pick",
    "move_home",
]


class PlanStep(BaseModel):

    id: str

    actor: ActorType

    action: ActionType

    target: str | None = None

    depends_on: list[str] = []


class TaskPlan(BaseModel):

    plan_id: str

    description: str

    steps: list[PlanStep]


class StepResult(BaseModel):

    step_id: str

    actor: str

    action: str

    target: str | None = None

    success: bool

    message: str


class PlanExecutionResult(BaseModel):

    plan_id: str

    success: bool

    completed_steps: list[str]

    failed_step: str | None = None

    results: list[StepResult]