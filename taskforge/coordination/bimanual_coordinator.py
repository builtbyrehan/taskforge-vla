from dataclasses import dataclass

import numpy as np

from taskforge.robot.ik import (
    solve_planar_ik,
)


# =========================================================
# EXCEPTION
# =========================================================

class BimanualCoordinationError(ValueError):
    pass


# =========================================================
# REACHABILITY REPORT
# =========================================================

@dataclass
class ArmReachability:

    actor: str

    pick_reachable: bool

    place_reachable: bool | None = None

    score: float | None = None


# =========================================================
# BIMANUAL COORDINATOR
# =========================================================

class BimanualCoordinator:

    # Same waypoint geometry currently used by arm.py.
    PICK_PREGRASP_HEIGHT = 0.22
    PICK_GRASP_HEIGHT = 0.12
    PICK_LIFT_HEIGHT = 0.24

    # Approximate placement EE geometry.
    # Exact attachment offset is known only after grasp.
    PLACE_EE_HEIGHT = 0.12
    PLACE_PREPLACE_EXTRA = 0.15

    # Current arms are planar.
    PLANAR_Y_TOLERANCE = 0.08


    def __init__(
        self,
        arms,
    ):

        self.arms = arms


    # =====================================================
    # BASIC CHECKS
    # =====================================================

    def _require_actor(
        self,
        actor,
    ):

        if actor not in self.arms:

            raise BimanualCoordinationError(
                f"Unknown robot actor: "
                f"{actor}"
            )


    def _require_object(
        self,
        target,
        world,
    ):

        if target not in world.objects:

            raise BimanualCoordinationError(
                f"Unknown world object: "
                f"{target}"
            )


        return world.objects[
            target
        ]


    # =====================================================
    # JOINT LIMIT CHECK
    # =====================================================

    def _joint_angle_allowed(
        self,
        arm,
        joint_name,
        angle,
    ):

        joint_id = (
            arm.backend.joint_id(
                joint_name
            )
        )


        model = (
            arm.backend.model
        )


        limited = bool(
            model.jnt_limited[
                joint_id
            ]
        )


        if not limited:

            return True


        low, high = (
            model.jnt_range[
                joint_id
            ]
        )


        return (
            float(low) - 1e-6
            <= float(angle)
            <= float(high) + 1e-6
        )


    # =====================================================
    # GENERIC REACHABILITY
    # =====================================================

    def _can_reach(
        self,
        actor,
        target,
    ):

        self._require_actor(
            actor
        )


        arm = (
            self.arms[
                actor
            ]
        )


        target = (
            np.asarray(
                target,
                dtype=float,
            )
        )


        # Current temporary robot is planar.
        y_error = abs(
            float(
                target[1]
                - arm.shoulder_position[1]
            )
        )


        if (
            y_error
            > self.PLANAR_Y_TOLERANCE
        ):

            return False


        try:

            shoulder, elbow = (
                solve_planar_ik(
                    target,
                    arm.shoulder_position,
                    arm.elbow_sign,
                )
            )


        except ValueError:

            return False


        shoulder_ok = (
            self._joint_angle_allowed(
                arm,
                arm.shoulder_joint,
                shoulder,
            )
        )


        elbow_ok = (
            self._joint_angle_allowed(
                arm,
                arm.elbow_joint,
                elbow,
            )
        )


        return (
            shoulder_ok
            and elbow_ok
        )


    # =====================================================
    # REACHABILITY SCORE
    # =====================================================

    def _distance_score(self,actor,target,):

        """
    Return a posture-quality score.

    Lower is better.

    We do NOT simply prefer the physically closest arm,
    because a very close target can require a highly
    folded elbow configuration.

    Instead we prefer a more stable, reasonably extended
    posture while avoiding near-singular full extension.
    """

        arm = (
            self.arms[
            actor
        ]
        )

        target = (
            np.asarray(
            target,
            dtype=float,
        )
    )

        try:

            shoulder, elbow = (
                solve_planar_ik(
                target,
                arm.shoulder_position,
                arm.elbow_sign,
            )
            )

        except ValueError:

            return float("inf")


        shoulder_cost = (
            0.15
            * abs(
            float(shoulder)
        )
        )


        elbow_cost = abs(
            float(elbow)
    )


    # Very small elbow angles mean the arm is close
    # to full extension / a singular configuration.
        singularity_penalty = 0.0

        if elbow_cost < 0.15:

                singularity_penalty = (
                0.15 - elbow_cost
            ) * 5.0


        return float(
            elbow_cost
            + shoulder_cost
            + singularity_penalty
     )

    # =====================================================
    # PICK WAYPOINTS
    # =====================================================

    def _pick_waypoints(
        self,
        object_position,
    ):

        object_position = (
            np.asarray(
                object_position,
                dtype=float,
            )
        )


        x = object_position[0]
        y = object_position[1]
        z = object_position[2]


        pregrasp = np.array(
            [
                x,
                y,
                z
                + self.PICK_PREGRASP_HEIGHT,
            ],
            dtype=float,
        )


        grasp = np.array(
            [
                x,
                y,
                z
                + self.PICK_GRASP_HEIGHT,
            ],
            dtype=float,
        )


        lift = np.array(
            [
                x,
                y,
                z
                + self.PICK_LIFT_HEIGHT,
            ],
            dtype=float,
        )


        return (
            pregrasp,
            grasp,
            lift,
        )


    # =====================================================
    # PLACE WAYPOINTS
    # =====================================================

    def _place_waypoints(
        self,
        target_position,
    ):

        target_position = (
            np.asarray(
                target_position,
                dtype=float,
            )
        )


        placement_ee = (
            target_position.copy()
        )


        placement_ee[2] += (
            self.PLACE_EE_HEIGHT
        )


        preplace_ee = (
            placement_ee.copy()
        )


        preplace_ee[2] += (
            self.PLACE_PREPLACE_EXTRA
        )


        return (
            preplace_ee,
            placement_ee,
        )


    # =====================================================
    # WAYPOINT SET CHECK
    # =====================================================

    def _waypoints_reachable(
        self,
        actor,
        waypoints,
    ):

        return all(

            self._can_reach(
                actor,
                waypoint,
            )

            for waypoint
            in waypoints
        )


    def _waypoint_score(
        self,
        actor,
        waypoints,
    ):

        if not self._waypoints_reachable(
            actor,
            waypoints,
        ):

            return float(
                "inf"
            )


        return max(

            self._distance_score(
                actor,
                waypoint,
            )

            for waypoint
            in waypoints
        )


    # =====================================================
    # PICK EVALUATION
    # =====================================================

    def evaluate_pick(
        self,
        actor,
        target,
        world,
    ) -> ArmReachability:

        self._require_actor(
            actor
        )


        obj = (
            self._require_object(
                target,
                world,
            )
        )


        waypoints = (
            self._pick_waypoints(
                obj.position
            )
        )


        reachable = (
            self._waypoints_reachable(
                actor,
                waypoints,
            )
        )


        score = None


        if reachable:

            score = (
                self._waypoint_score(
                    actor,
                    waypoints,
                )
            )


        return ArmReachability(
            actor=actor,
            pick_reachable=reachable,
            score=score,
        )


    # =====================================================
    # PICK + PLACE EVALUATION
    # =====================================================

    def evaluate_pick_and_place(
        self,
        actor,
        target,
        target_position,
        world,
    ) -> ArmReachability:

        self._require_actor(
            actor
        )


        obj = (
            self._require_object(
                target,
                world,
            )
        )


        pick_waypoints = (
            self._pick_waypoints(
                obj.position
            )
        )


        place_waypoints = (
            self._place_waypoints(
                target_position
            )
        )


        pick_reachable = (
            self._waypoints_reachable(
                actor,
                pick_waypoints,
            )
        )


        place_reachable = (
            self._waypoints_reachable(
                actor,
                place_waypoints,
            )
        )


        score = None


        if (
            pick_reachable
            and place_reachable
        ):

            score = (
                self._waypoint_score(
                    actor,
                    pick_waypoints,
                )
                +
                self._waypoint_score(
                    actor,
                    place_waypoints,
                )
            )


        return ArmReachability(
            actor=actor,
            pick_reachable=(
                pick_reachable
            ),
            place_reachable=(
                place_reachable
            ),
            score=score,
        )


    # =====================================================
    # PRINT REPORTS
    # =====================================================

    def _print_pick_report(
        self,
        target,
        reports,
    ):

        print()
        print("=" * 70)
        print(
            "BIMANUAL COORDINATOR"
        )
        print("=" * 70)


        print(
            f"Target: {target}"
        )


        for report in reports:

            score = (
                f"{report.score:.3f}"
                if report.score
                is not None
                else "N/A"
            )


            print(
                f"{report.actor}: "
                f"pick_reachable="
                f"{report.pick_reachable}, "
                f"score={score}"
            )


    def _print_pick_place_report(
        self,
        target,
        target_position,
        reports,
    ):

        print()
        print("=" * 70)
        print(
            "BIMANUAL COORDINATOR"
        )
        print("=" * 70)


        print(
            f"Object: {target}"
        )


        print(
            f"Destination: "
            f"{np.round(
                np.asarray(
                    target_position,
                    dtype=float,
                ),
                3,
            )}"
        )


        for report in reports:

            score = (
                f"{report.score:.3f}"
                if report.score
                is not None
                else "N/A"
            )


            print(
                f"{report.actor}: "
                f"pick="
                f"{report.pick_reachable}, "
                f"place="
                f"{report.place_reachable}, "
                f"score={score}"
            )


    # =====================================================
    # SELECT ARM FOR PICK
    # =====================================================

    def select_actor_for_pick(
        self,
        requested_actor,
        target,
        world,
        reserved_actors=None,
    ):

        reserved_actors = set(
            reserved_actors
            or []
        )


        # =================================================
        # EXPLICIT USER REQUEST
        # =================================================

        if requested_actor != "auto":

            self._require_actor(
                requested_actor
            )


            if (
                requested_actor
                in reserved_actors
            ):

                raise BimanualCoordinationError(
                    f"{requested_actor} is "
                    f"already assigned to "
                    f"another object."
                )


            report = (
                self.evaluate_pick(
                    requested_actor,
                    target,
                    world,
                )
            )


            self._print_pick_report(
                target,
                [report],
            )


            if not report.pick_reachable:

                raise BimanualCoordinationError(
                    f"{requested_actor} "
                    f"cannot safely reach "
                    f"{target}."
                )


            print(
                f"SELECTED_ACTOR: "
                f"{requested_actor}"
            )


            return requested_actor


        # =================================================
        # AUTOMATIC SELECTION
        # =================================================

        reports = []


        for actor in self.arms:

            if actor in reserved_actors:
                continue


            reports.append(

                self.evaluate_pick(
                    actor,
                    target,
                    world,
                )
            )


        self._print_pick_report(
            target,
            reports,
        )


        candidates = [

            report

            for report
            in reports

            if report.pick_reachable
        ]


        if not candidates:

            raise BimanualCoordinationError(
                f"No available arm can "
                f"reach {target}."
            )


        selected = min(
            candidates,
            key=lambda report: (
                report.score
                if report.score
                is not None
                else float("inf")
            ),
        )


        print(
            f"SELECTED_ACTOR: "
            f"{selected.actor}"
        )


        return selected.actor


    # =====================================================
    # SELECT ARM FOR PICK + PLACE
    # =====================================================

    def select_actor_for_pick_and_place(
        self,
        requested_actor,
        target,
        target_position,
        world,
    ):

        # =================================================
        # EXPLICIT ACTOR
        # =================================================

        if requested_actor != "auto":

            report = (
                self.evaluate_pick_and_place(
                    requested_actor,
                    target,
                    target_position,
                    world,
                )
            )


            self._print_pick_place_report(
                target,
                target_position,
                [report],
            )


            if (
                not report.pick_reachable
                or
                not report.place_reachable
            ):

                raise BimanualCoordinationError(
                    f"{requested_actor} cannot "
                    f"safely complete the "
                    f"pick-and-place task."
                )


            print(
                f"SELECTED_ACTOR: "
                f"{requested_actor}"
            )


            return requested_actor


        # =================================================
        # AUTOMATIC ACTOR
        # =================================================

        reports = []


        for actor in self.arms:

            reports.append(

                self.evaluate_pick_and_place(
                    actor,
                    target,
                    target_position,
                    world,
                )
            )


        self._print_pick_place_report(
            target,
            target_position,
            reports,
        )


        candidates = [

            report

            for report
            in reports

            if (
                report.pick_reachable
                and
                report.place_reachable
            )
        ]


        if not candidates:

            raise BimanualCoordinationError(
                f"No arm can safely pick "
                f"{target} and reach the "
                f"requested destination."
            )


        selected = min(
            candidates,
            key=lambda report: (
                report.score
                if report.score
                is not None
                else float("inf")
            ),
        )


        print(
            f"SELECTED_ACTOR: "
            f"{selected.actor}"
        )


        return selected.actor


    # =====================================================
    # MULTI-OBJECT BIMANUAL ASSIGNMENT
    # =====================================================

    def assign_pick_commands(
        self,
        commands,
        world,
    ):

        assignments = [
            None
        ] * len(commands)


        reserved_actors = set()

        seen_targets = set()


        # =================================================
        # DUPLICATE TARGET CHECK
        # =================================================

        for command in commands:

            if (
                command.target
                in seen_targets
            ):

                raise BimanualCoordinationError(
                    f"Duplicate pick target: "
                    f"{command.target}"
                )


            seen_targets.add(
                command.target
            )


        # =================================================
        # EXPLICIT ACTORS FIRST
        # =================================================

        for index, command in enumerate(
            commands
        ):

            if (
                command.actor
                == "auto"
            ):

                continue


            actor = (
                self.select_actor_for_pick(
                    command.actor,
                    command.target,
                    world,
                    reserved_actors,
                )
            )


            assignments[
                index
            ] = actor


            reserved_actors.add(
                actor
            )


        # =================================================
        # AUTO ASSIGN REMAINING COMMANDS
        # =================================================

        for index, command in enumerate(
            commands
        ):

            if (
                assignments[
                    index
                ]
                is not None
            ):

                continue


            actor = (
                self.select_actor_for_pick(
                    "auto",
                    command.target,
                    world,
                    reserved_actors,
                )
            )


            assignments[
                index
            ] = actor


            reserved_actors.add(
                actor
            )


        print()
        print("=" * 70)
        print(
            "FINAL BIMANUAL ASSIGNMENT"
        )
        print("=" * 70)


        for command, actor in zip(
            commands,
            assignments,
        ):

            print(
                f"{actor} -> "
                f"{command.target}"
            )


        return assignments