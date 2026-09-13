from datetime import datetime, timezone

import numpy as np

from taskforge.schemas.world import (
    ObjectState,
    RobotState,
    WorldState,
)


class WorldObserver:

    def __init__(
        self,
        backend,
        scenario_id="dual_block_v1",
    ):

        self.backend = backend

        self.scenario_id = (
            scenario_id
        )

        self.object_definitions = {
            "red_block": {
                "class": "block",
                "graspable": True,
            },
            "blue_block": {
                "class": "block",
                "graspable": True,
            },
        }


    # =====================================================
    # OBJECT OBSERVATION
    # =====================================================

    def observe_object(
        self,
        object_id,
    ):

        definition = (
            self.object_definitions[
                object_id
            ]
        )

        position = (
            self.backend.body_position(
                object_id
            )
        )

        orientation = (
            self.backend.body_orientation(
                object_id
            )
        )

        grasped_by = (
            self.backend.attached_to(
                object_id
            )
        )

        return ObjectState(
            object_id=object_id,

            object_class=definition[
                "class"
            ],

            position=[
                round(float(value), 4)
                for value in position
            ],

            orientation=[
                round(float(value), 4)
                for value in orientation
            ],

            graspable=definition[
                "graspable"
            ],

            grasped_by=grasped_by,
        )


    # =====================================================
    # ROBOT OBSERVATION
    # =====================================================

    def observe_robot(
        self,
        arm_name,
    ):

        ee_site = (
            f"{arm_name}_ee"
        )

        shoulder_joint = (
            f"{arm_name}_shoulder"
        )

        elbow_joint = (
            f"{arm_name}_elbow"
        )

        finger_a_joint = (
            f"{arm_name}_finger_a_joint"
        )

        finger_b_joint = (
            f"{arm_name}_finger_b_joint"
        )


        ee_position = (
            self.backend.site_position(
                ee_site
            )
        )

        shoulder_position = (
            self.backend.joint_position(
                shoulder_joint
            )
        )

        elbow_position = (
            self.backend.joint_position(
                elbow_joint
            )
        )

        finger_a = (
            self.backend.joint_position(
                finger_a_joint
            )
        )

        finger_b = (
            self.backend.joint_position(
                finger_b_joint
            )
        )


        # -----------------------------------------
        # Determine gripper state
        # -----------------------------------------

        finger_motion = (
            abs(finger_a)
            + abs(finger_b)
        )

        if finger_motion > 0.01:

            gripper_state = (
                "closed"
            )

        else:

            gripper_state = (
                "open"
            )


        # -----------------------------------------
        # Determine robot state
        # -----------------------------------------

        holding_object = False

        for object_id in (
            self.object_definitions
        ):

            if (
                self.backend.attached_to(
                    object_id
                )
                == f"{arm_name}_arm"
            ):

                holding_object = True
                break


        if holding_object:

            robot_status = (
                "holding"
            )

        else:

            robot_status = (
                "idle"
            )


        return RobotState(

            robot_id=(
                f"{arm_name}_arm"
            ),

            end_effector_position=[
                round(float(value), 4)
                for value
                in ee_position
            ],

            shoulder_position=round(
                float(
                    shoulder_position
                ),
                4,
            ),

            elbow_position=round(
                float(
                    elbow_position
                ),
                4,
            ),

            gripper=(
                gripper_state
            ),

            status=(
                robot_status
            ),
        )


    # =====================================================
    # COMPLETE WORLD OBSERVATION
    # =====================================================

    def observe(self):

        objects = {}

        for object_id in (
            self.object_definitions
        ):

            objects[
                object_id
            ] = self.observe_object(
                object_id
            )


        robots = {

            "left_arm":
                self.observe_robot(
                    "left"
                ),

            "right_arm":
                self.observe_robot(
                    "right"
                ),
        }


        return WorldState(

            timestamp=(
                datetime.now(
                    timezone.utc
                ).isoformat()
            ),

            scenario_id=(
                self.scenario_id
            ),

            simulation_time=round(
                float(
                    self.backend.data.time
                ),
                4,
            ),

            objects=objects,

            robots=robots,

            obstacles=[],

            relations=[],
        )