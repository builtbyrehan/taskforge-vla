import argparse

import mujoco.viewer

from taskforge.orchestration.task_runner import TaskRunner
from taskforge.recovery.failure_injector import FailureInjector
from taskforge.robot.arm import ArmController
from taskforge.simulation.mujoco_backend import MujocoBackend
from taskforge.world_model.observer import WorldObserver


MODEL_PATH = "models/scene.xml"


def build_runtime(inject_failure=False):
    backend = MujocoBackend(
        MODEL_PATH
    )

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

    observer = WorldObserver(
        backend=backend,
        scenario_id="viewer_demo_v1",
    )

    failure_injector = None

    if inject_failure:
        failure_injector = FailureInjector(
            fail_step_ids={"a3"},
            fail_once=True,
        )

    return (
        backend,
        arms,
        observer,
        failure_injector,
    )


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Run TaskForge with the live MuJoCo viewer."
        )
    )

    parser.add_argument(
        "--instruction",
        type=str,
        default=None,
        help=(
            "Natural-language manipulation instruction."
        ),
    )

    parser.add_argument(
        "--failure",
        action="store_true",
        help=(
            "Inject the Phase 13 recoverable failure "
            "at step a3 once."
        ),
    )

    args = parser.parse_args()

    instruction = (
        args.instruction
        or input(
            "TaskForge > "
        ).strip()
    )

    if not instruction:
        raise SystemExit(
            "No instruction provided."
        )

    (
        backend,
        arms,
        observer,
        failure_injector,
    ) = build_runtime(
        inject_failure=args.failure
    )

    print()
    print("=" * 70)
    print("TASKFORGE VLA - LIVE MUJOCO DEMO")
    print("=" * 70)

    print(
        f"Instruction: {instruction}"
    )

    print(
        "Failure injection: "
        + (
            "ON"
            if args.failure
            else "OFF"
        )
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
            failure_injector=failure_injector,
            max_recovery_attempts=2,
        )

        result = runner.run(
            instruction
        )

        print()
        print("=" * 70)
        print("LIVE DEMO RESULT")
        print("=" * 70)

        print(
            f"Success: {result.success}"
        )

        print(
            f"Status: {result.status}"
        )

        print(
            f"Message: {result.message}"
        )

        print()
        print(
            "Final simulation state is now visible."
        )

        print(
            "Close the MuJoCo viewer to exit."
        )

        while viewer.is_running():
            backend.step(
                viewer
            )


if __name__ == "__main__":
    main()
