import openvr

from mathutils import Vector, Quaternion

from ..transform import steamvr_to_standard_frame_transform


class ViveTracker:
    """
    A class representing the VIVE Tracker 2.0 or 3.0.

    Args:
        instance: The OpenVR instance.
        name: The name of the tracker.
        role: The role of the tracker.
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

    def update(self, session: xr.Session, xr_time_now: xr.Time):
        steamvr_location = # TODO: receive update
        steamvr_orientation = # TODO: receive update
        self._location = steamvr_to_standard_frame_transform(steamvr_location)
        self._orientation = steamvr_to_standard_frame_transform(steamvr_orientation)


    @property
    def location(self) -> Vector:
        """
        Get the location of the tracker.

        Returns:
            The location of the tracker in world frame, in meters.
        """
        return self._location

    @property
    def orientation(self) -> Quaternion:
        """
        Get the orientation of the tracker.

        Returns:
            The orientation of the tracker in world frame.
        """
        return self._orientation
