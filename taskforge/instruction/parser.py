import re

from taskforge.schemas.goal import (
    GoalCommand,
    ParsedGoal,
)


class InstructionParseError(Exception):
    pass


class InstructionParser:

    def __init__(self):

        self.object_aliases = {
            "red block": "red_block",
            "red_block": "red_block",

            "blue block": "blue_block",
            "blue_block": "blue_block",
        }

        self.actor_aliases = {
            "left arm": "left_arm",
            "left_arm": "left_arm",

            "right arm": "right_arm",
            "right_arm": "right_arm",
        }


    # =====================================================
    # HELPERS
    # =====================================================

    def _normalize(
        self,
        instruction: str,
    ) -> str:

        instruction = (
            instruction
            .strip()
            .lower()
        )

        instruction = re.sub(
            r"\s+",
            " ",
            instruction,
        )

        return instruction


    def _find_object(
        self,
        text: str,
    ):

        for phrase, object_id in (
            self.object_aliases.items()
        ):

            if phrase in text:
                return object_id

        return None


    def _find_actor(
        self,
        text: str,
    ):

        for phrase, actor_id in (
            self.actor_aliases.items()
        ):

            if phrase in text:
                return actor_id

        return None


    # =====================================================
    # PARSER
    # =====================================================

    def parse(
        self,
        instruction: str,
    ) -> ParsedGoal:

        normalized = self._normalize(
            instruction
        )


        if not normalized:

            raise InstructionParseError(
                "Instruction cannot be empty."
            )


        # =================================================
        # SPECIAL CASE:
        # PICK BOTH BLOCKS
        # =================================================

        if (
            "pick both blocks"
            in normalized
        ):

            return ParsedGoal(

                original_instruction=instruction,

                goal_type="multi_pick",

                commands=[

                    GoalCommand(
                        actor="auto",
                        action="pick",
                        target="red_block",
                    ),

                    GoalCommand(
                        actor="auto",
                        action="pick",
                        target="blue_block",
                    ),
                ],
            )


        # =================================================
        # SPLIT MULTI-COMMAND INSTRUCTION
        # =================================================

        parts = re.split(
            r"\s+(?:and|then)\s+",
            normalized,
        )


        commands = []


        for part in parts:

            part = part.strip()

            if not part:
                continue


            # ---------------------------------------------
            # ACTION
            # ---------------------------------------------

            if "pick" not in part:

                raise InstructionParseError(
                    f"Unsupported command: "
                    f"'{part}'. "
                    f"Only PICK is currently supported."
                )


            # ---------------------------------------------
            # OBJECT
            # ---------------------------------------------

            target = self._find_object(
                part
            )

            if target is None:

                raise InstructionParseError(
                    f"Could not identify an "
                    f"object in: '{part}'"
                )


            # ---------------------------------------------
            # ACTOR
            # ---------------------------------------------

            actor = self._find_actor(
                part
            )

            if actor is None:

                actor = "auto"


            commands.append(

                GoalCommand(
                    actor=actor,
                    action="pick",
                    target=target,
                )
            )


        if not commands:

            raise InstructionParseError(
                "No executable commands "
                "were found."
            )


        goal_type = (
            "single_pick"
            if len(commands) == 1
            else "multi_pick"
        )


        return ParsedGoal(

            original_instruction=instruction,

            goal_type=goal_type,

            commands=commands,
        )