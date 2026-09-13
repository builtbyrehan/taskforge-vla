from dataclasses import dataclass

from taskforge.schemas.goal import (
    ParsedGoal,
)

from taskforge.schemas.world import (
    WorldState,
)

from taskforge.world_model.predicates import (
    PredicateEngine,
)


@dataclass
class PredicateVerification:

    predicate: str

    subject: str

    reference: str

    satisfied: bool


@dataclass
class GoalVerificationResult:

    satisfied: bool

    checks: list[
        PredicateVerification
    ]


class GoalVerifier:

    def __init__(
        self,
        predicate_engine=None,
    ):

        self.predicate_engine = (
            predicate_engine
            or PredicateEngine()
        )


    # =====================================================
    # VERIFY
    # =====================================================

    def verify(
        self,
        goal: ParsedGoal,
        world: WorldState,
    ) -> GoalVerificationResult:

        checks = []


        # =================================================
        # RELATIONAL GOALS
        # =================================================

        for desired in (
            goal.desired_predicates
        ):

            satisfied = (
                self.predicate_engine.evaluate(
                    world=world,
                    predicate=(
                        desired.predicate
                    ),
                    subject=(
                        desired.subject
                    ),
                    reference=(
                        desired.reference
                    ),
                )
            )


            checks.append(

                PredicateVerification(
                    predicate=(
                        desired.predicate
                    ),
                    subject=(
                        desired.subject
                    ),
                    reference=(
                        desired.reference
                    ),
                    satisfied=(
                        satisfied
                    ),
                )
            )


        # =================================================
        # PICK GOALS
        # =================================================

        if not goal.desired_predicates:

            for command in (
                goal.commands
            ):

                obj = world.objects.get(
                    command.target
                )


                if obj is None:

                    satisfied = False

                elif (
                    command.actor
                    == "auto"
                ):

                    satisfied = (
                        obj.grasped_by
                        is not None
                    )

                else:

                    satisfied = (
                        obj.grasped_by
                        == command.actor
                    )


                checks.append(

                    PredicateVerification(
                        predicate=(
                            "grasped_by"
                        ),
                        subject=(
                            command.target
                        ),
                        reference=(
                            command.actor
                        ),
                        satisfied=(
                            satisfied
                        ),
                    )
                )


        overall = (
            len(checks) > 0
            and all(
                check.satisfied
                for check in checks
            )
        )


        return GoalVerificationResult(
            satisfied=overall,
            checks=checks,
        )