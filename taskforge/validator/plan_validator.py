from dataclasses import dataclass

from taskforge.schemas.plan import (
    TaskPlan,
)

from taskforge.schemas.world import (
    WorldState,
)


# =========================================================
# VALIDATION RESULT TYPES
# =========================================================

@dataclass
class ValidationIssue:

    code: str

    message: str

    step_id: str | None = None


@dataclass
class ValidationResult:

    valid: bool

    issues: list[ValidationIssue]


# =========================================================
# PLAN VALIDATOR
# =========================================================

class PlanValidator:

    def __init__(
        self,
        available_actors=None,
    ):

        self.available_actors = (
            available_actors
            or {
                "left_arm",
                "right_arm",
            }
        )


    # =====================================================
    # MAIN VALIDATION
    # =====================================================

    def validate(
        self,
        plan: TaskPlan,
        world: WorldState,
    ) -> ValidationResult:

        issues: list[
            ValidationIssue
        ] = []


        # =================================================
        # EMPTY PLAN
        # =================================================

        if not plan.steps:

            issues.append(
                ValidationIssue(
                    code="EMPTY_PLAN",
                    message=(
                        "Plan contains no steps."
                    ),
                )
            )

            return ValidationResult(
                valid=False,
                issues=issues,
            )


        # =================================================
        # STEP IDS
        # =================================================

        step_ids = [
            step.id
            for step in plan.steps
        ]


        # =================================================
        # UNIQUE STEP IDS
        # =================================================

        if len(step_ids) != len(
            set(step_ids)
        ):

            issues.append(
                ValidationIssue(
                    code=(
                        "DUPLICATE_STEP_ID"
                    ),
                    message=(
                        "Plan contains duplicate "
                        "step identifiers."
                    ),
                )
            )


        known_step_ids = set(
            step_ids
        )


        # =================================================
        # STEP ORDER LOOKUP
        # =================================================

        step_order = {
            step.id: index
            for index, step
            in enumerate(plan.steps)
        }


        # =================================================
        # PROJECTED SYMBOLIC WORLD STATE
        # =================================================
        #
        # This is very important.
        #
        # We cannot validate PLACE only from the initial
        # world state because PICK may happen before PLACE.
        #
        # Example:
        #
        # Initial:
        # red_block -> nobody holding it
        #
        # a1 PICK red_block
        # Projected:
        # red_block -> left_arm
        #
        # a2 PLACE red_block
        # Projected:
        # red_block -> None
        #
        # =================================================

        projected_grasped_by = {

            object_id:
                obj.grasped_by

            for object_id, obj
            in world.objects.items()
        }


        # =================================================
        # STEP VALIDATION
        # =================================================

        for step in plan.steps:


            # =================================================
            # ACTOR VALIDATION
            # =================================================

            actor_valid = True


            if (
                step.actor
                not in self.available_actors
            ):

                actor_valid = False

                issues.append(
                    ValidationIssue(
                        code="UNKNOWN_ACTOR",
                        message=(
                            f"Unknown actor: "
                            f"{step.actor}"
                        ),
                        step_id=step.id,
                    )
                )


            # =================================================
            # DEPENDENCY VALIDATION
            # =================================================

            for dependency in (
                step.depends_on
            ):


                # ---------------------------------------------
                # Dependency exists
                # ---------------------------------------------

                if (
                    dependency
                    not in known_step_ids
                ):

                    issues.append(
                        ValidationIssue(
                            code=(
                                "UNKNOWN_DEPENDENCY"
                            ),
                            message=(
                                f"Dependency "
                                f"'{dependency}' "
                                f"does not exist."
                            ),
                            step_id=step.id,
                        )
                    )

                    continue


                # ---------------------------------------------
                # Cannot depend on itself
                # ---------------------------------------------

                if dependency == step.id:

                    issues.append(
                        ValidationIssue(
                            code=(
                                "SELF_DEPENDENCY"
                            ),
                            message=(
                                "Step cannot depend "
                                "on itself."
                            ),
                            step_id=step.id,
                        )
                    )

                    continue


                # ---------------------------------------------
                # Dependency must occur before this step
                # ---------------------------------------------
                #
                # Our current executor runs sequentially.
                # Therefore a step cannot depend on a future
                # step even if the graph is technically
                # acyclic.
                # ---------------------------------------------

                if (
                    step_order[
                        dependency
                    ]
                    >
                    step_order[
                        step.id
                    ]
                ):

                    issues.append(
                        ValidationIssue(
                            code=(
                                "DEPENDENCY_ORDER_ERROR"
                            ),
                            message=(
                                f"Step '{step.id}' "
                                f"depends on future "
                                f"step '{dependency}'."
                            ),
                            step_id=step.id,
                        )
                    )


            # =================================================
            # PICK
            # =================================================

            if step.action == "pick":


                # ---------------------------------------------
                # PICK must have target
                # ---------------------------------------------

                if step.target is None:

                    issues.append(
                        ValidationIssue(
                            code=(
                                "MISSING_TARGET"
                            ),
                            message=(
                                "Pick action "
                                "requires target."
                            ),
                            step_id=step.id,
                        )
                    )

                    continue


                # ---------------------------------------------
                # PICK should not contain position
                # ---------------------------------------------

                if step.position is not None:

                    issues.append(
                        ValidationIssue(
                            code=(
                                "UNEXPECTED_POSITION"
                            ),
                            message=(
                                "Pick action must "
                                "not contain a "
                                "placement position."
                            ),
                            step_id=step.id,
                        )
                    )


                # ---------------------------------------------
                # Object must exist
                # ---------------------------------------------

                if (
                    step.target
                    not in world.objects
                ):

                    issues.append(
                        ValidationIssue(
                            code=(
                                "UNKNOWN_OBJECT"
                            ),
                            message=(
                                f"Object "
                                f"'{step.target}' "
                                f"does not exist "
                                f"in world state."
                            ),
                            step_id=step.id,
                        )
                    )

                    continue


                obj = world.objects[
                    step.target
                ]


                # ---------------------------------------------
                # Object must be graspable
                # ---------------------------------------------

                if not obj.graspable:

                    issues.append(
                        ValidationIssue(
                            code=(
                                "OBJECT_NOT_GRASPABLE"
                            ),
                            message=(
                                f"Object "
                                f"'{step.target}' "
                                f"is not graspable."
                            ),
                            step_id=step.id,
                        )
                    )

                    continue


                # ---------------------------------------------
                # Use PROJECTED state, not just initial state
                # ---------------------------------------------

                current_holder = (
                    projected_grasped_by[
                        step.target
                    ]
                )


                if current_holder is not None:

                    issues.append(
                        ValidationIssue(
                            code=(
                                "OBJECT_ALREADY_GRASPED"
                            ),
                            message=(
                                f"Object "
                                f"'{step.target}' "
                                f"is already projected "
                                f"to be held by "
                                f"{current_holder}."
                            ),
                            step_id=step.id,
                        )
                    )

                    continue


                # ---------------------------------------------
                # PROJECT PICK EFFECT
                # ---------------------------------------------

                if actor_valid:

                    projected_grasped_by[
                        step.target
                    ] = step.actor


            # =================================================
            # PLACE
            # =================================================

            elif step.action == "place":


                # ---------------------------------------------
                # PLACE requires target
                # ---------------------------------------------

                if step.target is None:

                    issues.append(
                        ValidationIssue(
                            code=(
                                "MISSING_TARGET"
                            ),
                            message=(
                                "Place action "
                                "requires target."
                            ),
                            step_id=step.id,
                        )
                    )

                    continue


                # ---------------------------------------------
                # PLACE requires XYZ position
                # ---------------------------------------------

                if step.position is None:

                    issues.append(
                        ValidationIssue(
                            code=(
                                "MISSING_POSITION"
                            ),
                            message=(
                                "Place action "
                                "requires a target "
                                "position."
                            ),
                            step_id=step.id,
                        )
                    )

                    continue


                # ---------------------------------------------
                # Object must exist
                # ---------------------------------------------

                if (
                    step.target
                    not in world.objects
                ):

                    issues.append(
                        ValidationIssue(
                            code=(
                                "UNKNOWN_OBJECT"
                            ),
                            message=(
                                f"Object "
                                f"'{step.target}' "
                                f"does not exist "
                                f"in world state."
                            ),
                            step_id=step.id,
                        )
                    )

                    continue


                # ---------------------------------------------
                # Check projected ownership
                # ---------------------------------------------

                current_holder = (
                    projected_grasped_by[
                        step.target
                    ]
                )


                if (
                    current_holder
                    != step.actor
                ):

                    issues.append(
                        ValidationIssue(
                            code=(
                                "OBJECT_NOT_HELD_BY_ACTOR"
                            ),
                            message=(
                                f"{step.actor} cannot "
                                f"place "
                                f"'{step.target}' "
                                f"because it is "
                                f"projected to be "
                                f"held by "
                                f"{current_holder}."
                            ),
                            step_id=step.id,
                        )
                    )

                    continue


                # ---------------------------------------------
                # PROJECT PLACE EFFECT
                # ---------------------------------------------
                #
                # After PLACE, the object is released.
                # ---------------------------------------------

                projected_grasped_by[
                    step.target
                ] = None


            # =================================================
            # MOVE HOME
            # =================================================

            elif (
                step.action
                == "move_home"
            ):


                # ---------------------------------------------
                # MOVE_HOME must not have object target
                # ---------------------------------------------

                if (
                    step.target
                    is not None
                ):

                    issues.append(
                        ValidationIssue(
                            code=(
                                "UNEXPECTED_TARGET"
                            ),
                            message=(
                                "move_home must "
                                "not have target."
                            ),
                            step_id=step.id,
                        )
                    )


                # ---------------------------------------------
                # MOVE_HOME must not have XYZ position
                # ---------------------------------------------

                if (
                    step.position
                    is not None
                ):

                    issues.append(
                        ValidationIssue(
                            code=(
                                "UNEXPECTED_POSITION"
                            ),
                            message=(
                                "move_home must "
                                "not contain a "
                                "position."
                            ),
                            step_id=step.id,
                        )
                    )


        # =================================================
        # DEPENDENCY CYCLE CHECK
        # =================================================

        if self._has_cycle(
            plan
        ):

            issues.append(
                ValidationIssue(
                    code=(
                        "DEPENDENCY_CYCLE"
                    ),
                    message=(
                        "Plan dependency graph "
                        "contains a cycle."
                    ),
                )
            )


        # =================================================
        # FINAL RESULT
        # =================================================

        return ValidationResult(
            valid=(
                len(issues) == 0
            ),
            issues=issues,
        )


    # =====================================================
    # CYCLE DETECTION
    # =====================================================

    def _has_cycle(
        self,
        plan: TaskPlan,
    ) -> bool:

        graph = {

            step.id:
                list(
                    step.depends_on
                )

            for step
            in plan.steps
        }


        visiting = set()

        visited = set()


        def visit(
            node,
        ):

            # ---------------------------------------------
            # Currently traversing this node -> cycle
            # ---------------------------------------------

            if node in visiting:

                return True


            # ---------------------------------------------
            # Already completely checked
            # ---------------------------------------------

            if node in visited:

                return False


            visiting.add(
                node
            )


            # ---------------------------------------------
            # Traverse dependencies
            # ---------------------------------------------

            for dependency in (
                graph.get(
                    node,
                    []
                )
            ):


                # Unknown dependencies are handled by the
                # main validator.
                if (
                    dependency
                    not in graph
                ):

                    continue


                if visit(
                    dependency
                ):

                    return True


            # ---------------------------------------------
            # Finish node
            # ---------------------------------------------

            visiting.remove(
                node
            )

            visited.add(
                node
            )


            return False


        # =================================================
        # CHECK EVERY COMPONENT
        # =================================================

        for node in graph:

            if visit(
                node
            ):

                return True


        return False