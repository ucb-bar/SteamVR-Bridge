#!/usr/bin/env python3
"""
List SteamVR/OpenXR devices (headset, controllers, trackers) and their tracking status.

Requires SteamVR to be running with the headset and controllers visible to the base station.
Uses OpenXR enumeration to detect all connected input sources.
"""

import sys
import time

import xr
from steamvr_bridge import SteamVrBridge


def _enumerate_devices(bridge) -> list[tuple[str, str, str | None, str]]:
    """Enumerate all input sources bound to pose actions. Returns (name, status, extra, side)."""
    devices: list[tuple[str, str, str | None, str]] = []
    seen_paths: set[int] = set()

    def add_from_action(action, default_name: str, side: str):
        if bridge.session is None:
            return
        try:
            info = xr.BoundSourcesForActionEnumerateInfo(
                type=xr.StructureType.BOUND_SOURCES_FOR_ACTION_ENUMERATE_INFO,
                next=None,
                action=action,
            )
            paths = xr.enumerate_bound_sources_for_action(bridge.session, info)
            for path in paths:
                path_val = int(path)
                if path_val in seen_paths or path_val == xr.NULL_PATH:
                    continue
                seen_paths.add(path_val)
                try:
                    name_info = xr.InputSourceLocalizedNameGetInfo(
                        type=xr.StructureType.INPUT_SOURCE_LOCALIZED_NAME_GET_INFO,
                        next=None,
                        source_path=path_val,
                        which_components=(
                            xr.INPUT_SOURCE_LOCALIZED_NAME_USER_PATH_BIT
                            | xr.INPUT_SOURCE_LOCALIZED_NAME_INTERACTION_PROFILE_BIT
                        ),
                    )
                    name = xr.get_input_source_localized_name(bridge.session, name_info)
                except Exception:
                    name = default_name
                devices.append((name, "Connected", None, side))
        except Exception:
            pass

    add_from_action(bridge.left_controller.pose_action, "Left Controller", "left")
    add_from_action(bridge.right_controller.pose_action, "Right Controller", "right")

    return devices


def _check_tracking(
    bridge, devices: list[tuple[str, str, str | None, str]]
) -> list[tuple[str, str, str | None]]:
    """Update device list with tracking status and controller state."""
    result: list[tuple[str, str, str | None]] = []

    # Headset - always present when session is ready
    hmd_tracked = any(getattr(bridge._hmd_position, c) != 0 for c in ("x", "y", "z"))
    result.append(("Headset (HMD)", "Tracked" if hmd_tracked else "Present", None))

    def _safe_trigger(ctrl) -> float:
        t = getattr(ctrl, "_trigger", 0.0)
        return getattr(t, "current_state", t) if not isinstance(t, (int, float)) else float(t)

    left = bridge.left_controller
    right = bridge.right_controller
    left_tracked = any(getattr(left._position, c) != 0 for c in ("x", "y", "z"))
    right_tracked = any(getattr(right._position, c) != 0 for c in ("x", "y", "z"))

    for name, _status, _extra, side in devices:
        if side == "left":
            new_status = "Tracked" if left_tracked else "Not tracked"
            result.append((name, new_status, f"trigger={_safe_trigger(left):.2f}"))
        elif side == "right":
            new_status = "Tracked" if right_tracked else "Not tracked"
            result.append((name, new_status, f"trigger={_safe_trigger(right):.2f}"))
        else:
            result.append((name, _status, _extra))

    return result


def main() -> int:
    print("Connecting to SteamVR...", flush=True)
    print("Make sure SteamVR is running and the headset is visible to the base station.", flush=True)
    print(flush=True)

    try:
        bridge = SteamVrBridge()
    except Exception as e:
        print(f"Failed to connect to SteamVR: {e}", flush=True)
        return 1

    print("Initialized Bridge")

    # Run update loop until session is ready (with timeout)
    timeout = 30
    start = time.monotonic()
    while bridge.session_state != xr.SessionState.FOCUSED:
        if time.monotonic() - start > timeout:
            print("Timeout waiting for SteamVR session to become ready.", flush=True)
            return 1
        bridge.update()
        time.sleep(0.05)

    print("Session is ready", flush=True)

    bridge.update()
    # Run several updates to get valid tracking data (devices may need a few frames)
    # for _ in range(15):
    #     bridge.update()
    #     time.sleep(0.05)
    #     if bridge.session is None:
    #         print("Session ended unexpectedly.", flush=True)
    #         return 1

    print("Enumerating devices...", flush=True)

    # Enumerate all connected devices via OpenXR
    enumerated = _enumerate_devices(bridge)

    # If enumeration returned nothing, fall back to known controllers
    if not enumerated:
        enumerated = [
            ("Left Controller", "Connected", None, "left"),
            ("Right Controller", "Connected", None, "right"),
        ]

    while True:
        bridge.update()

        devices = _check_tracking(bridge, enumerated)

        print("SteamVR devices:", flush=True)
        print("-" * 50, flush=True)
        for item in devices:
            if len(item) == 3 and item[2] is not None:
                name, status, extra = item
                print(f"  {name}: {status} ({extra})", flush=True)
            else:
                name, status = item[0], item[1]
                print(f"  {name}: {status}", flush=True)
        print(flush=True)

        bridge.exit()
        return 0


if __name__ == "__main__":
    sys.exit(main())
