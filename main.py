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

from taskforge.world_model.observer import (
    WorldObserver,
)


MODEL_PATH = "models/scene.xml"


def main():

    print("=" * 70)
    print("TASKFORGE VLA")
    print(
        "Phase 7 - Natural Language "
        "+ Symbolic Planning"
    )
    print("=" * 70)


    # =====================================================
    # SIMULATION
    # =====================================================

    backend = MujocoBackend(
        MODEL_PATH
    )


    # =====================================================
    # ROBOT CONTROLLERS
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

        "left_arm":
            left_arm,

        "right_arm":
            right_arm,
    }


    # =====================================================
    # WORLD MODEL
    # =====================================================

    observer = WorldObserver(

        backend=backend,

        scenario_id=(
            "dual_block_v1"
        ),
    )


    # =====================================================
    # NATURAL LANGUAGE INPUT
    # =====================================================

    print()
    print("Enter a robot instruction.")

    print()

    print(
        "Example:"
    )

    print(
        "Pick the red block with "
        "the left arm and pick the "
        "blue block with the right arm."
    )

    print()


    instruction = input(
        "TaskForge > "
    ).strip()


    # Default demo instruction

    if not instruction:

        instruction = (
            "Pick the red block with "
            "the left arm and pick the "
            "blue block with the "
            "right arm."
        )


    print()
    print(
        f"USER INSTRUCTION:"
    )

    print(
        instruction
    )


    # =====================================================
    # INSTRUCTION PARSER
    # =====================================================

    parser = InstructionParser()


    try:

        goal = parser.parse(
            instruction
        )

    except InstructionParseError as exc:

        print()
        print("=" * 70)
        print("INSTRUCTION REJECTED")
        print("=" * 70)

        print(
            str(exc)
        )

        return


    # =====================================================
    # PRINT STRUCTURED GOAL
    # =====================================================

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
    # SYMBOLIC PLANNER
    # =====================================================

    planner = SymbolicPlanner()


    try:

        plan = planner.create_plan(
            goal
        )

    except Exception as exc:

        print()
        print("=" * 70)
        print("PLANNING FAILED")
        print("=" * 70)

        print(
            str(exc)
        )

        return


    # =====================================================
    # PRINT PLAN
    # =====================================================

    print()
    print("=" * 70)
    print("GENERATED PLAN")
    print("=" * 70)

    print(
        plan.model_dump_json(
            indent=2
        )
    )


    # =====================================================
    # MUJOCO VIEWER
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
        # OBSERVE WORLD
        # =================================================

        world_before = (
            observer.observe()
        )


        print()
        print("=" * 70)
        print("WORLD BEFORE PLAN")
        print("=" * 70)

        print(
            world_before.model_dump_json(
                indent=2
            )
        )


        # =================================================
        # VALIDATE PLAN
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


            print()
            print(
                "Execution blocked."
            )

            return


        print(
            "PLAN_VALID"
        )


        # =================================================
        # EXECUTE PLAN
        # =================================================

        executor = PlanExecutor(

            arms=arms,

            viewer=viewer,
        )


        result = executor.execute(
            plan
        )


        # =================================================
        # OBSERVE AFTER
        # =================================================

        world_after = (
            observer.observe()
        )


        print()
        print("=" * 70)
        print("WORLD AFTER PLAN")
        print("=" * 70)

        print(
            world_after.model_dump_json(
                indent=2
            )
        )


        # =================================================
        # FINAL RESULT
        # =================================================

        print()
        print("=" * 70)
        print("EXECUTION RESULT")
        print("=" * 70)

        print(
            result.model_dump_json(
                indent=2
            )
        )


        if result.success:

            print()
            print(
                "TASKFORGE SUCCESS"
            )

        else:

            print()
            print(
                "TASKFORGE FAILURE"
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