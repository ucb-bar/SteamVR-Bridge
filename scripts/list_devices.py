#!/usr/bin/env python3
"""
List SteamVR/OpenXR devices (headset, controllers, trackers) and their tracking status.

Requires SteamVR to be running with the headset and controllers visible to the base station.
"""

from steamvr_bridge import SteamVrSession


if __name__ == "__main__":
    session = SteamVrSession(BaseConfig())

    devices = session.enumerate_devices()
    for device in devices:
        print(device.name)
