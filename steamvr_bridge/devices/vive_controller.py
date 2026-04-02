from enum import Enum

import openvr
from mathutils import Matrix, Vector

from .vive_device import DeviceIdentity, ViveDevice


def _button_mask(button_id: int) -> int:
    return 1 << button_id


class ViveControllerRole(Enum):
    """SteamVR controller role hints exposed by OpenVR."""

    INVALID = "invalid"
    LEFT = "left"
    RIGHT = "right"
    OPT_OUT = "opt_out"
    TREADMILL = "treadmill"
    STYLUS = "stylus"


class ViveController(ViveDevice):
    """
    SteamVR hand-controller wrapper with VIVE-style button and axis accessors.

    The controller role is resolved from SteamVR metadata, typically producing
    roles such as `left` and `right`.

    Args:
        vr_system: The OpenVR system handle.
        identity: User-facing device metadata.
    """
    visualization_asset_filename = "ObjModelViveController.obj"

    def __init__(self, vr_system: openvr.IVRSystem, identity: DeviceIdentity):
        super().__init__(vr_system=vr_system, identity=identity)
        self._trackpad_axis_index = self._find_axis_index(openvr.k_eControllerAxis_TrackPad, fallback=0)
        self._trigger_axis_index = self._find_axis_index(openvr.k_eControllerAxis_Trigger, fallback=1)
        self._menu_button = False
        self._trackpad_x = 0.0
        self._trackpad_y = 0.0
        self._trackpad_button = False
        self._trigger = 0.0
        self._grip_button = False

    def _find_axis_index(self, axis_type: int, fallback: int) -> int:
        """Best-effort lookup for the OpenVR axis slot used by a control input."""
        if self.vr_system is None:
            return fallback

        for axis_index in range(5):
            prop_name = f"Prop_Axis{axis_index}Type_Int32"
            prop = getattr(openvr, prop_name, None)
            if prop is None:
                continue

            try:
                if self.vr_system.getInt32TrackedDeviceProperty(self.device_index, prop) == axis_type:
                    return axis_index
            except openvr.OpenVRError:
                continue

        return fallback

    def update(
        self,
        pose: openvr.TrackedDevicePose_t,
        controller_state: openvr.VRControllerState_t | None = None,
    ):
        """Update pose state and the latest controller input snapshot."""
        super().update(pose)

        if controller_state is None:
            self._menu_button = False
            self._trackpad_x = 0.0
            self._trackpad_y = 0.0
            self._trackpad_button = False
            self._trigger = 0.0
            self._grip_button = False
            return

        self._menu_button = bool(
            controller_state.ulButtonPressed & _button_mask(openvr.k_EButton_ApplicationMenu)
        )
        self._trackpad_button = bool(
            controller_state.ulButtonPressed & _button_mask(openvr.k_EButton_SteamVR_Touchpad)
        )
        self._grip_button = bool(controller_state.ulButtonPressed & _button_mask(openvr.k_EButton_Grip))

        trackpad_axis = controller_state.rAxis[self._trackpad_axis_index]
        trigger_axis = controller_state.rAxis[self._trigger_axis_index]

        self._trackpad_x = float(trackpad_axis.x)
        self._trackpad_y = float(trackpad_axis.y)
        self._trigger = float(trigger_axis.x)

    @property
    def menu_button(self) -> bool:
        """Whether the application/menu button is currently pressed."""
        return self._menu_button

    @property
    def trackpad_x(self) -> float:
        """Current horizontal trackpad axis value in the range reported by SteamVR."""
        return self._trackpad_x

    @property
    def trackpad_y(self) -> float:
        """Current vertical trackpad axis value in the range reported by SteamVR."""
        return self._trackpad_y

    @property
    def trackpad_button(self) -> bool:
        """Whether the trackpad click is currently pressed."""
        return self._trackpad_button

    @property
    def trigger(self) -> float:
        """Current analog trigger value."""
        return self._trigger

    @property
    def grip_button(self) -> bool:
        """Whether the grip button is currently pressed."""
        return self._grip_button
