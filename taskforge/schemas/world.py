from typing import Literal

from pydantic import BaseModel, Field


class ObjectState(BaseModel):

    object_id: str

    object_class: str

    position: list[float] = Field(
        min_length=3,
        max_length=3,
    )

    orientation: list[float] = Field(
        min_length=4,
        max_length=4,
    )

    graspable: bool = True

    grasped_by: str | None = None


class RobotState(BaseModel):

    robot_id: str

    end_effector_position: list[float] = Field(
        min_length=3,
        max_length=3,
    )

    shoulder_position: float

    elbow_position: float

    gripper: Literal[
        "open",
        "closed",
    ]

    status: Literal[
        "idle",
        "executing",
        "holding",
        "error",
    ] = "idle"


class SpatialRelation(BaseModel):

    subject: str

    relation: str

    object: str


class WorldState(BaseModel):

    timestamp: str

    scenario_id: str

    simulation_time: float

    objects: dict[
        str,
        ObjectState,
    ]

    robots: dict[
        str,
        RobotState,
    ]

    obstacles: list[str] = []

    relations: list[
        SpatialRelation
    ] = []