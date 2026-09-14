class RecoveryManager:
    """
    Builds a residual goal from the CURRENT observed world.

    Completed parts of a multi-pick goal are removed so
    TaskForge does not repeat successful work after failure.
    """

    def build_residual_goal(
        self,
        goal,
        world,
    ):

        # Relational goals are still evaluated against the
        # desired final predicate. For now they can simply
        # be replanned from the latest world state.
        if goal.goal_type == "relational":

            print(
                "RECOVERY: relational goal "
                "still requires final predicate."
            )

            return goal


        remaining_commands = []


        for command in goal.commands:

            if command.target not in world.objects:

                remaining_commands.append(
                    command
                )

                continue


            obj = world.objects[
                command.target
            ]


            holder = (
                obj.grasped_by
            )


            # =============================================
            # AUTO ACTOR
            # =============================================

            if command.actor == "auto":

                satisfied = (
                    holder is not None
                )


            # =============================================
            # EXPLICIT ACTOR
            # =============================================

            else:

                satisfied = (
                    holder
                    == command.actor
                )


            if satisfied:

                print(
                    f"RECOVERY: skipping "
                    f"{command.target} "
                    f"- already grasped by "
                    f"{holder}"
                )

            else:

                remaining_commands.append(
                    command
                )


        # =================================================
        # EVERYTHING ALREADY ACHIEVED
        # =================================================

        if not remaining_commands:

            return None


        # =================================================
        # BUILD RESIDUAL GOAL
        # =================================================

        residual_type = (
            "single_pick"
            if len(
                remaining_commands
            ) == 1
            else "multi_pick"
        )


        residual_goal = (
            goal.model_copy(
                update={
                    "goal_type":
                        residual_type,

                    "commands":
                        remaining_commands,
                }
            )
        )


        print()
        print(
            "RESIDUAL GOAL CREATED"
        )

        print(
            residual_goal.model_dump_json(
                indent=2
            )
        )


        return residual_goal