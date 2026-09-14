import json
import os
from pathlib import Path

import requests

from dotenv import load_dotenv
from pydantic import ValidationError

from taskforge.schemas.goal import (
    ParsedGoal,
)


# =========================================================
# EXCEPTIONS
# =========================================================

class OpenRouterInterpreterError(Exception):
    pass


# =========================================================
# OPENROUTER GOAL INTERPRETER
# =========================================================

class OpenRouterGoalInterpreter:

    API_URL = (
        "https://openrouter.ai/"
        "api/v1/chat/completions"
    )


    def __init__(
        self,
        api_key=None,
        model=None,
        timeout=120,
    ):

        # =================================================
        # LOAD PROJECT .ENV
        # =================================================
        #
        # Current file:
        #
        # taskforge/
        #   taskforge/
        #       llm/
        #           openrouter_interpreter.py
        #
        # parents[2] gives us the project root:
        #
        # D:\AI Infra Summit Hackathon\taskforge
        # =================================================

        project_root = (
            Path(__file__)
            .resolve()
            .parents[2]
        )

        env_path = (
            project_root
            / ".env"
        )


        load_dotenv(
            dotenv_path=env_path,
            override=True,
        )


        # =================================================
        # API CONFIGURATION
        # =================================================

        self.api_key = (
            api_key
            or os.getenv(
                "OPENROUTER_API_KEY"
            )
        )


        self.model = (
            model
            or os.getenv(
                "OPENROUTER_MODEL",
                "openrouter/free",
            )
        )


        self.timeout = timeout


        # =================================================
        # CONFIG VALIDATION
        # =================================================

        if not self.api_key:

            raise OpenRouterInterpreterError(
                "OPENROUTER_API_KEY "
                "was not found. "
                "Add it to your project .env file."
            )


        if not self.model:

            raise OpenRouterInterpreterError(
                "OPENROUTER_MODEL "
                "was not configured."
            )


    # =====================================================
    # SYSTEM PROMPT
    # =====================================================

    def _system_prompt(
        self,
    ) -> str:

        return """
You are the language-understanding layer for TaskForge VLA,
a simulated dual-arm robotic manipulation system.

Your ONLY task is to translate the user's instruction into
a structured TaskForge goal by calling the provided
submit_taskforge_goal tool.

You do NOT:
- control motors
- generate joint angles
- generate coordinates
- execute robot actions
- invent objects
- invent predicates

CURRENT WORLD VOCABULARY

Objects:
- red_block
- blue_block

Actors:
- left_arm
- right_arm
- auto

Goal types:
- single_pick
- multi_pick
- relational

Command actions:
- pick

Relational predicates:
- left_of
- right_of
- near


RULES

1. Preserve original_instruction exactly as written by
   the user.

2. For one pick:
   goal_type = single_pick

3. For multiple picks:
   goal_type = multi_pick

4. For relational goals:
   goal_type = relational
   commands = []

5. If a pick does not specify an arm:
   actor = auto

6. For relational goals:
   desired_predicates must describe the desired relation.

7. For pick goals:
   desired_predicates = []

8. Resolve simple references such as:
   "red one" -> red_block
   "blue one" -> blue_block
   "red object" -> red_block
   "blue object" -> blue_block

9. Do not generate unsupported actions.

10. You MUST use the submit_taskforge_goal tool.


EXAMPLES

User:
Grab the red one.

Result:
goal_type = single_pick
command:
    actor = auto
    action = pick
    target = red_block


User:
Use the left arm to pick up the red block.

Result:
goal_type = single_pick
command:
    actor = left_arm
    action = pick
    target = red_block


User:
Move the red block to the left side of the blue one.

Result:
goal_type = relational
predicate:
    left_of(red_block, blue_block)


User:
Place the blue block close to the red one.

Result:
goal_type = relational
predicate:
    near(blue_block, red_block)
""".strip()


    # =====================================================
    # TOOL SCHEMA
    # =====================================================

    def _goal_tool(
        self,
    ):

        return {

            "type":
                "function",

            "function": {

                "name":
                    "submit_taskforge_goal",

                "description": (
                    "Submit a validated structured "
                    "goal for the TaskForge VLA system."
                ),

                "parameters": {

                    "type":
                        "object",

                    "properties": {

                        "original_instruction": {

                            "type":
                                "string",
                        },


                        "goal_type": {

                            "type":
                                "string",

                            "enum": [
                                "single_pick",
                                "multi_pick",
                                "relational",
                            ],
                        },


                        "commands": {

                            "type":
                                "array",

                            "items": {

                                "type":
                                    "object",

                                "properties": {

                                    "actor": {

                                        "type":
                                            "string",

                                        "enum": [
                                            "left_arm",
                                            "right_arm",
                                            "auto",
                                        ],
                                    },


                                    "action": {

                                        "type":
                                            "string",

                                        "enum": [
                                            "pick",
                                        ],
                                    },


                                    "target": {

                                        "type":
                                            "string",

                                        "enum": [
                                            "red_block",
                                            "blue_block",
                                        ],
                                    },
                                },


                                "required": [
                                    "actor",
                                    "action",
                                    "target",
                                ],


                                "additionalProperties":
                                    False,
                            },
                        },


                        "desired_predicates": {

                            "type":
                                "array",

                            "items": {

                                "type":
                                    "object",

                                "properties": {

                                    "predicate": {

                                        "type":
                                            "string",

                                        "enum": [
                                            "left_of",
                                            "right_of",
                                            "near",
                                        ],
                                    },


                                    "subject": {

                                        "type":
                                            "string",

                                        "enum": [
                                            "red_block",
                                            "blue_block",
                                        ],
                                    },


                                    "reference": {

                                        "type":
                                            "string",

                                        "enum": [
                                            "red_block",
                                            "blue_block",
                                        ],
                                    },
                                },


                                "required": [
                                    "predicate",
                                    "subject",
                                    "reference",
                                ],


                                "additionalProperties":
                                    False,
                            },
                        },
                    },


                    "required": [
                        "original_instruction",
                        "goal_type",
                        "commands",
                        "desired_predicates",
                    ],


                    "additionalProperties":
                        False,
                },
            },
        }


    # =====================================================
    # BUILD REQUEST
    # =====================================================

    def _build_payload(
        self,
        instruction,
    ):

        return {

            "model":
                self.model,


            "messages": [

                {
                    "role":
                        "system",

                    "content":
                        self._system_prompt(),
                },

                {
                    "role":
                        "user",

                    "content":
                        instruction,
                },
            ],


            # Deterministic interpretation.
            "temperature":
                0,


            # Structured communication channel.
            "tools": [
                self._goal_tool()
            ],


            # Force the model to return our goal tool.
            "tool_choice": {

                "type":
                    "function",

                "function": {

                    "name":
                        "submit_taskforge_goal",
                },
            },


            # Only route to an endpoint that accepts
            # the parameters we are sending.
            "provider": {

                "require_parameters":
                    True,
            },
        }


    # =====================================================
    # INTERPRET USER INSTRUCTION
    # =====================================================

    def interpret(
        self,
        instruction: str,
    ) -> ParsedGoal:

        instruction = (
            instruction.strip()
        )


        if not instruction:

            raise OpenRouterInterpreterError(
                "Instruction cannot be empty."
            )


        payload = (
            self._build_payload(
                instruction
            )
        )


        headers = {

            "Authorization":
                f"Bearer {self.api_key}",

            "Content-Type":
                "application/json",

            "X-Title":
                "TaskForge VLA",
        }


        # =================================================
        # API REQUEST
        # =================================================

        try:

            response = requests.post(

                self.API_URL,

                headers=headers,

                json=payload,

                timeout=self.timeout,
            )


        except requests.Timeout as exc:

            raise OpenRouterInterpreterError(
                f"OpenRouter request timed out "
                f"after {self.timeout} seconds."
            ) from exc


        except requests.RequestException as exc:

            raise OpenRouterInterpreterError(
                f"OpenRouter network error: "
                f"{exc}"
            ) from exc


        # =================================================
        # HTTP ERROR
        # =================================================

        if not response.ok:

            try:

                error_data = (
                    response.json()
                )

            except ValueError:

                error_data = (
                    response.text
                )


            raise OpenRouterInterpreterError(
                f"OpenRouter API error "
                f"{response.status_code}: "
                f"{error_data}"
            )


        # =================================================
        # RESPONSE JSON
        # =================================================

        try:

            data = (
                response.json()
            )

        except ValueError as exc:

            raise OpenRouterInterpreterError(
                "OpenRouter returned "
                "invalid response JSON."
            ) from exc


        # =================================================
        # EXTRACT MODEL MESSAGE
        # =================================================

        try:

            message = (
                data[
                    "choices"
                ][0][
                    "message"
                ]
            )

        except (
            KeyError,
            IndexError,
            TypeError,
        ) as exc:

            raise OpenRouterInterpreterError(
                "OpenRouter response did "
                "not contain a valid message."
            ) from exc


        # =================================================
        # EXTRACT TOOL CALL
        # =================================================

        tool_calls = (
            message.get(
                "tool_calls"
            )
            or []
        )


        if not tool_calls:

            raise OpenRouterInterpreterError(
                "The model returned no "
                "TaskForge goal tool call."
            )


        tool_call = (
            tool_calls[0]
        )


        try:

            function_data = (
                tool_call[
                    "function"
                ]
            )


            function_name = (
                function_data[
                    "name"
                ]
            )


            arguments_text = (
                function_data[
                    "arguments"
                ]
            )


        except (
            KeyError,
            TypeError,
        ) as exc:

            raise OpenRouterInterpreterError(
                "Malformed tool call "
                "returned by the model."
            ) from exc


        # =================================================
        # VERIFY TOOL NAME
        # =================================================

        if (
            function_name
            != "submit_taskforge_goal"
        ):

            raise OpenRouterInterpreterError(
                f"Unexpected tool call: "
                f"{function_name}"
            )


        # =================================================
        # TOOL ARGUMENTS
        # =================================================

        if isinstance(
            arguments_text,
            dict,
        ):

            raw_goal = (
                arguments_text
            )

        else:

            try:

                raw_goal = (
                    json.loads(
                        arguments_text
                    )
                )


            except (
                json.JSONDecodeError,
                TypeError,
            ) as exc:

                raise OpenRouterInterpreterError(
                    "Model returned invalid "
                    "tool argument JSON."
                ) from exc


        # =================================================
        # PYDANTIC SAFETY BOUNDARY
        # =================================================

        try:

            goal = (
                ParsedGoal.model_validate(
                    raw_goal
                )
            )


        except ValidationError as exc:

            raise OpenRouterInterpreterError(
                "LLM tool output failed "
                "ParsedGoal validation:\n"
                f"{exc}"
            ) from exc


        # =================================================
        # ORIGINAL INSTRUCTION CHECK
        # =================================================

        if (
            goal.original_instruction
            != instruction
        ):

            raise OpenRouterInterpreterError(
                "LLM changed the original "
                "instruction."
            )


        # =================================================
        # SEMANTIC CONSISTENCY
        # =================================================

        if (
            goal.goal_type
            == "relational"
        ):

            if goal.commands:

                raise OpenRouterInterpreterError(
                    "Relational goal must "
                    "not contain commands."
                )


            if (
                not goal.desired_predicates
            ):

                raise OpenRouterInterpreterError(
                    "Relational goal must "
                    "contain at least one "
                    "desired predicate."
                )


        elif goal.goal_type in (
            "single_pick",
            "multi_pick",
        ):

            if not goal.commands:

                raise OpenRouterInterpreterError(
                    "Pick goal must contain "
                    "at least one command."
                )


            if goal.desired_predicates:

                raise OpenRouterInterpreterError(
                    "Pick goal must not "
                    "contain relational "
                    "predicates."
                )


            if (
                goal.goal_type
                == "single_pick"
                and len(
                    goal.commands
                ) != 1
            ):

                raise OpenRouterInterpreterError(
                    "single_pick must contain "
                    "exactly one command."
                )


            if (
                goal.goal_type
                == "multi_pick"
                and len(
                    goal.commands
                ) < 2
            ):

                raise OpenRouterInterpreterError(
                    "multi_pick must contain "
                    "at least two commands."
                )


        else:

            raise OpenRouterInterpreterError(
                f"Unsupported goal type: "
                f"{goal.goal_type}"
            )


        # =================================================
        # RELATIONAL SANITY CHECK
        # =================================================

        for predicate in (
            goal.desired_predicates
        ):

            if (
                predicate.subject
                == predicate.reference
            ):

                raise OpenRouterInterpreterError(
                    "Relational subject and "
                    "reference cannot be "
                    "the same object."
                )


        # =================================================
        # SUCCESS
        # =================================================

        return goal