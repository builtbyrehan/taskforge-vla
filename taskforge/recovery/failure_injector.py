class FailureInjector:
    """
    Controlled failure injection for TaskForge demos/tests.

    This does NOT damage the simulator or robot state.
    It simply prevents a selected plan step from executing
    and reports that step as failed.

    By default each configured failure happens only once,
    allowing the recovery plan to succeed afterward.
    """

    def __init__(
        self,
        fail_step_ids=None,
        fail_actions=None,
        fail_once=True,
    ):

        self.fail_step_ids = set(
            fail_step_ids or []
        )

        self.fail_actions = set(
            fail_actions or []
        )

        self.fail_once = fail_once

        self.triggered = set()


    # =====================================================
    # SHOULD THIS STEP FAIL?
    # =====================================================

    def should_fail(
        self,
        step,
    ) -> bool:

        step_match = (
            step.id in self.fail_step_ids
        )

        action_match = (
            step.action in self.fail_actions
        )


        if not (
            step_match
            or action_match
        ):

            return False


        failure_key = (
            step.id,
            step.actor,
            step.action,
            step.target,
        )


        if (
            self.fail_once
            and failure_key
            in self.triggered
        ):

            return False


        self.triggered.add(
            failure_key
        )


        return True


    # =====================================================
    # FAILURE MESSAGE
    # =====================================================

    def failure_message(
        self,
        step,
    ) -> str:

        return (
            "INJECTED_FAILURE: "
            f"forced failure for "
            f"step={step.id}, "
            f"actor={step.actor}, "
            f"action={step.action}, "
            f"target={step.target}"
        )


    # =====================================================
    # RESET
    # =====================================================

    def reset(
        self,
    ):

        self.triggered.clear()