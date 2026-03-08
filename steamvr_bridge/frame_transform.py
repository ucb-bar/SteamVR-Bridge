"""
Functions for transforming between the SteamVR/OpenXR frame and the robotics frame.
"""

import xr

# Quaternion (w, x, y, z) for the rotation from the SteamVR/OpenXR frame
# (X-right, Y-up, -Z-forward) to the robotics frame (X-forward, Y-left, Z-up).
_VR_TO_ROBOTICS_QUAT = (0.5, 0.5, -0.5, -0.5)
_VR_TO_ROBOTICS_QUAT_INV = (0.5, -0.5, 0.5, 0.5)


def _quat_multiply(q1, q2):
    """Hamilton product of two quaternions in (w, x, y, z) format."""
    w1, x1, y1, z1 = q1
    w2, x2, y2, z2 = q2
    return (
        w1*w2 - x1*x2 - y1*y2 - z1*z2,
        w1*x2 + x1*w2 + y1*z2 - z1*y2,
        w1*y2 - x1*z2 + y1*w2 + z1*x2,
        w1*z2 + x1*y2 - y1*x2 + z1*w2,
    )


def _vr_to_robotics_position(pos):
    """Convert position from SteamVR (X-right, Y-up, -Z-forward) to robotics (X-fwd, Y-left, Z-up)."""
    p = xr.Vector3f()
    p.x = -pos.z
    p.y = -pos.x
    p.z = pos.y
    return p


def _vr_to_robotics_orientation(quat):
    """
    Convert pose orientation from SteamVR world frame to robotics world frame.

    OpenXR pose orientation maps vectors from local device frame into the tracking world frame.
    To express that same pose in robotics coordinates, both world and local basis vectors are
    represented in the robotics frame:
        q_robot = q_R * q_vr * q_R^-1
    where q_R maps SteamVR/OpenXR axes into robotics axes.
    """
    q_vr = (quat.w, quat.x, quat.y, quat.z)
    w, x, y, z = _quat_multiply(
        _VR_TO_ROBOTICS_QUAT,
        _quat_multiply(q_vr, _VR_TO_ROBOTICS_QUAT_INV),
    )
    q = xr.Quaternionf()
    q.w = w
    q.x = x
    q.y = y
    q.z = z
    return q
