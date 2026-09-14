from taskforge.recovery.recovery_manager import (
    RecoveryManager,
)
from dataclasses import dataclass

from taskforge.execution.executor import (
    PlanExecutor,
)

from taskforge.instruction.parser import (
    InstructionParser,
    InstructionParseError,
)

from taskforge.llm.openrouter_interpreter import (
    OpenRouterGoalInterpreter,
    OpenRouterInterpreterError,
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

# =========================================================
# TASK RESULT
# =========================================================


@dataclass
class TaskRunResult:

    success: bool

    status: str

    message: str

    goal: object | None = None

    plan: object | None = None

    execution_result: object | None = None

    verification_result: object | None = None

    interpretation_source: str | None = None


# =========================================================
# TASK RUNNER
# =========================================================


class TaskRunner:

    def __init__(
        self,
        observer,
        arms,
        viewer,
        failure_injector=None,
        max_recovery_attempts=2,
    ):

        self.observer = observer

        self.arms = arms

        self.viewer = viewer
        self.failure_injector = failure_injector

        self.max_recovery_attempts = max_recovery_attempts

        self.recovery_manager = RecoveryManager()

        # =================================================
        # DETERMINISTIC FALLBACK PARSER
        # =================================================

        self.parser = InstructionParser()

        # =================================================
        # LLM INTERPRETER
        # =================================================
        #
        # The LLM is ONLY used to convert natural language
        # into a typed ParsedGoal.
        #
        # It never controls MuJoCo directly.
        #
        # A shorter timeout is intentional here because
        # this is the real robot pipeline. If the free
        # endpoint becomes slow, TaskForge falls back to
        # the deterministic parser instead of hanging.
        # =================================================

        self.llm_interpreter = None

        self.llm_initialization_error = None

        try:

            self.llm_interpreter = OpenRouterGoalInterpreter(
                timeout=35,
            )

        except OpenRouterInterpreterError as exc:

            self.llm_initialization_error = str(exc)

        # =================================================
        # PLANNING / VALIDATION / VERIFICATION
        # =================================================

        self.planner = SymbolicPlanner(
            arms=self.arms,
        )

        self.validator = PlanValidator()

        self.verifier = GoalVerifier()

        # =================================================
        # EXECUTION
        # =================================================

        self.executor = PlanExecutor(
            arms=self.arms,
            viewer=self.viewer,
            failure_injector=(self.failure_injector),
        )

    # =====================================================
    # GOAL INTERPRETATION
    # =====================================================

    def _interpret_instruction(
        self,
        instruction: str,
    ):

        # =================================================
        # TRY LLM FIRST
        # =================================================

        if self.llm_interpreter is not None:

            print()
            print("Trying OpenRouter " "LLM interpretation...")

            print(f"Model: " f"{self.llm_interpreter.model}")

            try:

                goal = self.llm_interpreter.interpret(instruction)

                print()
                print("LLM_INTERPRETATION_SUCCESS")

                return (
                    goal,
                    "LLM",
                )

            except OpenRouterInterpreterError as exc:

                print()
                print("LLM_INTERPRETATION_FAILED")

                print(str(exc))

                print()
                print("Falling back to " "deterministic parser...")

        else:

            print()
            print("LLM interpreter unavailable.")

            if self.llm_initialization_error:

                print(self.llm_initialization_error)

            print()
            print("Using deterministic " "parser fallback...")

        # =================================================
        # RULE-BASED FALLBACK
        # =================================================

        try:

            goal = self.parser.parse(instruction)

        except InstructionParseError as exc:

            raise InstructionParseError(
                "Both LLM interpretation "
                "and deterministic parsing "
                "failed. "
                f"Parser error: {exc}"
            ) from exc

        print()
        print("RULE_FALLBACK_SUCCESS")

        return (
            goal,
            "RULE_FALLBACK",
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

        print(f"Instruction: " f"{instruction}")

        # =================================================
        # 1. OBSERVE CURRENT WORLD
        # =================================================

        print()
        print("[1/7] Observing current world...")

        try:

            world_before = self.observer.observe()

        except Exception as exc:

            return TaskRunResult(
                success=False,
                status="OBSERVATION_FAILED",
                message=("Could not observe the " f"current world: {exc}"),
            )

        print("WORLD_OBSERVED")

        # =================================================
        # 2. INTERPRET NATURAL LANGUAGE
        # =================================================

        print()
        print("[2/7] Interpreting instruction...")

        try:

            (
                goal,
                interpretation_source,
            ) = self._interpret_instruction(instruction)

        except InstructionParseError as exc:

            return TaskRunResult(
                success=False,
                status="INTERPRETATION_FAILED",
                message=str(exc),
            )

        print()
        print(f"INTERPRETATION_SOURCE: " f"{interpretation_source}")

        print(goal.model_dump_json(indent=2))

        # =================================================
        # 3. CHECK WHETHER GOAL IS ALREADY TRUE
        # =================================================

        print()
        print("[3/7] Checking current " "goal state...")

        try:

            current_verification = self.verifier.verify(
                goal,
                world_before,
            )

        except Exception as exc:

            return TaskRunResult(
                success=False,
                status=("INITIAL_VERIFICATION_FAILED"),
                message=("Could not verify the " "initial goal state: " f"{exc}"),
                goal=goal,
                interpretation_source=(interpretation_source),
            )

        if current_verification.satisfied:

            print()
            print("GOAL_ALREADY_SATISFIED")

            print("No robot movement required.")

            return TaskRunResult(
                success=True,
                status=("GOAL_ALREADY_SATISFIED"),
                message=(
                    "The requested goal was "
                    "already true in the "
                    "current world state."
                ),
                goal=goal,
                verification_result=(current_verification),
                interpretation_source=(interpretation_source),
            )

        print("Goal not currently satisfied.")

        # =================================================
        # 4. PLAN
        # =================================================

        print()
        print("[4/7] Generating symbolic plan...")

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
                interpretation_source=(interpretation_source),
            )

        print("PLAN_GENERATED")

        print(plan.model_dump_json(indent=2))

        # =================================================
        # 5. VALIDATE PLAN
        # =================================================

        print()
        print("[5/7] Validating plan...")

        try:

            validation = self.validator.validate(
                plan,
                world_before,
            )

        except Exception as exc:

            return TaskRunResult(
                success=False,
                status=("VALIDATION_FAILED"),
                message=("Plan validation crashed: " f"{exc}"),
                goal=goal,
                plan=plan,
                interpretation_source=(interpretation_source),
            )

        if not validation.valid:

            print()
            print("PLAN_INVALID")

            for issue in validation.issues:

                print(f"[{issue.code}] " f"step={issue.step_id} " f"{issue.message}")

            return TaskRunResult(
                success=False,
                status="PLAN_INVALID",
                message=("Plan rejected by " "PlanValidator."),
                goal=goal,
                plan=plan,
                interpretation_source=(interpretation_source),
            )

        print("PLAN_VALID")

        # =================================================
        # 6. EXECUTE
        # =================================================

        print()
        print("[6/7] Executing validated plan...")

        try:

            execution_result = self.executor.execute(plan)

        except Exception as exc:

            return TaskRunResult(
                success=False,
                status=("EXECUTION_EXCEPTION"),
                message=("Unexpected execution " f"error: {exc}"),
                goal=goal,
                plan=plan,
                interpretation_source=(interpretation_source),
            )

        if not execution_result.success:

            print()
            print("=" * 70)
            print("RECOVERY TRIGGERED")
            print("=" * 70)

            print(
                f"Initial plan failed at "
                f"step: "
                f"{execution_result.failed_step}"
            )


            # =============================================
            # RECOVERY LOOP
            # =============================================

            for recovery_attempt in range(
                1,
                self.max_recovery_attempts
                + 1,
            ):

                print()
                print("=" * 70)

                print(
                    f"RECOVERY ATTEMPT "
                    f"{recovery_attempt}/"
                    f"{self.max_recovery_attempts}"
                )

                print("=" * 70)


                # =========================================
                # OBSERVE CURRENT WORLD
                # =========================================

                try:

                    recovery_world = (
                        self.observer.observe()
                    )

                except Exception as exc:

                    return TaskRunResult(
                        success=False,
                        status=(
                            "RECOVERY_OBSERVATION_FAILED"
                        ),
                        message=(
                            "Could not observe world "
                            "during recovery: "
                            f"{exc}"
                        ),
                        goal=goal,
                        plan=plan,
                        execution_result=(
                            execution_result
                        ),
                        interpretation_source=(
                            interpretation_source
                        ),
                    )


                print(
                    "RECOVERY_WORLD_OBSERVED"
                )


                # =========================================
                # CHECK ORIGINAL GOAL FIRST
                # =========================================

                recovery_verification = (
                    self.verifier.verify(
                        goal,
                        recovery_world,
                    )
                )


                if (
                    recovery_verification
                    .satisfied
                ):

                    print()
                    print(
                        "GOAL_ALREADY_SATISFIED "
                        "AFTER FAILURE"
                    )


                    return TaskRunResult(
                        success=True,
                        status=(
                            "RECOVERY_SUCCESS"
                        ),
                        message=(
                            "Execution reported a "
                            "failure, but the observed "
                            "world already satisfies "
                            "the original goal."
                        ),
                        goal=goal,
                        plan=plan,
                        execution_result=(
                            execution_result
                        ),
                        verification_result=(
                            recovery_verification
                        ),
                        interpretation_source=(
                            interpretation_source
                        ),
                    )


                # =========================================
                # BUILD RESIDUAL GOAL
                # =========================================

                residual_goal = (
                    self.recovery_manager
                    .build_residual_goal(
                        goal,
                        recovery_world,
                    )
                )


                if residual_goal is None:

                    print(
                        "No residual actions remain."
                    )

                    continue


                # =========================================
                # REPLAN FROM CURRENT WORLD
                # =========================================

                print()
                print(
                    "REPLANNING_FROM_CURRENT_WORLD"
                )


                try:

                    recovery_plan = (
                        self.planner.create_plan(
                            residual_goal,
                            recovery_world,
                        )
                    )

                except Exception as exc:

                    print(
                        f"Recovery planning "
                        f"failed: {exc}"
                    )

                    continue


                print()
                print(
                    "RECOVERY_PLAN_GENERATED"
                )

                print(
                    recovery_plan.model_dump_json(
                        indent=2
                    )
                )


                # =========================================
                # VALIDATE RECOVERY PLAN
                # =========================================

                recovery_validation = (
                    self.validator.validate(
                        recovery_plan,
                        recovery_world,
                    )
                )


                if not recovery_validation.valid:

                    print(
                        "RECOVERY_PLAN_INVALID"
                    )


                    for issue in (
                        recovery_validation.issues
                    ):

                        print(
                            f"[{issue.code}] "
                            f"step="
                            f"{issue.step_id} "
                            f"{issue.message}"
                        )


                    continue


                print(
                    "RECOVERY_PLAN_VALID"
                )


                # =========================================
                # EXECUTE RECOVERY
                # =========================================

                recovery_execution = (
                    self.executor.execute(
                        recovery_plan
                    )
                )


                if (
                    not recovery_execution.success
                ):

                    print()
                    print(
                        "RECOVERY_EXECUTION_FAILED"
                    )

                    execution_result = (
                        recovery_execution
                    )

                    plan = (
                        recovery_plan
                    )

                    continue


                print()
                print(
                    "RECOVERY_EXECUTION_SUCCESS"
                )


                # =========================================
                # OBSERVE AGAIN
                # =========================================

                final_recovery_world = (
                    self.observer.observe()
                )


                # IMPORTANT:
                # Verify the ORIGINAL user goal,
                # not merely the residual goal.
                final_recovery_verification = (
                    self.verifier.verify(
                        goal,
                        final_recovery_world,
                    )
                )


                print()
                print("=" * 70)
                print(
                    "RECOVERY GOAL VERIFICATION"
                )
                print("=" * 70)


                for check in (
                    final_recovery_verification
                    .checks
                ):

                    print(
                        f"{check.predicate}"
                        f"("
                        f"{check.subject}, "
                        f"{check.reference}"
                        f") -> "
                        f"{check.satisfied}"
                    )


                if (
                    final_recovery_verification
                    .satisfied
                ):

                    print()
                    print(
                        "RECOVERY_SUCCESS"
                    )


                    return TaskRunResult(
                        success=True,
                        status=(
                            "RECOVERY_SUCCESS"
                        ),
                        message=(
                            "The initial execution "
                            "failed, TaskForge observed "
                            "the updated world, replanned "
                            "the remaining work, and "
                            "satisfied the original goal."
                        ),
                        goal=goal,
                        plan=(
                            recovery_plan
                        ),
                        execution_result=(
                            recovery_execution
                        ),
                        verification_result=(
                            final_recovery_verification
                        ),
                        interpretation_source=(
                            interpretation_source
                        ),
                    )


                print(
                    "Recovery execution completed "
                    "but original goal is still "
                    "not satisfied."
                )


            # =============================================
            # ALL RECOVERY ATTEMPTS FAILED
            # =============================================

            return TaskRunResult(
                success=False,
                status=(
                    "RECOVERY_FAILED"
                ),
                message=(
                    "Initial execution failed "
                    "and TaskForge exhausted "
                    "its recovery attempts."
                ),
                goal=goal,
                plan=plan,
                execution_result=(
                    execution_result
                ),
                interpretation_source=(
                    interpretation_source
                ),
            )

        # =================================================
        # NORMAL EXECUTION SUCCESS
        # =================================================

        print()
        print("EXECUTION_SUCCESS")

        # =================================================
        # 7. FINAL WORLD OBSERVATION + GOAL VERIFICATION
        # =================================================

        print()
        print("[7/7] Observing final world and verifying goal...")

        try:
            world_after = self.observer.observe()

        except Exception as exc:
            return TaskRunResult(
                success=False,
                status="FINAL_OBSERVATION_FAILED",
                message=(
                    "Execution succeeded, but final world "
                    f"observation failed: {exc}"
                ),
                goal=goal,
                plan=plan,
                execution_result=execution_result,
                interpretation_source=interpretation_source,
            )

        try:
            final_verification = self.verifier.verify(
                goal,
                world_after,
            )

        except Exception as exc:
            return TaskRunResult(
                success=False,
                status="FINAL_VERIFICATION_FAILED",
                message=(
                    "Execution succeeded, but final goal "
                    f"verification failed: {exc}"
                ),
                goal=goal,
                plan=plan,
                execution_result=execution_result,
                interpretation_source=interpretation_source,
            )

        print()
        print("=" * 70)
        print("FINAL GOAL VERIFICATION")
        print("=" * 70)

        for check in final_verification.checks:
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
            print("GOAL_SATISFIED")

            return TaskRunResult(
                success=True,
                status="GOAL_SATISFIED",
                message=(
                    "Execution completed and the final "
                    "world state satisfies the requested goal."
                ),
                goal=goal,
                plan=plan,
                execution_result=execution_result,
                verification_result=final_verification,
                interpretation_source=interpretation_source,
            )

        print()
        print("GOAL_NOT_SATISFIED")

        return TaskRunResult(
            success=False,
            status="GOAL_NOT_SATISFIED",
            message=(
                "Actions executed successfully, but the final "
                "observed world state does not satisfy the requested goal."
            ),
            goal=goal,
            plan=plan,
            execution_result=execution_result,
            verification_result=final_verification,
            interpretation_source=interpretation_source,
        )

