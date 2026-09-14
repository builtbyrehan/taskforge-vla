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
    ):

        self.observer = observer

        self.arms = arms

        self.viewer = viewer


        # =================================================
        # DETERMINISTIC FALLBACK PARSER
        # =================================================

        self.parser = (
            InstructionParser()
        )


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

            self.llm_interpreter = (
                OpenRouterGoalInterpreter(
                    timeout=35,
                )
            )


        except OpenRouterInterpreterError as exc:

            self.llm_initialization_error = (
                str(exc)
            )


        # =================================================
        # PLANNING / VALIDATION / VERIFICATION
        # =================================================

        self.planner = (
            SymbolicPlanner(
                arms=self.arms,
            )
        )

        self.validator = (
            PlanValidator()
        )

        self.verifier = (
            GoalVerifier()
        )


        # =================================================
        # EXECUTION
        # =================================================

        self.executor = (
            PlanExecutor(
                arms=self.arms,
                viewer=self.viewer,
            )
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

        if (
            self.llm_interpreter
            is not None
        ):

            print()
            print(
                "Trying OpenRouter "
                "LLM interpretation..."
            )

            print(
                f"Model: "
                f"{self.llm_interpreter.model}"
            )


            try:

                goal = (
                    self.llm_interpreter.interpret(
                        instruction
                    )
                )


                print()
                print(
                    "LLM_INTERPRETATION_SUCCESS"
                )


                return (
                    goal,
                    "LLM",
                )


            except OpenRouterInterpreterError as exc:

                print()
                print(
                    "LLM_INTERPRETATION_FAILED"
                )

                print(
                    str(exc)
                )

                print()
                print(
                    "Falling back to "
                    "deterministic parser..."
                )


        else:

            print()
            print(
                "LLM interpreter unavailable."
            )


            if (
                self.llm_initialization_error
            ):

                print(
                    self.llm_initialization_error
                )


            print()
            print(
                "Using deterministic "
                "parser fallback..."
            )


        # =================================================
        # RULE-BASED FALLBACK
        # =================================================

        try:

            goal = (
                self.parser.parse(
                    instruction
                )
            )


        except InstructionParseError as exc:

            raise InstructionParseError(
                "Both LLM interpretation "
                "and deterministic parsing "
                "failed. "
                f"Parser error: {exc}"
            ) from exc


        print()
        print(
            "RULE_FALLBACK_SUCCESS"
        )


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

        print(
            f"Instruction: "
            f"{instruction}"
        )


        # =================================================
        # 1. OBSERVE CURRENT WORLD
        # =================================================

        print()
        print(
            "[1/7] Observing current world..."
        )


        try:

            world_before = (
                self.observer.observe()
            )


        except Exception as exc:

            return TaskRunResult(
                success=False,
                status="OBSERVATION_FAILED",
                message=(
                    "Could not observe the "
                    f"current world: {exc}"
                ),
            )


        print(
            "WORLD_OBSERVED"
        )


        # =================================================
        # 2. INTERPRET NATURAL LANGUAGE
        # =================================================

        print()
        print(
            "[2/7] Interpreting instruction..."
        )


        try:

            (
                goal,
                interpretation_source,
            ) = self._interpret_instruction(
                instruction
            )


        except InstructionParseError as exc:

            return TaskRunResult(
                success=False,
                status="INTERPRETATION_FAILED",
                message=str(exc),
            )


        print()
        print(
            f"INTERPRETATION_SOURCE: "
            f"{interpretation_source}"
        )


        print(
            goal.model_dump_json(
                indent=2
            )
        )


        # =================================================
        # 3. CHECK WHETHER GOAL IS ALREADY TRUE
        # =================================================

        print()
        print(
            "[3/7] Checking current "
            "goal state..."
        )


        try:

            current_verification = (
                self.verifier.verify(
                    goal,
                    world_before,
                )
            )


        except Exception as exc:

            return TaskRunResult(
                success=False,
                status=(
                    "INITIAL_VERIFICATION_FAILED"
                ),
                message=(
                    "Could not verify the "
                    "initial goal state: "
                    f"{exc}"
                ),
                goal=goal,
                interpretation_source=(
                    interpretation_source
                ),
            )


        if (
            current_verification.satisfied
        ):

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

                interpretation_source=(
                    interpretation_source
                ),
            )


        print(
            "Goal not currently satisfied."
        )


        # =================================================
        # 4. PLAN
        # =================================================

        print()
        print(
            "[4/7] Generating symbolic plan..."
        )


        try:

            plan = (
                self.planner.create_plan(
                    goal,
                    world_before,
                )
            )


        except Exception as exc:

            return TaskRunResult(
                success=False,

                status="PLANNING_FAILED",

                message=str(exc),

                goal=goal,

                interpretation_source=(
                    interpretation_source
                ),
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
        # 5. VALIDATE PLAN
        # =================================================

        print()
        print(
            "[5/7] Validating plan..."
        )


        try:

            validation = (
                self.validator.validate(
                    plan,
                    world_before,
                )
            )


        except Exception as exc:

            return TaskRunResult(
                success=False,

                status=(
                    "VALIDATION_FAILED"
                ),

                message=(
                    "Plan validation crashed: "
                    f"{exc}"
                ),

                goal=goal,

                plan=plan,

                interpretation_source=(
                    interpretation_source
                ),
            )


        if not validation.valid:

            print()
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

                interpretation_source=(
                    interpretation_source
                ),
            )


        print(
            "PLAN_VALID"
        )


        # =================================================
        # 6. EXECUTE
        # =================================================

        print()
        print(
            "[6/7] Executing validated plan..."
        )


        try:

            execution_result = (
                self.executor.execute(
                    plan
                )
            )


        except Exception as exc:

            return TaskRunResult(
                success=False,

                status=(
                    "EXECUTION_EXCEPTION"
                ),

                message=(
                    "Unexpected execution "
                    f"error: {exc}"
                ),

                goal=goal,

                plan=plan,

                interpretation_source=(
                    interpretation_source
                ),
            )


        if not execution_result.success:

            print()
            print(
                "EXECUTION_FAILED"
            )


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

                interpretation_source=(
                    interpretation_source
                ),
            )


        print()
        print(
            "EXECUTION_SUCCESS"
        )


        # =================================================
        # 7. OBSERVE AGAIN + VERIFY FINAL WORLD STATE
        # =================================================

        print()
        print(
            "[7/7] Observing final world "
            "and verifying goal..."
        )


        try:

            world_after = (
                self.observer.observe()
            )


        except Exception as exc:

            return TaskRunResult(
                success=False,

                status=(
                    "FINAL_OBSERVATION_FAILED"
                ),

                message=(
                    "Execution succeeded, but "
                    "final world observation "
                    f"failed: {exc}"
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


        try:

            final_verification = (
                self.verifier.verify(
                    goal,
                    world_after,
                )
            )


        except Exception as exc:

            return TaskRunResult(
                success=False,

                status=(
                    "FINAL_VERIFICATION_FAILED"
                ),

                message=(
                    "Could not verify final "
                    f"goal state: {exc}"
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
        # PRINT FINAL VERIFICATION
        # =================================================

        print()
        print("=" * 70)
        print(
            "FINAL GOAL VERIFICATION"
        )
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


        # =================================================
        # GOAL SATISFIED
        # =================================================

        if (
            final_verification.satisfied
        ):

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
                    "satisfies the requested "
                    "goal."
                ),

                goal=goal,

                plan=plan,

                execution_result=(
                    execution_result
                ),

                verification_result=(
                    final_verification
                ),

                interpretation_source=(
                    interpretation_source
                ),
            )


        # =================================================
        # ACTIONS SUCCEEDED BUT GOAL DID NOT
        # =================================================

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
                "the final observed world "
                "state does not satisfy "
                "the requested goal."
            ),

            goal=goal,

            plan=plan,

            execution_result=(
                execution_result
            ),

            verification_result=(
                final_verification
            ),

            interpretation_source=(
                interpretation_source
            ),
        )
