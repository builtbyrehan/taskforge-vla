from typing import Literal

from pydantic import BaseModel


GoalType = Literal[
    "single_pick",
    "multi_pick",
]


GoalActor = Literal[
    "left_arm",
    "right_arm",
    "auto",
]


GoalAction = Literal[
    "pick",
]


class GoalCommand(BaseModel):

    actor: GoalActor

    action: GoalAction

    target: str


class ParsedGoal(BaseModel):

    original_instruction: str

    goal_type: GoalType

    commands: list[GoalCommand]