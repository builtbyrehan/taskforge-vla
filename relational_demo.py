import mujoco.viewer

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

from taskforge.robot.arm import (
    ArmController,
)

from taskforge.simulation.mujoco_backend import (
    MujocoBackend,
)

from taskforge.validator.plan_validator import (
    PlanValidator,
)

from taskforge.verification.goal_verifier import (
    GoalVerifier,
)

from taskforge.world_model.observer import (
    WorldObserver,
)

from taskforge.world_model.predicates import (
    PredicateEngine,
)


MODEL_PATH = "models/scene.xml"


def main():

    print("=" * 70)
    print("TASKFORGE VLA")
    print(
        "Phase 9 - Relational Goal "
        "+ Final Verification"
    )
    print("=" * 70)


    # =====================================================
    # SIMULATION
    # =====================================================

    backend = MujocoBackend(
        MODEL_PATH
    )


    # =====================================================
    # ROBOTS
    # =====================================================

    left_arm = ArmController(
        backend=backend,
        name="left",
        shoulder_position=[
            -0.35,
            0.0,
            0.53,
        ],
        elbow_sign=1,
    )


    right_arm = ArmController(
        backend=backend,
        name="right",
        shoulder_position=[
            0.35,
            0.0,
            0.53,
        ],
        elbow_sign=-1,
    )


    arms = {
        "left_arm": left_arm,
        "right_arm": right_arm,
    }


    # =====================================================
    # WORLD MODEL
    # =====================================================

    observer = WorldObserver(
        backend=backend,
        scenario_id=(
            "relational_demo_v1"
        ),
    )


    # =====================================================
    # NATURAL LANGUAGE
    # =====================================================

    instruction = (
        "Put the red block to the "
        "right of the blue block."
    )


    print()
    print(
        "USER INSTRUCTION:"
    )

    print(
        instruction
    )


    # =====================================================
    # PARSE
    # =====================================================

    parser = InstructionParser()


    try:

        goal = parser.parse(
            instruction
        )

    except InstructionParseError as exc:

        print(
            f"PARSING FAILED: {exc}"
        )

        return


    print()
    print("=" * 70)
    print("PARSED GOAL")
    print("=" * 70)

    print(
        goal.model_dump_json(
            indent=2
        )
    )


    # =====================================================
    # VIEWER
    # =====================================================

    with mujoco.viewer.launch_passive(
        backend.model,
        backend.data,
        show_left_ui=False,
        show_right_ui=False,
    ) as viewer:


        backend.run_for(
            1.0,
            viewer,
        )


        # =================================================
        # WORLD BEFORE
        # =================================================

        world_before = (
            observer.observe()
        )


        print()
        print("=" * 70)
        print("WORLD BEFORE")
        print("=" * 70)

        print(
            world_before.model_dump_json(
                indent=2
            )
        )


        # =================================================
        # CHECK GOAL BEFORE EXECUTION
        # =================================================

        predicate_engine = (
            PredicateEngine()
        )


        verifier = GoalVerifier(
            predicate_engine=(
                predicate_engine
            )
        )


        before_verification = (
            verifier.verify(
                goal,
                world_before,
            )
        )


        print()
        print("=" * 70)
        print("GOAL BEFORE EXECUTION")
        print("=" * 70)

        print(
            f"Satisfied: "
            f"{before_verification.satisfied}"
        )


        # =================================================
        # PLAN
        # =================================================

        planner = SymbolicPlanner()


        try:

            plan = planner.create_plan(
                goal,
                world_before,
            )

        except Exception as exc:

            print()
            print(
                f"PLANNING FAILED: "
                f"{exc}"
            )

            return


        print()
        print("=" * 70)
        print("GENERATED PLAN")
        print("=" * 70)

        print(
            plan.model_dump_json(
                indent=2
            )
        )


        # =================================================
        # VALIDATE
        # =================================================

        validator = PlanValidator()


        validation = validator.validate(
            plan,
            world_before,
        )


        print()
        print("=" * 70)
        print("PLAN VALIDATION")
        print("=" * 70)


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


            return


        print(
            "PLAN_VALID"
        )


        # =================================================
        # EXECUTE
        # =================================================

        executor = PlanExecutor(
            arms=arms,
            viewer=viewer,
        )


        execution_result = (
            executor.execute(
                plan
            )
        )


        # =================================================
        # WORLD AFTER
        # =================================================

        world_after = (
            observer.observe()
        )


        print()
        print("=" * 70)
        print("WORLD AFTER")
        print("=" * 70)

        print(
            world_after.model_dump_json(
                indent=2
            )
        )


        # =================================================
        # FINAL GOAL VERIFICATION
        # =================================================

        final_verification = (
            verifier.verify(
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
                f")"
                f" -> "
                f"{check.satisfied}"
            )


        print()


        if (
            execution_result.success
            and final_verification.satisfied
        ):

            print(
                "GOAL_SATISFIED"
            )

            print(
                "PHASE_9_SUCCESS"
            )

        else:

            print(
                "GOAL_FAILED"
            )

            print(
                "PHASE_9_FAILED"
            )


        print()
        print(
            "Close viewer to exit."
        )


        while viewer.is_running():

            backend.step(
                viewer
            )


if __name__ == "__main__":

    main()