import mujoco.viewer

from taskforge.orchestration.task_runner import (
    TaskRunner,
)

from taskforge.robot.arm import (
    ArmController,
)

from taskforge.simulation.mujoco_backend import (
    MujocoBackend,
)

from taskforge.world_model.observer import (
    WorldObserver,
)


MODEL_PATH = "models/scene.xml"


def main():

    print("=" * 70)
    print("TASKFORGE VLA")
    print(
        "Phase 12 - Reachability-Aware "
        "Bimanual Task Orchestration"
    )
    print("=" * 70)


    # =====================================================
    # SIMULATION
    # =====================================================

    backend = MujocoBackend(
        MODEL_PATH
    )


    # =====================================================
    # ARMS
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
            "llm_orchestrator_demo_v1"
        ),
    )


    # =====================================================
    # USER INSTRUCTION
    # =====================================================

    print()
    print("Example instructions:")
    print(
        '- "Move the red block to the '
        'left side of the blue one"'
    )
    print(
        '- "Put the red block to the '
        'right of the blue block"'
    )
    print(
        '- "Put the red block near '
        'the blue one"'
    )
    print()

    instruction = input(
        "TaskForge > "
    ).strip()


    # Default instruction if user presses Enter.
    if not instruction:

        instruction = (
            "Move the red block to the "
            "left side of the blue one"
        )


    print()
    print(
        f"Selected instruction: "
        f"{instruction}"
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


        # Let MuJoCo settle before observing.
        backend.run_for(
            1.0,
            viewer,
        )


        # =================================================
        # TASK RUNNER
        # =================================================

        runner = TaskRunner(
            observer=observer,
            arms=arms,
            viewer=viewer,
        )


        # =================================================
        # END-TO-END TASK
        # =================================================

        result = runner.run(
            instruction
        )


        # =================================================
        # RESULT
        # =================================================

        print()
        print("=" * 70)
        print("TASK RUN RESULT")
        print("=" * 70)


        print(
            f"Success: "
            f"{result.success}"
        )


        print(
            f"Status: "
            f"{result.status}"
        )


        print(
            f"Message: "
            f"{result.message}"
        )


        print(
            f"Interpretation source: "
            f"{result.interpretation_source}"
        )


        # =================================================
        # GOAL
        # =================================================

        if result.goal is not None:

            print()
            print("FINAL PARSED GOAL")
            print("-" * 70)

            print(
                result.goal.model_dump_json(
                    indent=2
                )
            )


        # =================================================
        # PLAN
        # =================================================

        if result.plan is not None:

            print()
            print("EXECUTED PLAN")
            print("-" * 70)

            print(
                result.plan.model_dump_json(
                    indent=2
                )
            )


        # =================================================
        # FINAL STATUS
        # =================================================

        print()
        print("=" * 70)


        if result.success:

            print(
                "PHASE_12B_SUCCESS"
            )

        else:

            print(
                "PHASE_12B_FAILED"
            )


        print("=" * 70)


        # =================================================
        # KEEP VIEWER OPEN
        # =================================================

        print()
        print(
            "Close the MuJoCo viewer "
            "to exit."
        )


        while viewer.is_running():

            backend.step(
                viewer
            )


if __name__ == "__main__":

    main()