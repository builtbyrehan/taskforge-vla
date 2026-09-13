from dataclasses import dataclass

from taskforge.schemas.plan import TaskPlan
from taskforge.schemas.world import WorldState


@dataclass
class ValidationIssue:

    code: str

    message: str

    step_id: str | None = None


@dataclass
class ValidationResult:

    valid: bool

    issues: list[ValidationIssue]


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
        # UNIQUE STEP IDS
        # =================================================

        step_ids = [
            step.id
            for step in plan.steps
        ]

        if len(step_ids) != len(
            set(step_ids)
        ):

            issues.append(
                ValidationIssue(
                    code="DUPLICATE_STEP_ID",
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
        # STEP VALIDATION
        # =================================================

        for step in plan.steps:

            # ---------------------------------------------
            # ACTOR
            # ---------------------------------------------

            if (
                step.actor
                not in self.available_actors
            ):

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


            # ---------------------------------------------
            # DEPENDENCIES EXIST
            # ---------------------------------------------

            for dependency in (
                step.depends_on
            ):

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


                if dependency == step.id:

                    issues.append(
                        ValidationIssue(
                            code="SELF_DEPENDENCY",
                            message=(
                                "Step cannot depend "
                                "on itself."
                            ),
                            step_id=step.id,
                        )
                    )


            # ---------------------------------------------
            # PICK RULES
            # ---------------------------------------------

            if step.action == "pick":

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


                if (
                    obj.grasped_by
                    is not None
                ):

                    issues.append(
                        ValidationIssue(
                            code=(
                                "OBJECT_ALREADY_GRASPED"
                            ),
                            message=(
                                f"Object "
                                f"'{step.target}' "
                                f"is already held by "
                                f"{obj.grasped_by}."
                            ),
                            step_id=step.id,
                        )
                    )


            # ---------------------------------------------
            # MOVE HOME RULES
            # ---------------------------------------------

            elif (
                step.action
                == "move_home"
            ):

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
                list(step.depends_on)

            for step
            in plan.steps
        }


        visiting = set()

        visited = set()


        def visit(node):

            if node in visiting:
                return True

            if node in visited:
                return False


            visiting.add(
                node
            )


            for dependency in (
                graph.get(
                    node,
                    []
                )
            ):

                if dependency not in graph:
                    continue

                if visit(
                    dependency
                ):
                    return True


            visiting.remove(
                node
            )

            visited.add(
                node
            )

            return False


        for node in graph:

            if visit(
                node
            ):
                return True


        return False