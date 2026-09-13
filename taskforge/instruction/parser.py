import re

from taskforge.schemas.goal import (
    GoalCommand,
    GoalPredicate,
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
    # NORMALIZATION
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

        # Remove punctuation that is not useful
        instruction = re.sub(
            r"[.!?,]",
            "",
            instruction,
        )

        instruction = re.sub(
            r"\s+",
            " ",
            instruction,
        )

        return instruction


    # =====================================================
    # OBJECT HELPERS
    # =====================================================

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


    def _find_objects_in_order(
        self,
        text: str,
    ):

        matches = []

        used_object_ids = set()


        for phrase, object_id in (
            self.object_aliases.items()
        ):

            for match in re.finditer(
                re.escape(phrase),
                text,
            ):

                matches.append(
                    (
                        match.start(),
                        object_id,
                    )
                )


        matches.sort(
            key=lambda item: item[0]
        )


        objects = []


        for _, object_id in matches:

            if (
                object_id
                in used_object_ids
            ):

                continue

            objects.append(
                object_id
            )

            used_object_ids.add(
                object_id
            )


        return objects


    # =====================================================
    # ACTOR
    # =====================================================

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
    # RELATIONAL PARSER
    # =====================================================

    def _parse_relational(
        self,
        normalized: str,
        original_instruction: str,
    ):

        relation = None


        if "right of" in normalized:

            relation = "right_of"

        elif "left of" in normalized:

            relation = "left_of"

        elif (
            "near" in normalized
            or "close to" in normalized
        ):

            relation = "near"


        if relation is None:

            return None


        objects = (
            self._find_objects_in_order(
                normalized
            )
        )


        if len(objects) < 2:

            raise InstructionParseError(
                "A relational instruction "
                "requires two objects."
            )


        subject = objects[0]

        reference = objects[1]


        if subject == reference:

            raise InstructionParseError(
                "Subject and reference "
                "cannot be the same object."
            )


        return ParsedGoal(

            original_instruction=(
                original_instruction
            ),

            goal_type="relational",

            desired_predicates=[

                GoalPredicate(
                    predicate=relation,
                    subject=subject,
                    reference=reference,
                )
            ],
        )


    # =====================================================
    # MAIN PARSER
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
        # TRY RELATIONAL GOAL FIRST
        # =================================================

        relational_goal = (
            self._parse_relational(
                normalized,
                instruction,
            )
        )


        if relational_goal is not None:

            return relational_goal


        # =================================================
        # PICK BOTH BLOCKS
        # =================================================

        if (
            "pick both blocks"
            in normalized
        ):

            return ParsedGoal(

                original_instruction=(
                    instruction
                ),

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
        # NORMAL PICK COMMANDS
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


            if "pick" not in part:

                raise InstructionParseError(
                    f"Unsupported command: "
                    f"'{part}'."
                )


            target = self._find_object(
                part
            )


            if target is None:

                raise InstructionParseError(
                    f"Could not identify "
                    f"an object in: "
                    f"'{part}'"
                )


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

            original_instruction=(
                instruction
            ),

            goal_type=goal_type,

            commands=commands,
        )