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
        "Phase 10 - Goal-Aware "
        "Task Orchestration"
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
            "orchestrator_demo_v1"
        ),
    )


    # =====================================================
    # USER GOAL
    # =====================================================

    instruction = (
        "Put the red block to the "
        "left of the blue block."
    )


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


        runner = TaskRunner(
            observer=observer,
            arms=arms,
            viewer=viewer,
        )


        result = runner.run(
            instruction
        )


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


        print()


        if result.success:

            print(
                "PHASE_10_SUCCESS"
            )

        else:

            print(
                "PHASE_10_FAILED"
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