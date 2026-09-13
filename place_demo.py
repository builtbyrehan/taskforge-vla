import mujoco.viewer

from taskforge.execution.executor import (
    PlanExecutor,
)

from taskforge.robot.arm import (
    ArmController,
)

from taskforge.schemas.plan import (
    PlanStep,
    TaskPlan,
)

from taskforge.simulation.mujoco_backend import (
    MujocoBackend,
)

from taskforge.validator.plan_validator import (
    PlanValidator,
)

from taskforge.world_model.observer import (
    WorldObserver,
)


MODEL_PATH = "models/scene.xml"


def main():

    print("=" * 70)
    print("TASKFORGE VLA")
    print("Phase 8 - PICK + PLACE")
    print("=" * 70)


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
        scenario_id="place_demo_v1",
    )


    # =====================================================
    # PICK + PLACE PLAN
    # =====================================================

    plan = TaskPlan(

        plan_id="place_demo_001",

        description=(
            "Pick the red block with "
            "the left arm and place it "
            "near the center of the table."
        ),

        steps=[

            PlanStep(
                id="a1",
                actor="left_arm",
                action="pick",
                target="red_block",
            ),

            PlanStep(
                id="a2",
                actor="left_arm",
                action="place",
                target="red_block",
                position=(
                    0.05,
                    0.0,
                    0.45,
                ),
                depends_on=[
                    "a1"
                ],
            ),

            PlanStep(
                id="a3",
                actor="left_arm",
                action="move_home",
                depends_on=[
                    "a2"
                ],
            ),
        ],
    )


    print()
    print("=" * 70)
    print("PICK + PLACE PLAN")
    print("=" * 70)

    print(
        plan.model_dump_json(
            indent=2
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
        # VALIDATION
        # =================================================

        validator = (
            PlanValidator()
        )


        validation = (
            validator.validate(
                plan,
                world_before,
            )
        )


        print()
        print("=" * 70)
        print("PLAN VALIDATION")
        print("=" * 70)


        if not validation.valid:

            print(
                "PLAN_INVALID"
            )


            for issue in validation.issues:

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
        # EXECUTION
        # =================================================

        executor = PlanExecutor(
            arms=arms,
            viewer=viewer,
        )


        result = executor.execute(
            plan
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
        # FINAL VERIFICATION
        # =================================================

        red = (
            world_after.objects[
                "red_block"
            ]
        )


        position = red.position


        position_error = (
            (
                (position[0] - 0.05) ** 2
                + (position[1] - 0.0) ** 2
                + (position[2] - 0.45) ** 2
            )
            ** 0.5
        )


        released = (
            red.grasped_by is None
        )


        placed = (
            position_error <= 0.05
        )


        print()
        print("=" * 70)
        print("FINAL PLACE VERIFICATION")
        print("=" * 70)

        print(
            f"Released: {released}"
        )

        print(
            f"Position error: "
            f"{position_error * 100:.2f} cm"
        )

        print(
            f"Placed correctly: "
            f"{placed}"
        )


        if (
            result.success
            and released
            and placed
        ):

            print()
            print(
                "PHASE_8_PICK_PLACE_SUCCESS"
            )

        else:

            print()
            print(
                "PHASE_8_PICK_PLACE_FAILED"
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