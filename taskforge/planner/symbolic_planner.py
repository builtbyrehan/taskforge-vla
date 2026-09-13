from taskforge.schemas.goal import (
    ParsedGoal,
)

from taskforge.schemas.plan import (
    PlanStep,
    TaskPlan,
)


class SymbolicPlanner:

    def __init__(
        self,
        relation_offset=0.10,
        near_offset=0.14,
    ):

        # Temporary assignment based on our
        # current placeholder robot geometry.

        self.default_actor_assignment = {

            "red_block":
                "left_arm",

            "blue_block":
                "right_arm",
        }


        self.relation_offset = (
            relation_offset
        )

        self.near_offset = (
            near_offset
        )


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
            f"No automatic arm "
            f"assignment available "
            f"for '{target}'."
        )


    # =====================================================
    # RELATIONAL TARGET POSITION
    # =====================================================

    def calculate_relation_position(
        self,
        predicate,
        world,
    ):

        subject = predicate.subject

        reference = predicate.reference


        if (
            subject
            not in world.objects
        ):

            raise ValueError(
                f"Unknown subject object: "
                f"{subject}"
            )


        if (
            reference
            not in world.objects
        ):

            raise ValueError(
                f"Unknown reference object: "
                f"{reference}"
            )


        subject_position = list(
            world.objects[
                subject
            ].position
        )

        reference_position = list(
            world.objects[
                reference
            ].position
        )


        # Keep our current table/object Z.
        target_z = (
            subject_position[2]
        )


        # =================================================
        # RIGHT OF
        # =================================================

        if (
            predicate.predicate
            == "right_of"
        ):

            return (
                reference_position[0]
                + self.relation_offset,

                reference_position[1],

                target_z,
            )


        # =================================================
        # LEFT OF
        # =================================================

        if (
            predicate.predicate
            == "left_of"
        ):

            return (
                reference_position[0]
                - self.relation_offset,

                reference_position[1],

                target_z,
            )


        # =================================================
        # NEAR
        # =================================================

        if (
            predicate.predicate
            == "near"
        ):

            return (
                reference_position[0]
                + self.near_offset,

                reference_position[1],

                target_z,
            )


        raise ValueError(
            f"Unsupported predicate: "
            f"{predicate.predicate}"
        )


    # =====================================================
    # RELATIONAL PLAN
    # =====================================================

    def _create_relational_plan(
        self,
        goal,
        world,
    ):

        if world is None:

            raise ValueError(
                "Relational planning "
                "requires WorldState."
            )


        if (
            not goal.desired_predicates
        ):

            raise ValueError(
                "Relational goal contains "
                "no desired predicate."
            )


        predicate = (
            goal.desired_predicates[0]
        )


        actor = self.resolve_actor(
            "auto",
            predicate.subject,
        )


        target_position = (
            self.calculate_relation_position(
                predicate,
                world,
            )
        )


        return TaskPlan(

            plan_id=(
                "plan_relational_001"
            ),

            description=(
                goal.original_instruction
            ),

            steps=[

                PlanStep(
                    id="a1",
                    actor=actor,
                    action="pick",
                    target=(
                        predicate.subject
                    ),
                ),

                PlanStep(
                    id="a2",
                    actor=actor,
                    action="place",
                    target=(
                        predicate.subject
                    ),
                    position=(
                        target_position
                    ),
                    depends_on=[
                        "a1"
                    ],
                ),

                PlanStep(
                    id="a3",
                    actor=actor,
                    action="move_home",
                    depends_on=[
                        "a2"
                    ],
                ),
            ],
        )


    # =====================================================
    # PICK PLAN
    # =====================================================

    def _create_pick_plan(
        self,
        goal,
    ):

        steps = []

        previous_step_id = None

        step_number = 1


        for command in goal.commands:

            actor = self.resolve_actor(
                command.actor,
                command.target,
            )


            pick_id = (
                f"a{step_number}"
            )


            dependencies = []


            if previous_step_id is not None:

                dependencies.append(
                    previous_step_id
                )


            steps.append(

                PlanStep(
                    id=pick_id,
                    actor=actor,
                    action="pick",
                    target=(
                        command.target
                    ),
                    depends_on=(
                        dependencies
                    ),
                )
            )


            step_number += 1


            home_id = (
                f"a{step_number}"
            )


            steps.append(

                PlanStep(
                    id=home_id,
                    actor=actor,
                    action="move_home",
                    depends_on=[
                        pick_id
                    ],
                )
            )


            previous_step_id = (
                home_id
            )

            step_number += 1


        return TaskPlan(

            plan_id=(
                "plan_from_language_001"
            ),

            description=(
                goal.original_instruction
            ),

            steps=steps,
        )


    # =====================================================
    # MAIN ENTRY POINT
    # =====================================================

    def create_plan(
        self,
        goal: ParsedGoal,
        world=None,
    ) -> TaskPlan:

        if (
            goal.goal_type
            == "relational"
        ):

            return (
                self._create_relational_plan(
                    goal,
                    world,
                )
            )


        return (
            self._create_pick_plan(
                goal
            )
        )