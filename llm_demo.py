from taskforge.llm.openrouter_interpreter import (
    OpenRouterGoalInterpreter,
    OpenRouterInterpreterError,
)



def main():

    print("=" * 70)
    print("TASKFORGE VLA")
    print(
        "Phase 11A - "
        "OpenRouter Goal Interpreter"
    )
    print("=" * 70)


    # =====================================================
    # CREATE INTERPRETER
    # =====================================================

    try:

        interpreter = (
            OpenRouterGoalInterpreter()
        )

    except OpenRouterInterpreterError as exc:

        print()
        print(
            "INITIALIZATION FAILED"
        )

        print(
            str(exc)
        )

        return


    print()
    print(
        f"Model: "
        f"{interpreter.model}"
    )


    # =====================================================
    # USER INPUT
    # =====================================================

    print()
    print(
        "Try natural language such as:"
    )

    print(
        '- "Grab the red one."'
    )

    print(
        '- "Use the left arm to '
        'pick up the red block."'
    )

    print(
        '- "Move the red block '
        'over to the left side '
        'of the blue one."'
    )

    print(
        '- "Put the blue block '
        'close to the red block."'
    )

    print()


    instruction = input(
        "TaskForge LLM > "
    ).strip()


    if not instruction:

        instruction = (
            "Move the red block "
            "over to the left side "
            "of the blue one."
        )


    print()
    print("=" * 70)
    print("USER INSTRUCTION")
    print("=" * 70)

    print(
        instruction
    )


    # =====================================================
    # CALL OPENROUTER
    # =====================================================

    print()
    print(
        "Calling OpenRouter..."
    )


    try:

        goal = interpreter.interpret(
            instruction
        )


    except OpenRouterInterpreterError as exc:

        print()
        print("=" * 70)
        print("LLM INTERPRETATION FAILED")
        print("=" * 70)

        print(
            str(exc)
        )

        return


    # =====================================================
    # SUCCESS
    # =====================================================

    print()
    print("=" * 70)
    print("VALIDATED LLM GOAL")
    print("=" * 70)

    print(
        goal.model_dump_json(
            indent=2
        )
    )


    print()
    print(
        "LLM_SCHEMA_VALIDATION_SUCCESS"
    )

    print()
    print(
        "Robot was NOT executed."
    )


if __name__ == "__main__":

    main()