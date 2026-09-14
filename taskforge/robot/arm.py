import time
import numpy as np

from taskforge.robot.ik import solve_planar_ik


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
        self.shoulder_position = np.asarray(
            shoulder_position,
            dtype=float,
        )
        self.elbow_sign = elbow_sign

        self.shoulder_motor = backend.actuator_id(
            f"{name}_shoulder_motor"
        )
        self.elbow_motor = backend.actuator_id(
            f"{name}_elbow_motor"
        )
        self.finger_a_motor = backend.actuator_id(
            f"{name}_finger_a_motor"
        )
        self.finger_b_motor = backend.actuator_id(
            f"{name}_finger_b_motor"
        )

        self.shoulder_joint = f"{name}_shoulder"
        self.elbow_joint = f"{name}_elbow"
        self.ee_site = f"{name}_ee"

    # =====================================================
    # VIEWER SAFETY
    # =====================================================

    @staticmethod
    def _viewer_is_available(viewer):
        """
        Return True when execution may continue.

        In terminal demos, viewer is a MuJoCo viewer instance.
        In Streamlit/headless mode, viewer is None.

        Headless execution is valid, so None means "continue".
        """

        if viewer is None:
            return True

        return viewer.is_running()

    # =====================================================
    # GRIPPER
    # =====================================================

    def open_gripper(self):
        self.backend.data.ctrl[self.finger_a_motor] = -0.015
        self.backend.data.ctrl[self.finger_b_motor] = 0.015

    def close_gripper(self):
        self.backend.data.ctrl[self.finger_a_motor] = -0.025
        self.backend.data.ctrl[self.finger_b_motor] = 0.025

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

        shoulder, elbow = solve_planar_ik(
            target,
            self.shoulder_position,
            self.elbow_sign,
        )

        self.backend.data.ctrl[self.shoulder_motor] = shoulder
        self.backend.data.ctrl[self.elbow_motor] = elbow

        start = time.time()

        while time.time() - start < timeout:

            if not self._viewer_is_available(viewer):
                print(f"{self.name}: VIEWER CLOSED")
                return False

            self.backend.step(viewer)

            current = self.backend.site_position(
                self.ee_site
            )

            error = np.linalg.norm(
                target - current
            )

            if error < tolerance:
                print(
                    f"{self.name}: target reached "
                    f"({error * 100:.2f} cm)"
                )
                return True

        print(f"{self.name}: MOVE TIMEOUT")
        return False

    # =====================================================
    # JOINT MOTION
    # =====================================================

    def move_home(
        self,
        viewer,
        timeout=6.0,
    ):
        self.backend.data.ctrl[self.shoulder_motor] = 0.0
        self.backend.data.ctrl[self.elbow_motor] = 0.0

        start = time.time()

        while time.time() - start < timeout:

            if not self._viewer_is_available(viewer):
                print(f"{self.name}: VIEWER CLOSED")
                return False

            self.backend.step(viewer)

            shoulder = self.backend.joint_position(
                self.shoulder_joint
            )

            elbow = self.backend.joint_position(
                self.elbow_joint
            )

            error = abs(shoulder) + abs(elbow)

            if error < 0.04:
                print(f"{self.name}: HOME")
                return True

        print(f"{self.name}: HOME TIMEOUT")
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
            f"{self.name.upper()} ARM -> "
            f"PICK({object_name})"
        )
        print("=" * 55)

        object_start = self.backend.body_position(
            object_name
        )

        x = object_start[0]
        y = object_start[1]
        z = object_start[2]

        pregrasp = np.array(
            [x, y, z + 0.22]
        )

        grasp = np.array(
            [x, y, z + 0.12]
        )

        lift = np.array(
            [x, y, z + 0.24]
        )

        # Open
        print(f"{self.name}: OPEN")

        self.open_gripper()

        self.backend.run_for(
            0.5,
            viewer,
        )

        # Approach
        print(f"{self.name}: APPROACH")

        if not self.move_to(
            pregrasp,
            viewer,
        ):
            return False

        # Descend
        print(f"{self.name}: DESCEND")

        if not self.move_to(
            grasp,
            viewer,
        ):
            return False

        # Close
        print(f"{self.name}: CLOSE")

        self.close_gripper()

        self.backend.run_for(
            1.0,
            viewer,
        )

        # Verify Grasp
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
                "PICK_FAILED"
            )
            return False

        # Attach
        self.backend.attach_object(
            object_name,
            self.ee_site,
        )

        print(
            f"{self.name}: "
            "GRASP VERIFIED"
        )

        # Lift
        print(f"{self.name}: LIFT")

        if not self.move_to(
            lift,
            viewer,
        ):
            return False

        # Final Verification
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
                "PICK_SUCCESS"
            )

            print(
                f"Lifted "
                f"{lift_distance:.3f} m"
            )

            return True

        print(
            f"{self.name}: "
            "PICK_FAILED "
            "(lift verification)"
        )

        return False

    # =====================================================
    # PLACE PRIMITIVE
    # =====================================================

    def place(
        self,
        object_name,
        target_position,
        viewer,
    ):
        print()
        print("=" * 55)
        print(
            f"{self.name.upper()} ARM -> "
            f"PLACE({object_name})"
        )
        print("=" * 55)

        # Verify object is actually held
        if not self.backend.is_attached(
            object_name
        ):
            print(
                f"{self.name}: "
                "PLACE FAILED"
            )

            print(
                f"{object_name} "
                "is not attached."
            )

            return False

        # Read current grasp offset
        offset = (
            self.backend.attachment_offset(
                object_name
            )
        )

        if offset is None:
            print(
                f"{self.name}: "
                "PLACE FAILED - "
                "missing attachment offset."
            )
            return False

        target_position = np.array(
            target_position,
            dtype=float,
        )

        # Compute end-effector target
        placement_ee = (
            target_position
            - offset
        )

        preplace_ee = (
            placement_ee.copy()
        )

        preplace_ee[2] += 0.15

        print(
            f"{self.name}: "
            "target object position "
            f"{np.round(target_position, 3)}"
        )

        print(
            f"{self.name}: "
            "PRE-PLACE"
        )

        # Move above placement location
        if not self.move_to(
            preplace_ee,
            viewer,
        ):
            print(
                f"{self.name}: "
                "PRE-PLACE MOVE FAILED"
            )
            return False

        # Descend
        print(
            f"{self.name}: "
            "DESCEND TO PLACE"
        )

        if not self.move_to(
            placement_ee,
            viewer,
        ):
            print(
                f"{self.name}: "
                "PLACE DESCENT FAILED"
            )
            return False

        # Release object
        print(
            f"{self.name}: "
            "RELEASE"
        )

        detached = (
            self.backend.detach_object(
                object_name
            )
        )

        if not detached:
            print(
                f"{self.name}: "
                "DETACH FAILED"
            )
            return False

        self.open_gripper()

        self.backend.run_for(
            0.5,
            viewer,
        )

        # Verify release
        if self.backend.is_attached(
            object_name
        ):
            print(
                f"{self.name}: "
                "RELEASE VERIFICATION FAILED"
            )
            return False

        # Verify final position
        actual_position = (
            self.backend.body_position(
                object_name
            )
        )

        error = float(
            np.linalg.norm(
                actual_position
                - target_position
            )
        )

        print(
            f"{self.name}: "
            f"placement error "
            f"{error * 100:.2f} cm"
        )

        placement_success = (
            error <= 0.05
        )

        # Retreat
        print(
            f"{self.name}: "
            "RETREAT"
        )

        retreat_success = (
            self.move_to(
                preplace_ee,
                viewer,
            )
        )

        if not retreat_success:
            print(
                f"{self.name}: "
                "RETREAT WARNING"
            )

        # Result
        if placement_success:
            print(
                f"{self.name}: "
                "PLACE_SUCCESS"
            )

            print(
                "Final position: "
                f"{np.round(actual_position, 3)}"
            )

            return True

        print(
            f"{self.name}: "
            "PLACE_FAILED"
        )

        print(
            "Expected: "
            f"{np.round(target_position, 3)}"
        )

        print(
            "Actual: "
            f"{np.round(actual_position, 3)}"
        )

        return False
