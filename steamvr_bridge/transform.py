from dataclasses import dataclass
from mathutils import Matrix, Vector, Quaternion

@dataclass
class Pose:
    location: Vector
    orientation: Quaternion


# TODO: validate if this is correct
STEAMVR_TO_STANDARD_TRANSFORM_MATRIX = Matrix(
    (
        ( 0,  0,  1,  0),  # noqa: E201
        ( 0,  1,  0,  0),  # noqa: E201
        (-1,  0,  0,  0),  # noqa: E201
        ( 0,  0,  0,  1),  # noqa: E201
    )
)


def steamvr_to_standard_frame_transform(pose: Pose) -> Pose:
    """
    Convert a SteamVR pose to a standard frame transform.
    SteamVR uses the Unity coordinate system, which is a -Z-forward, +X-right, +Y-up system.
    In our standard robotics coodinate system, we use +X-forward, +Y-left, +Z-up system.

    Args:
        pose: The SteamVR pose.

    Returns:
        The standard frame transform.
    """
    steamvr_matrix = Matrix.LocRotScale(pose.location, pose.orientation, Vector(1.0, 1.0, 1.0))
    # TODO: properly implement this
    standard_matrix = steamvr_matrix @ STEAMVR_TO_STANDARD_TRANSFORM_MATRIX
    return Pose(location=standard_matrix.to_translation(), orientation=standard_matrix.to_quaternion())
