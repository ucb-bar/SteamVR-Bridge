from __future__ import annotations

from dataclasses import dataclass

import openvr
from mathutils import Matrix, Quaternion, Vector


@dataclass
class Pose:
    """Rigid transform represented as a 3D location and quaternion orientation."""

    location: Vector
    orientation: Quaternion

    @classmethod
    def from_matrix(cls, matrix: Matrix) -> "Pose":
        return cls(location=matrix.to_translation(), orientation=matrix.to_quaternion())

    def to_matrix(self) -> Matrix:
        return Matrix.LocRotScale(self.location, self.orientation, Vector((1.0, 1.0, 1.0)))


STEAMVR_TO_STANDARD_TRANSFORM_MATRIX = Matrix(
    (
        (0.0, 0.0, -1.0, 0.0),
        (-1.0, 0.0, 0.0, 0.0),
        (0.0, 1.0, 0.0, 0.0),
        (0.0, 0.0, 0.0, 1.0),
    )
)
STANDARD_TO_STEAMVR_TRANSFORM_MATRIX = STEAMVR_TO_STANDARD_TRANSFORM_MATRIX.inverted()


def steamvr_matrix34_to_matrix(matrix34: openvr.HmdMatrix34_t) -> Matrix:
    """Convert an OpenVR 3x4 transform matrix into a homogeneous 4x4 matrix."""
    rows = [tuple(float(matrix34.m[i][j]) for j in range(4)) for i in range(3)]
    return Matrix(
        (
            rows[0],
            rows[1],
            rows[2],
            (0.0, 0.0, 0.0, 1.0),
        )
    )


def steamvr_vector_to_standard_frame(vector: openvr.HmdVector3_t | tuple[float, float, float]) -> Vector:
    """Convert a SteamVR vector into the library's standard frame."""
    x = float(vector[0])
    y = float(vector[1])
    z = float(vector[2])
    transformed = STEAMVR_TO_STANDARD_TRANSFORM_MATRIX.to_3x3() @ Vector((x, y, z))
    return Vector(transformed)


def apply_local_transform(pose: Pose, local_transform: Matrix) -> Pose:
    """Apply a device-local transform to a pose."""
    transformed_matrix = pose.to_matrix() @ local_transform
    return Pose.from_matrix(transformed_matrix)


def steamvr_to_standard_frame_transform(pose: Pose) -> Pose:
    """
    Convert a SteamVR pose into the library's standard robotics frame.

    SteamVR reports poses in a right-handed frame with `+X` right, `+Y` up, and
    `-Z` forward. SteamVR Bridge converts these poses into `+X` forward,
    `+Y` left, `+Z` up.

    Args:
        pose: The SteamVR pose.

    Returns:
        The standard frame transform.
    """
    steamvr_matrix = pose.to_matrix()
    standard_matrix = (
        STEAMVR_TO_STANDARD_TRANSFORM_MATRIX
        @ steamvr_matrix
        @ STANDARD_TO_STEAMVR_TRANSFORM_MATRIX
    )
    return Pose.from_matrix(standard_matrix)
