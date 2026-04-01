from enum import Enum
import math

import openvr
from mathutils import Matrix

from .vive_device import DeviceIdentity, ViveDevice


class ViveTrackerRole(Enum):
    """Known SteamVR body-role assignments for generic trackers."""

    HELD_IN_HAND = "vive_tracker_held_in_hand"
    LEFT_FOOT = "vive_tracker_left_foot"
    RIGHT_FOOT = "vive_tracker_right_foot"
    LEFT_SHOULDER = "vive_tracker_left_shoulder"
    RIGHT_SHOULDER = "vive_tracker_right_shoulder"
    LEFT_ELBOW = "vive_tracker_left_elbow"
    RIGHT_ELBOW = "vive_tracker_right_elbow"
    LEFT_KNEE = "vive_tracker_left_knee"
    RIGHT_KNEE = "vive_tracker_right_knee"
    LEFT_WRIST = "vive_tracker_left_wrist"
    RIGHT_WRIST = "vive_tracker_right_wrist"
    LEFT_ANKLE = "vive_tracker_left_ankle"
    RIGHT_ANKLE = "vive_tracker_right_ankle"
    WAIST = "vive_tracker_waist"
    CHEST = "vive_tracker_chest"
    CAMERA = "vive_tracker_camera"
    KEYBOARD = "vive_tracker_keyboard"


class ViveTracker(ViveDevice):
    """
    Generic SteamVR tracker wrapper.

    Tracker roles are inferred from SteamVR controller metadata and tracker
    assignments stored in `steamvr.vrsettings`.

    Args:
        vr_system: The OpenVR system handle.
        identity: User-facing device metadata.
    """
    device_to_local_transform = (
        Matrix.Rotation(math.pi / 2.0, 4, "X") @ Matrix.Rotation(math.pi, 4, "Z")
    )
    visualization_asset_filename = "ObjModelViveTracker3.obj"

    def __init__(self, vr_system: openvr.IVRSystem, identity: DeviceIdentity):
        super().__init__(vr_system=vr_system, identity=identity)

    @staticmethod
    def tracker_role_name(tracker_role: ViveTrackerRole) -> str:
        """Convert a SteamVR tracker enum into the public short role string."""
        return tracker_role.value.removeprefix("vive_tracker_")

    @staticmethod
    def tracker_role_from_controller_type(controller_type: str) -> ViveTrackerRole | None:
        """Resolve a tracker role directly from the OpenVR controller-type string."""
        try:
            return ViveTrackerRole(controller_type)
        except ValueError:
            return None

    @staticmethod
    def tracker_role_from_steamvr_role(steamvr_role: str) -> ViveTrackerRole | None:
        """Resolve a tracker role from the role labels stored in SteamVR settings."""
        for role in ViveTrackerRole:
            suffix = "".join(part.title() for part in role.name.split("_"))
            if steamvr_role == f"TrackerRole_{suffix}":
                return role
        return None
