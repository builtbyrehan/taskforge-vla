import time

import mujoco


class MujocoBackend:

    def __init__(self, model_path):

        self.model = (
            mujoco.MjModel.from_xml_path(
                model_path
            )
        )

        self.data = mujoco.MjData(
            self.model
        )

        # Tracks assisted grasps:
        #
        # {
        #   "red_block": {
        #       "site_id": ...,
        #       "qpos_address": ...,
        #       "dof_address": ...,
        #       "offset": ...
        #   }
        # }
        self.attachments = {}

        mujoco.mj_forward(
            self.model,
            self.data,
        )


    # =====================================================
    # LOOKUPS
    # =====================================================

    def actuator_id(self, name):

        idx = mujoco.mj_name2id(
            self.model,
            mujoco.mjtObj.mjOBJ_ACTUATOR,
            name,
        )

        if idx == -1:
            raise RuntimeError(
                f"Actuator not found: {name}"
            )

        return idx


    def joint_id(self, name):

        idx = mujoco.mj_name2id(
            self.model,
            mujoco.mjtObj.mjOBJ_JOINT,
            name,
        )

        if idx == -1:
            raise RuntimeError(
                f"Joint not found: {name}"
            )

        return idx


    def body_id(self, name):

        idx = mujoco.mj_name2id(
            self.model,
            mujoco.mjtObj.mjOBJ_BODY,
            name,
        )

        if idx == -1:
            raise RuntimeError(
                f"Body not found: {name}"
            )

        return idx


    def site_id(self, name):

        idx = mujoco.mj_name2id(
            self.model,
            mujoco.mjtObj.mjOBJ_SITE,
            name,
        )

        if idx == -1:
            raise RuntimeError(
                f"Site not found: {name}"
            )

        return idx


    # =====================================================
    # STATE
    # =====================================================

    def body_position(self, name):

        body_id = self.body_id(
            name
        )

        return (
            self.data.xpos[
                body_id
            ].copy()
        )


    def body_orientation(self, name):

        body_id = self.body_id(
            name
        )

        return (
            self.data.xquat[
                body_id
            ].copy()
        )


    def site_position(self, name):

        site_id = self.site_id(
            name
        )

        return (
            self.data.site_xpos[
                site_id
            ].copy()
        )


    def joint_position(self, name):

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
    # ASSISTED GRASP BACKEND
    # =====================================================

    def attach_object(
        self,
        object_name,
        site_name,
    ):

        body_id = self.body_id(
            object_name
        )

        site_id = self.site_id(
            site_name
        )

        joint_id = (
            self.model.body_jntadr[
                body_id
            ]
        )

        if joint_id < 0:

            raise RuntimeError(
                f"Object '{object_name}' "
                f"does not have a movable joint."
            )


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


        # Preserve object position relative
        # to the end effector when attached.

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


    def detach_object(
        self,
        object_name,
    ):

        self.attachments.pop(
            object_name,
            None,
        )


    def _update_attachments(self):

        if not self.attachments:
            return


        for attachment in (
            self.attachments.values()
        ):

            site_position = (
                self.data.site_xpos[
                    attachment[
                        "site_id"
                    ]
                ].copy()
            )


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


            # Free joint layout:
            #
            # qpos:
            # [x, y, z, qw, qx, qy, qz]
            #
            # qvel:
            # [vx, vy, vz, wx, wy, wz]

            self.data.qpos[
                qpos_address:
                qpos_address + 3
            ] = desired_position


            # Freeze object translational and
            # rotational velocity while attached.

            self.data.qvel[
                dof_address:
                dof_address + 6
            ] = 0.0


        # Recalculate MuJoCo world transforms
        # after manually changing qpos.

        mujoco.mj_forward(
            self.model,
            self.data,
        )


    # =====================================================
    # PHYSICS
    # =====================================================

    def step(
        self,
        viewer=None,
        realtime=True,
    ):

        start = time.time()


        # Advance physics

        mujoco.mj_step(
            self.model,
            self.data,
        )


        # Apply assisted grasp constraints

        self._update_attachments()


        # Update viewer

        if viewer is not None:

            viewer.sync()


        # Keep simulation near real time

        if realtime:

            remaining = (
                self.model.opt.timestep
                - (
                    time.time()
                    - start
                )
            )

            if remaining > 0:

                time.sleep(
                    remaining
                )


    def run_for(
        self,
        seconds,
        viewer=None,
        realtime=True,
    ):

        start = time.time()

        while (
            time.time()
            - start
            < seconds
        ):

            if (
                viewer is not None
                and not viewer.is_running()
            ):
                break

            self.step(
                viewer=viewer,
                realtime=realtime,
            )