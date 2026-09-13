from dataclasses import dataclass

from taskforge.execution.executor import (
    PlanExecutor,
)

from taskforge.instruction.parser import (
    InstructionParser,
    InstructionParseError,
)

from taskforge.planner.symbolic_planner import (
    SymbolicPlanner,
)

from taskforge.validator.plan_validator import (
    PlanValidator,
)

from taskforge.verification.goal_verifier import (
    GoalVerifier,
)


@dataclass
class TaskRunResult:

    success: bool

    status: str

    message: str

    goal: object | None = None

    plan: object | None = None

    execution_result: object | None = None

    verification_result: object | None = None


class TaskRunner:

    def __init__(
        self,
        observer,
        arms,
        viewer,
    ):

        self.observer = observer

        self.arms = arms

        self.viewer = viewer

        self.parser = (
            InstructionParser()
        )

        self.planner = (
            SymbolicPlanner()
        )

        self.validator = (
            PlanValidator()
        )

        self.verifier = (
            GoalVerifier()
        )

        self.executor = (
            PlanExecutor(
                arms=self.arms,
                viewer=self.viewer,
            )
        )


    # =====================================================
    # MAIN TASK PIPELINE
    # =====================================================

    def run(
        self,
        instruction: str,
    ) -> TaskRunResult:

        print()
        print("=" * 70)
        print("TASKFORGE TASK RUNNER")
        print("=" * 70)

        print(
            f"Instruction: "
            f"{instruction}"
        )


        # =================================================
        # 1. PARSE
        # =================================================

        print()
        print("[1/6] Parsing instruction...")


        try:

            goal = self.parser.parse(
                instruction
            )

        except InstructionParseError as exc:

            return TaskRunResult(
                success=False,
                status="PARSE_FAILED",
                message=str(exc),
            )


        print(
            "PARSE_SUCCESS"
        )

        print(
            goal.model_dump_json(
                indent=2
            )
        )


        # =================================================
        # 2. OBSERVE CURRENT WORLD
        # =================================================

        print()
        print("[2/6] Observing world...")


        world_before = (
            self.observer.observe()
        )


        # =================================================
        # 3. CHECK WHETHER GOAL IS ALREADY TRUE
        # =================================================

        print()
        print(
            "[3/6] Checking current "
            "goal state..."
        )


        current_verification = (
            self.verifier.verify(
                goal,
                world_before,
            )
        )


        if current_verification.satisfied:

            print()
            print(
                "GOAL_ALREADY_SATISFIED"
            )

            print(
                "No robot movement required."
            )


            return TaskRunResult(
                success=True,
                status=(
                    "GOAL_ALREADY_SATISFIED"
                ),
                message=(
                    "The requested goal was "
                    "already true in the "
                    "current world state."
                ),
                goal=goal,
                verification_result=(
                    current_verification
                ),
            )


        print(
            "Goal not currently satisfied."
        )


        # =================================================
        # 4. PLAN
        # =================================================

        print()
        print("[4/6] Generating plan...")


        try:

            plan = self.planner.create_plan(
                goal,
                world_before,
            )

        except Exception as exc:

            return TaskRunResult(
                success=False,
                status="PLANNING_FAILED",
                message=str(exc),
                goal=goal,
            )


        print(
            "PLAN_GENERATED"
        )

        print(
            plan.model_dump_json(
                indent=2
            )
        )


        # =================================================
        # 5. VALIDATE
        # =================================================

        print()
        print("[5/6] Validating plan...")


        validation = (
            self.validator.validate(
                plan,
                world_before,
            )
        )


        if not validation.valid:

            print(
                "PLAN_INVALID"
            )


            for issue in (
                validation.issues
            ):

                print(
                    f"[{issue.code}] "
                    f"step={issue.step_id} "
                    f"{issue.message}"
                )


            return TaskRunResult(
                success=False,
                status="PLAN_INVALID",
                message=(
                    "Plan rejected by "
                    "PlanValidator."
                ),
                goal=goal,
                plan=plan,
            )


        print(
            "PLAN_VALID"
        )


        # =================================================
        # 6. EXECUTE
        # =================================================

        print()
        print("[6/6] Executing plan...")


        execution_result = (
            self.executor.execute(
                plan
            )
        )


        if not execution_result.success:

            return TaskRunResult(
                success=False,
                status=(
                    "EXECUTION_FAILED"
                ),
                message=(
                    "One or more execution "
                    "steps failed."
                ),
                goal=goal,
                plan=plan,
                execution_result=(
                    execution_result
                ),
            )


        # =================================================
        # FINAL OBSERVATION
        # =================================================

        world_after = (
            self.observer.observe()
        )


        # =================================================
        # FINAL GOAL VERIFICATION
        # =================================================

        final_verification = (
            self.verifier.verify(
                goal,
                world_after,
            )
        )


        print()
        print("=" * 70)
        print("FINAL GOAL VERIFICATION")
        print("=" * 70)


        for check in (
            final_verification.checks
        ):

            print(
                f"{check.predicate}"
                f"("
                f"{check.subject}, "
                f"{check.reference}"
                f") -> "
                f"{check.satisfied}"
            )


        if final_verification.satisfied:

            print()
            print(
                "GOAL_SATISFIED"
            )


            return TaskRunResult(
                success=True,
                status="GOAL_SATISFIED",
                message=(
                    "Execution completed and "
                    "the final world state "
                    "satisfies the goal."
                ),
                goal=goal,
                plan=plan,
                execution_result=(
                    execution_result
                ),
                verification_result=(
                    final_verification
                ),
            )


        print()
        print(
            "GOAL_NOT_SATISFIED"
        )


        return TaskRunResult(
            success=False,
            status=(
                "GOAL_NOT_SATISFIED"
            ),
            message=(
                "Actions executed, but "
                "the final world state does "
                "not satisfy the goal."
            ),
            goal=goal,
            plan=plan,
            execution_result=(
                execution_result
            ),
            verification_result=(
                final_verification
            ),
        )