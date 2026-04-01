from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import openvr
from mathutils import Matrix, Quaternion, Vector

from ..transform import (
    Pose,
    apply_local_transform,
    steamvr_matrix34_to_matrix,
    steamvr_to_standard_frame_transform,
    steamvr_vector_to_standard_frame,
)


@dataclass
class DeviceIdentity:
    index: int
    """The device index in the OpenVR system."""
    kind: str
    """The type of device, whether it's a head-mounted display (HMD), controller, tracker, base station, etc."""
    name: str
    """The device serial number."""
    role: str
    """The device role assigned in SteamVR."""
    model_number: str
    """The device model number."""


class ViveDevice:
    """
    Shared SteamVR tracked-device functionality.

    Args:
        vr_system: Initialized OpenVR system handle.
        identity: User-facing device identity and SteamVR metadata.
    """

    device_to_local_transform = Matrix.Identity(4)
    visualization_asset_filename: str | None = None

    def __init__(self, vr_system: openvr.IVRSystem, identity: DeviceIdentity):
        self.vr_system = vr_system
        self.refresh_identity(identity)

        self._location = Vector((0.0, 0.0, 0.0))
        self._orientation = Quaternion((1.0, 0.0, 0.0, 0.0))
        self._velocity = Vector((0.0, 0.0, 0.0))
        self._angular_velocity = Vector((0.0, 0.0, 0.0))
        self._is_connected = False
        self._is_pose_valid = False

    @property
    def device_index(self) -> int:
        return self.identity.index

    @classmethod
    def visualization_asset_path(cls) -> Path | None:
        if cls.visualization_asset_filename is None:
            return None
        return Path(__file__).resolve().parents[2] / "assets" / cls.visualization_asset_filename

    def refresh_identity(self, identity: DeviceIdentity):
        self.identity = identity
        self.name = identity.name
        self.role = identity.role
        self.kind = identity.kind
        self.model_number = identity.model_number

    @property
    def is_connected(self) -> bool:
        return self._is_connected

    @property
    def is_pose_valid(self) -> bool:
        return self._is_pose_valid

    @property
    def location(self) -> Vector:
        return self._location

    @property
    def orientation(self) -> Quaternion:
        return self._orientation

    @property
    def velocity(self) -> Vector:
        return self._velocity

    @property
    def angular_velocity(self) -> Vector:
        return self._angular_velocity

    def update(self, pose: openvr.TrackedDevicePose_t):
        """
        Update the device state from the latest OpenVR pose.
        """
        self._is_connected = bool(pose.bDeviceIsConnected)
        self._is_pose_valid = bool(pose.bPoseIsValid)

        if not self._is_connected or not self._is_pose_valid:
            return

        steamvr_pose = Pose.from_matrix(steamvr_matrix34_to_matrix(pose.mDeviceToAbsoluteTracking))
        adjusted_pose = apply_local_transform(steamvr_pose, self.device_to_local_transform)
        standard_pose = steamvr_to_standard_frame_transform(adjusted_pose)

        self._location = standard_pose.location.copy()
        self._orientation = standard_pose.orientation.copy()
        self._velocity = steamvr_vector_to_standard_frame(pose.vVelocity)
        self._angular_velocity = steamvr_vector_to_standard_frame(pose.vAngularVelocity)
