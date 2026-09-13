import numpy as np

from taskforge.schemas.world import WorldState


class PredicateEngine:

    def __init__(
        self,
        left_right_tolerance=0.05,
        near_threshold=0.20,
    ):

        self.left_right_tolerance = (
            left_right_tolerance
        )

        self.near_threshold = (
            near_threshold
        )


    # =====================================================
    # HELPERS
    # =====================================================

    def _object(
        self,
        world: WorldState,
        object_id: str,
    ):

        if object_id not in world.objects:

            raise ValueError(
                f"Unknown object: {object_id}"
            )

        return world.objects[
            object_id
        ]


    def _position(
        self,
        world: WorldState,
        object_id: str,
    ):

        obj = self._object(
            world,
            object_id,
        )

        return np.asarray(
            obj.position,
            dtype=float,
        )


    # =====================================================
    # SPATIAL PREDICATES
    # =====================================================

    def left_of(
        self,
        world: WorldState,
        subject: str,
        reference: str,
    ) -> bool:

        subject_position = (
            self._position(
                world,
                subject,
            )
        )

        reference_position = (
            self._position(
                world,
                reference,
            )
        )

        return bool(
            subject_position[0]
            <
            (
                reference_position[0]
                - self.left_right_tolerance
            )
        )


    def right_of(
        self,
        world: WorldState,
        subject: str,
        reference: str,
    ) -> bool:

        subject_position = (
            self._position(
                world,
                subject,
            )
        )

        reference_position = (
            self._position(
                world,
                reference,
            )
        )

        return bool(
            subject_position[0]
            >
            (
                reference_position[0]
                + self.left_right_tolerance
            )
        )


    def near(
        self,
        world: WorldState,
        subject: str,
        reference: str,
    ) -> bool:

        subject_position = (
            self._position(
                world,
                subject,
            )
        )

        reference_position = (
            self._position(
                world,
                reference,
            )
        )

        distance = np.linalg.norm(
            subject_position
            - reference_position
        )

        return bool(
            distance
            <= self.near_threshold
        )


    # =====================================================
    # GRASP PREDICATE
    # =====================================================

    def grasped_by(
        self,
        world: WorldState,
        object_id: str,
        robot_id: str,
    ) -> bool:

        obj = self._object(
            world,
            object_id,
        )

        return bool(
            obj.grasped_by
            == robot_id
        )


    # =====================================================
    # GENERIC EVALUATOR
    # =====================================================

    def evaluate(
        self,
        world: WorldState,
        predicate: str,
        subject: str,
        reference: str,
    ) -> bool:

        if predicate == "left_of":

            return self.left_of(
                world,
                subject,
                reference,
            )

        if predicate == "right_of":

            return self.right_of(
                world,
                subject,
                reference,
            )

        if predicate == "near":

            return self.near(
                world,
                subject,
                reference,
            )

        if predicate == "grasped_by":

            return self.grasped_by(
                world,
                subject,
                reference,
            )

        raise ValueError(
            f"Unsupported predicate: "
            f"{predicate}"
        )