from taskforge.schemas.goal import (
    ParsedGoal,
)

from taskforge.schemas.plan import (
    PlanStep,
    TaskPlan,
)


class SymbolicPlanner:

    def __init__(self):

        # TEMPORARY assignment for our current
        # 2-DOF placeholder robot geometry.
        #
        # This will later be replaced by the
        # Bimanual Coordinator / reachability logic.

        self.default_actor_assignment = {

            "red_block":
                "left_arm",

            "blue_block":
                "right_arm",
        }


    # =====================================================
    # ARM RESOLUTION
    # =====================================================

    def resolve_actor(
        self,
        requested_actor,
        target,
    ):

        if requested_actor != "auto":

            return requested_actor


        if (
            target
            in self.default_actor_assignment
        ):

            return (
                self.default_actor_assignment[
                    target
                ]
            )


        raise ValueError(
            f"No automatic arm assignment "
            f"available for '{target}'."
        )


    # =====================================================
    # PLAN GENERATION
    # =====================================================

    def create_plan(
        self,
        goal: ParsedGoal,
    ) -> TaskPlan:

        steps = []

        previous_step_id = None

        step_number = 1


        for command in goal.commands:

            actor = self.resolve_actor(
                command.actor,
                command.target,
            )


            # =============================================
            # PICK
            # =============================================

            pick_id = (
                f"a{step_number}"
            )


            dependencies = []

            if previous_step_id is not None:

                dependencies.append(
                    previous_step_id
                )


            pick_step = PlanStep(

                id=pick_id,

                actor=actor,

                action="pick",

                target=command.target,

                depends_on=dependencies,
            )


            steps.append(
                pick_step
            )

            step_number += 1


            # =============================================
            # RETURN ARM HOME
            # =============================================

            home_id = (
                f"a{step_number}"
            )


            home_step = PlanStep(

                id=home_id,

                actor=actor,

                action="move_home",

                target=None,

                depends_on=[
                    pick_id
                ],
            )


            steps.append(
                home_step
            )

            previous_step_id = (
                home_id
            )

            step_number += 1


        return TaskPlan(

            plan_id="plan_from_language_001",

            description=(
                goal.original_instruction
            ),

            steps=steps,
        )