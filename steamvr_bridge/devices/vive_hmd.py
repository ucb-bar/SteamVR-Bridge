import openvr

from mathutils import Vector, Quaternion

from ..transform import steamvr_to_standard_frame_transform


class ViveHmd:
    """
    A class representing the VIVE Head-Mounted Display (HMD).

    Args:
        instance: The OpenVR instance.
    """
    def __init__(
        self,
        instance: xr.Instance,
    ):
        self.instance = instance
        pass

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
        Get the location of the HMD.

        Returns:
            The location of the HMD in world frame, in meters.
        """
        return self._location

    @property
    def orientation(self) -> Quaternion:
        """
        Get the orientation of the HMD.

        Returns:
            The orientation of the HMD in world frame.
        """
        return self._orientation
