from enum import Enum

import openvr
from mathutils import Matrix, Vector

from .vive_device import DeviceIdentity, ViveDevice


def _button_mask(button_id: int) -> int:
    return 1 << button_id


class ViveControllerRole(Enum):
    INVALID = "invalid"
    LEFT = "left"
    RIGHT = "right"
    OPT_OUT = "opt_out"
    TREADMILL = "treadmill"
    STYLUS = "stylus"


class ViveController(ViveDevice):
    """
    A class representing the VIVE Controller (2018).

    For more information, please refer to the VIVE Controller (2018) product documentation:
    https://www.vive.com/us/support/vive-pro2/category_howto/about-the-controllers---2018.html

    Args:
        vr_system: The OpenVR system handle.
        identity: User-facing device metadata.
    """
    device_to_local_transform = Matrix.Identity(4)  #Matrix.Translation(Vector((0.0, -0.025, -0.025)))
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
        """
        Get the state of the menu button.

        Returns:
            The state of the menu button as a boolean.
        """
        return self._menu_button

    @property
    def trackpad_x(self) -> float:
        """
        Get the state of the trackpad x axis.

        Returns:
            The state of the trackpad x axis as a float.
        """
        return self._trackpad_x

    @property
    def trackpad_y(self) -> float:
        """
        Get the state of the trackpad y axis.

        Returns:
            The state of the trackpad y axis as a float.
        """
        return self._trackpad_y

    @property
    def trackpad_button(self) -> bool:
        """
        Get the state of the trackpad button.

        Returns:
            The state of the trackpad button as a boolean.
        """
        return self._trackpad_button

    @property
    def trigger(self) -> float:
        """
        Get the state of the trigger.

        Returns:
            The state of the trigger as a float.
        """
        return self._trigger

    @property
    def grip_button(self) -> bool:
        """
        Get the state of the grip button.

        Returns:
            The state of the grip button as a boolean.
        """
        return self._grip_button
