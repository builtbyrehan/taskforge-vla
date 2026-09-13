from typing import Literal

from pydantic import BaseModel, Field


ActorType = Literal[
    "left_arm",
    "right_arm",
]


ActionType = Literal[
    "pick",
    "place",
    "move_home",
]


class PlanStep(BaseModel):

    id: str

    actor: ActorType

    action: ActionType

    target: str | None = None

    # World-space XYZ position.
    # Only required for PLACE.
    position: tuple[
        float,
        float,
        float,
    ] | None = None

    depends_on: list[str] = Field(
        default_factory=list
    )


class TaskPlan(BaseModel):

    plan_id: str

    description: str

    steps: list[PlanStep]


class StepResult(BaseModel):

    step_id: str

    actor: ActorType

    action: ActionType

    target: str | None = None

    success: bool

    message: str


class PlanExecutionResult(BaseModel):

    plan_id: str

    success: bool

    completed_steps: list[str]

    failed_step: str | None

    results: list[StepResult]