import mujoco.viewer

from taskforge.execution.executor import (
    PlanExecutor,
)

from taskforge.orchestration.task_runner import (
    TaskRunner,
)

from taskforge.recovery.failure_injector import (
    FailureInjector,
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
        "Phase 13 - Failure Recovery "
        "and Replanning"
    )
    print("=" * 70)


    backend = (
        MujocoBackend(
            MODEL_PATH
        )
    )


    left_arm = (
        ArmController(
            backend=backend,
            name="left",
            shoulder_position=[
                -0.35,
                0.0,
                0.53,
            ],
            elbow_sign=1,
        )
    )


    right_arm = (
        ArmController(
            backend=backend,
            name="right",
            shoulder_position=[
                0.35,
                0.0,
                0.53,
            ],
            elbow_sign=-1,
        )
    )


    arms = {
        "left_arm":
            left_arm,

        "right_arm":
            right_arm,
    }


    observer = (
        WorldObserver(
            backend=backend,
            scenario_id=(
                "recovery_demo_v1"
            ),
        )
    )


    # =====================================================
    # CONTROLLED FAILURE
    # =====================================================
    #
    # Normal "Pick both blocks" plan:
    #
    # a1 left  pick red
    # a2 left  home
    # a3 right pick blue
    # a4 right home
    #
    # We deliberately fail a3 ONCE.
    #
    # This means TaskForge must preserve the already
    # completed red-block grasp and replan only for blue.
    # =====================================================

    failure_injector = (
        FailureInjector(
            fail_step_ids={
                "a3"
            },
            fail_once=True,
        )
    )


    instruction = (
        "Pick both blocks"
    )


    print()
    print(
        f"Instruction: "
        f"{instruction}"
    )

    print(
        "Injected failure: "
        "step a3, once"
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


        runner = (
            TaskRunner(
                observer=observer,
                arms=arms,
                viewer=viewer,
                failure_injector=(
                    failure_injector
                ),
                max_recovery_attempts=2,
            )
        )


        result = (
            runner.run(
                instruction
            )
        )


        print()
        print("=" * 70)
        print(
            "PHASE 13 RESULT"
        )
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
        print("=" * 70)


        if (
            result.success
            and
            result.status
            == "RECOVERY_SUCCESS"
        ):

            print(
                "PHASE_13_SUCCESS"
            )

        else:

            print(
                "PHASE_13_FAILED"
            )


        print("=" * 70)

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