from taskforge.schemas.plan import (
    PlanExecutionResult,
    StepResult,
    TaskPlan,
)


class PlanExecutor:

    def __init__(
        self,
        arms,
        viewer,
    ):
        self.arms = arms
        self.viewer = viewer


    # =====================================================
    # ACTION DISPATCH
    # =====================================================

    def execute_step(
        self,
        step,
    ):

        # -------------------------------------------------
        # ACTOR CHECK
        # -------------------------------------------------

        if step.actor not in self.arms:

            return StepResult(
                step_id=step.id,
                actor=step.actor,
                action=step.action,
                target=step.target,
                success=False,
                message=(
                    f"Unknown actor: "
                    f"{step.actor}"
                ),
            )


        arm = self.arms[
            step.actor
        ]


        # =================================================
        # PICK
        # =================================================

        if step.action == "pick":

            if step.target is None:

                return StepResult(
                    step_id=step.id,
                    actor=step.actor,
                    action=step.action,
                    target=None,
                    success=False,
                    message=(
                        "PICK requires target"
                    ),
                )


            success = arm.pick(
                step.target,
                self.viewer,
            )


            return StepResult(
                step_id=step.id,
                actor=step.actor,
                action=step.action,
                target=step.target,
                success=success,
                message=(
                    "Pick completed"
                    if success
                    else "Pick failed"
                ),
            )


        # =================================================
        # MOVE HOME
        # =================================================

        if step.action == "move_home":

            success = arm.move_home(
                self.viewer
            )


            return StepResult(
                step_id=step.id,
                actor=step.actor,
                action=step.action,
                target=None,
                success=success,
                message=(
                    "Arm returned home"
                    if success
                    else "Home movement failed"
                ),
            )


        # =================================================
        # UNSUPPORTED ACTION
        # =================================================

        return StepResult(
            step_id=step.id,
            actor=step.actor,
            action=step.action,
            target=step.target,
            success=False,
            message=(
                f"Unsupported action: "
                f"{step.action}"
            ),
        )


    # =====================================================
    # PLAN EXECUTION
    # =====================================================

    def execute(
        self,
        plan: TaskPlan,
    ) -> PlanExecutionResult:

        print()
        print("=" * 70)
        print("TASKFORGE PLAN EXECUTOR")
        print("=" * 70)

        print(
            f"Plan ID: {plan.plan_id}"
        )

        print(
            f"Goal: {plan.description}"
        )

        print(
            f"Steps: {len(plan.steps)}"
        )

        print()


        # -------------------------------------------------
        # completed_steps:
        # preserves actual execution order
        #
        # completed_step_ids:
        # fast dependency lookup
        # -------------------------------------------------

        completed_steps = []

        completed_step_ids = set()

        results = []


        # =================================================
        # EXECUTE PLAN SEQUENTIALLY
        # =================================================

        for step in plan.steps:

            print()
            print("-" * 70)

            print(
                f"STEP {step.id}"
            )

            print(
                f"Actor:  {step.actor}"
            )

            print(
                f"Action: {step.action}"
            )

            print(
                f"Target: {step.target}"
            )

            print(
                f"Depends on: "
                f"{step.depends_on}"
            )


            # =============================================
            # DEPENDENCY CHECK
            # =============================================

            missing_dependencies = [

                dependency

                for dependency
                in step.depends_on

                if dependency
                not in completed_step_ids
            ]


            if missing_dependencies:

                print()
                print(
                    "DEPENDENCY FAILURE"
                )

                print(
                    f"Missing: "
                    f"{missing_dependencies}"
                )


                result = StepResult(
                    step_id=step.id,
                    actor=step.actor,
                    action=step.action,
                    target=step.target,
                    success=False,
                    message=(
                        "Dependencies not "
                        "completed: "
                        f"{missing_dependencies}"
                    ),
                )


                results.append(
                    result
                )


                return PlanExecutionResult(
                    plan_id=plan.plan_id,
                    success=False,
                    completed_steps=(
                        completed_steps
                    ),
                    failed_step=step.id,
                    results=results,
                )


            # =============================================
            # VIEWER CHECK
            # =============================================

            if (
                self.viewer is not None
                and not self.viewer.is_running()
            ):

                result = StepResult(
                    step_id=step.id,
                    actor=step.actor,
                    action=step.action,
                    target=step.target,
                    success=False,
                    message=(
                        "Viewer closed before "
                        "step execution."
                    ),
                )


                results.append(
                    result
                )


                return PlanExecutionResult(
                    plan_id=plan.plan_id,
                    success=False,
                    completed_steps=(
                        completed_steps
                    ),
                    failed_step=step.id,
                    results=results,
                )


            # =============================================
            # EXECUTE ACTION
            # =============================================

            print()
            print(
                f"Executing {step.id}..."
            )


            try:

                result = (
                    self.execute_step(
                        step
                    )
                )


            except Exception as exc:

                result = StepResult(
                    step_id=step.id,
                    actor=step.actor,
                    action=step.action,
                    target=step.target,
                    success=False,
                    message=(
                        f"Execution exception: "
                        f"{exc}"
                    ),
                )


            results.append(
                result
            )


            # =============================================
            # STEP SUCCESS
            # =============================================

            if result.success:

                # Preserve order
                completed_steps.append(
                    step.id
                )

                # Fast membership check
                completed_step_ids.add(
                    step.id
                )

                print()
                print(
                    f"STEP {step.id}: "
                    f"SUCCESS"
                )


            # =============================================
            # STEP FAILURE
            # =============================================

            else:

                print()
                print(
                    f"STEP {step.id}: "
                    f"FAILED"
                )

                print(
                    f"Reason: "
                    f"{result.message}"
                )


                return PlanExecutionResult(
                    plan_id=plan.plan_id,
                    success=False,
                    completed_steps=(
                        completed_steps
                    ),
                    failed_step=step.id,
                    results=results,
                )


        # =================================================
        # PLAN SUCCESS
        # =================================================

        print()
        print("=" * 70)
        print("ALL PLAN STEPS COMPLETED")
        print("=" * 70)


        return PlanExecutionResult(
            plan_id=plan.plan_id,
            success=True,
            completed_steps=(
                completed_steps
            ),
            failed_step=None,
            results=results,
        )