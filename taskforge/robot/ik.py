import math

import numpy as np


UPPER_ARM_LENGTH = 0.30
FOREARM_LENGTH = 0.25


def solve_planar_ik(
    target,
    shoulder_position,
    elbow_sign=1,
):

    target = np.asarray(
        target,
        dtype=float,
    )

    shoulder_position = np.asarray(
        shoulder_position,
        dtype=float,
    )

    dx = (
        target[0]
        - shoulder_position[0]
    )

    dz = (
        target[2]
        - shoulder_position[2]
    )

    l1 = UPPER_ARM_LENGTH
    l2 = FOREARM_LENGTH

    distance = math.sqrt(
        dx**2 + dz**2
    )

    if distance > l1 + l2:

        raise ValueError(
            f"Target unreachable: {target}"
        )

    if distance < abs(l1 - l2):

        raise ValueError(
            f"Target too close: {target}"
        )

    cos_elbow = (
        dx**2
        + dz**2
        - l1**2
        - l2**2
    ) / (
        2 * l1 * l2
    )

    cos_elbow = np.clip(
        cos_elbow,
        -1.0,
        1.0,
    )

    elbow = (
        elbow_sign
        * math.acos(cos_elbow)
    )

    shoulder = (
        math.atan2(dx, dz)
        - math.atan2(
            l2 * math.sin(elbow),
            l1
            + l2 * math.cos(elbow),
        )
    )

    return shoulder, elbow