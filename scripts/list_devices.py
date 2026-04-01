#!/usr/bin/env python3
"""
List currently detected SteamVR tracked devices and their public metadata.
"""

from steamvr_bridge import SteamVrSession


if __name__ == "__main__":
    session = SteamVrSession()
    try:
        for device in session.tracked_devices:
            print(
                f"name={device.name:16s} "
                f"kind={device.kind:16s} "
                f"role={device.role:16s} "
                f"model_number={device.model_number:16s}"
            )
    finally:
        session.stop()
