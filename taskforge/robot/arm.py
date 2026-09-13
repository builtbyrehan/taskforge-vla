import time

import numpy as np

from taskforge.robot.ik import (
    solve_planar_ik,
)


class ArmController:

    def __init__(
        self,
        backend,
        name,
        shoulder_position,
        elbow_sign,
    ):

        self.backend = backend

        self.name = name

        self.shoulder_position = (
            np.asarray(
                shoulder_position,
                dtype=float,
            )
        )

        self.elbow_sign = (
            elbow_sign
        )

        self.shoulder_motor = (
            backend.actuator_id(
                f"{name}_shoulder_motor"
            )
        )

        self.elbow_motor = (
            backend.actuator_id(
                f"{name}_elbow_motor"
            )
        )

        self.finger_a_motor = (
            backend.actuator_id(
                f"{name}_finger_a_motor"
            )
        )

        self.finger_b_motor = (
            backend.actuator_id(
                f"{name}_finger_b_motor"
            )
        )

        self.shoulder_joint = (
            f"{name}_shoulder"
        )

        self.elbow_joint = (
            f"{name}_elbow"
        )

        self.ee_site = (
            f"{name}_ee"
        )


    # =====================================================
    # GRIPPER
    # =====================================================

    def open_gripper(self):

        self.backend.data.ctrl[
            self.finger_a_motor
        ] = -0.015

        self.backend.data.ctrl[
            self.finger_b_motor
        ] = 0.015


    def close_gripper(self):

        self.backend.data.ctrl[
            self.finger_a_motor
        ] = -0.025

        self.backend.data.ctrl[
            self.finger_b_motor
        ] = 0.025


    # =====================================================
    # CARTESIAN MOTION
    # =====================================================

    def move_to(
        self,
        target,
        viewer,
        tolerance=0.025,
        timeout=6.0,
    ):

        target = np.asarray(
            target,
            dtype=float,
        )

        shoulder, elbow = (
            solve_planar_ik(
                target,
                self.shoulder_position,
                self.elbow_sign,
            )
        )

        self.backend.data.ctrl[
            self.shoulder_motor
        ] = shoulder

        self.backend.data.ctrl[
            self.elbow_motor
        ] = elbow

        start = time.time()

        while (
            time.time() - start
            < timeout
        ):

            if not viewer.is_running():
                return False

            self.backend.step(
                viewer
            )

            current = (
                self.backend.site_position(
                    self.ee_site
                )
            )

            error = np.linalg.norm(
                target - current
            )

            if error < tolerance:

                print(
                    f"{self.name}: "
                    f"target reached "
                    f"({error * 100:.2f} cm)"
                )

                return True

        print(
            f"{self.name}: "
            f"MOVE TIMEOUT"
        )

        return False


    # =====================================================
    # JOINT MOTION
    # =====================================================

    def move_home(
        self,
        viewer,
        timeout=6.0,
    ):

        self.backend.data.ctrl[
            self.shoulder_motor
        ] = 0.0

        self.backend.data.ctrl[
            self.elbow_motor
        ] = 0.0

        start = time.time()

        while (
            time.time() - start
            < timeout
        ):

            self.backend.step(
                viewer
            )

            shoulder = (
                self.backend.joint_position(
                    self.shoulder_joint
                )
            )

            elbow = (
                self.backend.joint_position(
                    self.elbow_joint
                )
            )

            error = (
                abs(shoulder)
                + abs(elbow)
            )

            if error < 0.04:

                print(
                    f"{self.name}: HOME"
                )

                return True

        return False


    # =====================================================
    # PICK PRIMITIVE
    # =====================================================

    def pick(
        self,
        object_name,
        viewer,
    ):

        print()
        print("=" * 55)

        print(
            f"{self.name.upper()} ARM"
            f" -> PICK({object_name})"
        )

        print("=" * 55)

        object_start = (
            self.backend.body_position(
                object_name
            )
        )

        x = object_start[0]
        y = object_start[1]
        z = object_start[2]

        pregrasp = np.array([
            x,
            y,
            z + 0.22,
        ])

        grasp = np.array([
            x,
            y,
            z + 0.12,
        ])

        lift = np.array([
            x,
            y,
            z + 0.24,
        ])


        # -----------------------------------------
        # OPEN
        # -----------------------------------------

        print(
            f"{self.name}: OPEN"
        )

        self.open_gripper()

        self.backend.run_for(
            0.5,
            viewer,
        )


        # -----------------------------------------
        # APPROACH
        # -----------------------------------------

        print(
            f"{self.name}: APPROACH"
        )

        if not self.move_to(
            pregrasp,
            viewer,
        ):
            return False


        # -----------------------------------------
        # DESCEND
        # -----------------------------------------

        print(
            f"{self.name}: DESCEND"
        )

        if not self.move_to(
            grasp,
            viewer,
        ):
            return False


        # -----------------------------------------
        # CLOSE
        # -----------------------------------------

        print(
            f"{self.name}: CLOSE"
        )

        self.close_gripper()

        self.backend.run_for(
            1.0,
            viewer,
        )


        # -----------------------------------------
        # VERIFY GRASP
        # -----------------------------------------

        ee_position = (
            self.backend.site_position(
                self.ee_site
            )
        )

        object_position = (
            self.backend.body_position(
                object_name
            )
        )

        distance = np.linalg.norm(
            ee_position
            - object_position
        )

        print(
            f"{self.name}: "
            f"EE/object distance "
            f"{distance:.3f} m"
        )

        if distance > 0.13:

            print(
                f"{self.name}: "
                f"PICK_FAILED"
            )

            return False


        # -----------------------------------------
        # ATTACH
        # -----------------------------------------

        self.backend.attach_object(
            object_name,
            self.ee_site,
        )

        print(
            f"{self.name}: "
            f"GRASP VERIFIED"
        )


        # -----------------------------------------
        # LIFT
        # -----------------------------------------

        print(
            f"{self.name}: LIFT"
        )

        if not self.move_to(
            lift,
            viewer,
        ):

            return False


        # -----------------------------------------
        # FINAL VERIFICATION
        # -----------------------------------------

        final_position = (
            self.backend.body_position(
                object_name
            )
        )

        lift_distance = (
            final_position[2]
            - object_start[2]
        )

        if lift_distance > 0.10:

            print(
                f"{self.name}: "
                f"PICK_SUCCESS"
            )

            print(
                f"Lifted "
                f"{lift_distance:.3f} m"
            )

            return True


        print(
            f"{self.name}: "
            f"PICK_FAILED "
            f"(lift verification)"
        )

        return False