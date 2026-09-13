from typing import Literal

from pydantic import BaseModel, Field


GoalType = Literal[
    "single_pick",
    "multi_pick",
    "relational",
]


GoalActor = Literal[
    "left_arm",
    "right_arm",
    "auto",
]


GoalAction = Literal[
    "pick",
]


PredicateType = Literal[
    "left_of",
    "right_of",
    "near",
]


class GoalCommand(BaseModel):

    actor: GoalActor

    action: GoalAction

    target: str


class GoalPredicate(BaseModel):

    predicate: PredicateType

    subject: str

    reference: str


class ParsedGoal(BaseModel):

    original_instruction: str

    goal_type: GoalType

    commands: list[GoalCommand] = Field(
        default_factory=list
    )

    desired_predicates: list[
        GoalPredicate
    ] = Field(
        default_factory=list
    )