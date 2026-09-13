import time

import mujoco


class MujocoBackend:

    # =====================================================
    # INITIALIZATION
    # =====================================================

    def __init__(
        self,
        model_path,
    ):

        self.model = (
            mujoco.MjModel.from_xml_path(
                model_path
            )
        )

        self.data = mujoco.MjData(
            self.model
        )

        # -------------------------------------------------
        # Assisted grasp bookkeeping
        #
        # {
        #     "red_block": {
        #         "site_id": ...,
        #         "site_name": ...,
        #         "qpos_address": ...,
        #         "dof_address": ...,
        #         "offset": ...
        #     }
        # }
        # -------------------------------------------------

        self.attachments = {}

        mujoco.mj_forward(
            self.model,
            self.data,
        )


    # =====================================================
    # LOOKUPS
    # =====================================================

    def actuator_id(
        self,
        name,
    ):

        idx = mujoco.mj_name2id(
            self.model,
            mujoco.mjtObj.mjOBJ_ACTUATOR,
            name,
        )

        if idx == -1:

            raise RuntimeError(
                f"Actuator not found: "
                f"{name}"
            )

        return idx


    def joint_id(
        self,
        name,
    ):

        idx = mujoco.mj_name2id(
            self.model,
            mujoco.mjtObj.mjOBJ_JOINT,
            name,
        )

        if idx == -1:

            raise RuntimeError(
                f"Joint not found: "
                f"{name}"
            )

        return idx


    def body_id(
        self,
        name,
    ):

        idx = mujoco.mj_name2id(
            self.model,
            mujoco.mjtObj.mjOBJ_BODY,
            name,
        )

        if idx == -1:

            raise RuntimeError(
                f"Body not found: "
                f"{name}"
            )

        return idx


    def site_id(
        self,
        name,
    ):

        idx = mujoco.mj_name2id(
            self.model,
            mujoco.mjtObj.mjOBJ_SITE,
            name,
        )

        if idx == -1:

            raise RuntimeError(
                f"Site not found: "
                f"{name}"
            )

        return idx


    # =====================================================
    # STATE ACCESS
    # =====================================================

    def body_position(
        self,
        name,
    ):

        body_id = self.body_id(
            name
        )

        return (
            self.data.xpos[
                body_id
            ].copy()
        )


    def body_orientation(
        self,
        name,
    ):

        body_id = self.body_id(
            name
        )

        return (
            self.data.xquat[
                body_id
            ].copy()
        )


    def site_position(
        self,
        name_or_id,
    ):

        # Allows either:
        #
        # site_position("left_ee")
        #
        # or:
        #
        # site_position(site_id)

        if isinstance(
            name_or_id,
            str,
        ):

            site_id = self.site_id(
                name_or_id
            )

        else:

            site_id = int(
                name_or_id
            )

        return (
            self.data.site_xpos[
                site_id
            ].copy()
        )


    def joint_position(
        self,
        name,
    ):

        joint_id = self.joint_id(
            name
        )

        address = (
            self.model.jnt_qposadr[
                joint_id
            ]
        )

        return float(
            self.data.qpos[
                address
            ]
        )


    # =====================================================
    # ATTACHMENT STATE
    # =====================================================

    def is_attached(
        self,
        object_name,
    ):

        return (
            object_name
            in self.attachments
        )


    def attached_to(
        self,
        object_name,
    ):

        attachment = (
            self.attachments.get(
                object_name
            )
        )

        if attachment is None:

            return None


        attached_site_id = (
            attachment[
                "site_id"
            ]
        )


        left_site_id = (
            self.site_id(
                "left_ee"
            )
        )

        right_site_id = (
            self.site_id(
                "right_ee"
            )
        )


        if (
            attached_site_id
            == left_site_id
        ):

            return "left_arm"


        if (
            attached_site_id
            == right_site_id
        ):

            return "right_arm"


        return "unknown"


    # =====================================================
    # ATTACHMENT OFFSET
    # =====================================================

    def attachment_offset(
        self,
        object_name,
    ):

        attachment = (
            self.attachments.get(
                object_name
            )
        )

        if attachment is None:

            return None


        return (
            attachment[
                "offset"
            ].copy()
        )


    # =====================================================
    # ASSISTED GRASP
    # =====================================================

    def attach_object(
        self,
        object_name,
        site_name,
    ):

        # -------------------------------------------------
        # Find object body and EE site
        # -------------------------------------------------

        body_id = self.body_id(
            object_name
        )

        site_id = self.site_id(
            site_name
        )


        # -------------------------------------------------
        # Find object's joint
        # -------------------------------------------------

        joint_id = (
            self.model.body_jntadr[
                body_id
            ]
        )


        joint_count = (
            self.model.body_jntnum[
                body_id
            ]
        )


        if (
            joint_id < 0
            or joint_count == 0
        ):

            raise RuntimeError(
                f"Object '{object_name}' "
                f"does not have a "
                f"movable joint."
            )


        # -------------------------------------------------
        # Object should use a MuJoCo free joint
        # -------------------------------------------------

        joint_type = (
            self.model.jnt_type[
                joint_id
            ]
        )


        if (
            joint_type
            != mujoco.mjtJoint.mjJNT_FREE
        ):

            raise RuntimeError(
                f"Object '{object_name}' "
                f"must use a free joint "
                f"for assisted grasp."
            )


        # -------------------------------------------------
        # Joint addresses
        # -------------------------------------------------

        qpos_address = (
            self.model.jnt_qposadr[
                joint_id
            ]
        )

        dof_address = (
            self.model.jnt_dofadr[
                joint_id
            ]
        )


        # -------------------------------------------------
        # Current object and EE locations
        # -------------------------------------------------

        object_position = (
            self.body_position(
                object_name
            )
        )

        site_position = (
            self.site_position(
                site_name
            )
        )


        # -------------------------------------------------
        # Preserve current relative offset
        #
        # object_position =
        # EE_position + offset
        # -------------------------------------------------

        offset = (
            object_position
            - site_position
        )


        self.attachments[
            object_name
        ] = {

            "site_id":
                site_id,

            "site_name":
                site_name,

            "qpos_address":
                qpos_address,

            "dof_address":
                dof_address,

            "offset":
                offset,
        }


        # Immediately synchronize object.
        self._update_attachments()


        return True


    # =====================================================
    # DETACH OBJECT
    # =====================================================

    def detach_object(
        self,
        object_name,
    ):

        if (
            object_name
            not in self.attachments
        ):

            return False


        del self.attachments[
            object_name
        ]


        # Recompute MuJoCo transforms after release.
        mujoco.mj_forward(
            self.model,
            self.data,
        )


        return True


    # =====================================================
    # UPDATE ASSISTED GRASPS
    # =====================================================

    def _update_attachments(
        self,
    ):

        if not self.attachments:

            return


        for attachment in (
            self.attachments.values()
        ):

            # ---------------------------------------------
            # Read end-effector position
            # ---------------------------------------------

            site_position = (
                self.data.site_xpos[
                    attachment[
                        "site_id"
                    ]
                ].copy()
            )


            # ---------------------------------------------
            # Desired object position
            # ---------------------------------------------

            desired_position = (
                site_position
                + attachment[
                    "offset"
                ]
            )


            qpos_address = (
                attachment[
                    "qpos_address"
                ]
            )

            dof_address = (
                attachment[
                    "dof_address"
                ]
            )


            # ---------------------------------------------
            # Free joint qpos:
            #
            # x y z qw qx qy qz
            #
            # Update translation only.
            # ---------------------------------------------

            self.data.qpos[
                qpos_address:
                qpos_address + 3
            ] = desired_position


            # ---------------------------------------------
            # Free joint qvel:
            #
            # vx vy vz wx wy wz
            #
            # Zero velocity while assisted-grasped.
            # ---------------------------------------------

            self.data.qvel[
                dof_address:
                dof_address + 6
            ] = 0.0


        # Recalculate world transforms after
        # manually modifying qpos.
        mujoco.mj_forward(
            self.model,
            self.data,
        )


    # =====================================================
    # SINGLE PHYSICS STEP
    # =====================================================

    def step(
        self,
        viewer=None,
        realtime=True,
    ):

        start = time.time()


        # -------------------------------------------------
        # Advance MuJoCo physics
        # -------------------------------------------------

        mujoco.mj_step(
            self.model,
            self.data,
        )


        # -------------------------------------------------
        # Update assisted grasp objects
        # -------------------------------------------------

        self._update_attachments()


        # -------------------------------------------------
        # Update viewer
        # -------------------------------------------------

        if viewer is not None:

            if viewer.is_running():

                viewer.sync()


        # -------------------------------------------------
        # Approximate real-time playback
        # -------------------------------------------------

        if realtime:

            elapsed = (
                time.time()
                - start
            )

            remaining = (
                self.model.opt.timestep
                - elapsed
            )


            if remaining > 0:

                time.sleep(
                    remaining
                )


    # =====================================================
    # RUN SIMULATION FOR N SIMULATED SECONDS
    # =====================================================

    def run_for(
        self,
        seconds,
        viewer=None,
        realtime=True,
    ):

        timestep = (
            self.model.opt.timestep
        )


        number_of_steps = max(
            1,
            int(
                seconds
                / timestep
            ),
        )


        for _ in range(
            number_of_steps
        ):

            # Viewer may have been closed.
            if (
                viewer is not None
                and not viewer.is_running()
            ):

                break


            self.step(
                viewer=viewer,
                realtime=realtime,
            )