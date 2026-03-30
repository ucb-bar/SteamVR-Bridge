import openvr

from mathutils import Vector, Quaternion

from ..transform import steamvr_to_standard_frame_transform


class ViveController:
    """
    A class representing the VIVE Controller (2018).

    For more information, please refer to the VIVE Controller (2018) product documentation:
    https://www.vive.com/us/support/vive-pro2/category_howto/about-the-controllers---2018.html

    Args:
        instance: The OpenVR instance.
        name: The name of the controller.
        role: The role of the controller, either "left" or "right".
    """
    def __init__(
        self,
        instance: xr.Instance,
        name: str,
        role: str,
    ):
        self.instance = instance
        self.name = name
        self.role = role

        self._location = Vector()
        self._orientation = Quaternion()
        self._menu_button = False
        self._trackpad_x = 0.0
        self._trackpad_y = 0.0
        self._trackpad_button = False
        self._trigger = 0.0
        self._grip_button = False

    def update(self, session: xr.Session, xr_time_now: xr.Time):
        steamvr_location = # TODO: receive update
        steamvr_orientation = # TODO: receive update
        self._location = steamvr_to_standard_frame_transform(steamvr_location)
        self._orientation = steamvr_to_standard_frame_transform(steamvr_orientation)


    @property
    def location(self) -> Vector:
        """
        Get the location of the controller.

        Returns:
            The location of the controller in world frame, in meters.
        """
        return self._location

    @property
    def orientation(self) -> Quaternion:
        """
        Get the orientation of the controller.

        Returns:
            The orientation of the controller in world frame.
        """
        return self._orientation

    @property
    def menu_button(self) -> bool:
        """
        Get the state of the menu button.

        Returns:
            The state of the menu button as a boolean.
        """
        return self._menu_button.current_state

    @property
    def trackpad_x(self) -> float:
        """
        Get the state of the trackpad x axis.

        Returns:
            The state of the trackpad x axis as a float.
        """
        return self._trackpad_x.current_state

    @property
    def trackpad_y(self) -> float:
        """
        Get the state of the trackpad y axis.

        Returns:
            The state of the trackpad y axis as a float.
        """
        return self._trackpad_y.current_state

    @property
    def trackpad_button(self) -> bool:
        """
        Get the state of the trackpad button.

        Returns:
            The state of the trackpad button as a boolean.
        """
        return self._trackpad_button.current_state

    @property
    def trigger(self) -> float:
        """
        Get the state of the trigger.

        Returns:
            The state of the trigger as a float.
        """
        return self._trigger.current_state

    @property
    def grip_button(self) -> bool:
        """
        Get the state of the grip button.

        Returns:
            The state of the grip button as a boolean.
        """
        return self._grip_button.current_state
