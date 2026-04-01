from __future__ import annotations

import openvr

from .vive_device import DeviceIdentity, ViveDevice


class ViveBaseStation(ViveDevice):
    """
    A class representing a SteamVR base station / tracking reference.

    Args:
        vr_system: The OpenVR system handle.
        identity: User-facing device metadata.
    """

    visualization_asset_filename = "ObjModelViveBaseStation2.obj"

    def __init__(self, vr_system: openvr.IVRSystem, identity: DeviceIdentity):
        super().__init__(vr_system=vr_system, identity=identity)
