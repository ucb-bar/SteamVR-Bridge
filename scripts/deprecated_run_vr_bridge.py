#!/usr/bin/env python3
"""
Deprecated compatibility wrapper for the old `scripts/run_vr_bridge.py`.

This preserves the legacy UDP payload shape:

{
    "left": {
        "pose": [[... 4x4 homogeneous transform ...]],
        "button_pressed": bool,
        "trigger": float,
    },
    "right": {
        "pose": [[... 4x4 homogeneous transform ...]],
        "button_pressed": bool,
        "trigger": float,
    },
}
"""

from __future__ import annotations

import time

import numpy as np
from udpack import UDP

from steamvr_bridge import SteamVrSession


def controller_pose_matrix(controller) -> list[list[float]]:
    pose = np.eye(4, dtype=float)
    pose[:3, :3] = np.array(controller.orientation.to_matrix())
    pose[:3, 3] = np.array(list(controller.location), dtype=float)
    return pose.tolist()


def default_controller_state() -> dict[str, list[list[float]] | bool | float]:
    return {
        "pose": np.eye(4, dtype=float).tolist(),
        "button_pressed": False,
        "trigger": 0.0,
    }


if __name__ == "__main__":
    print(
        "Deprecated: use `scripts/stream.py` or `scripts/visualize.py` for the current API.",
        flush=True,
    )

    session = SteamVrSession()
    udp = UDP(recv_addr=None, send_addr=("0.0.0.0", 11005))

    try:
        while True:
            session.update()

            controller_states = {
                "left": default_controller_state(),
                "right": default_controller_state(),
            }

            left_devices = session.get_devices_by_role("left")
            right_devices = session.get_devices_by_role("right")

            left_controller = left_devices[0] if left_devices else None
            right_controller = right_devices[0] if right_devices else None

            if left_controller is not None:
                controller_states["left"]["pose"] = controller_pose_matrix(left_controller)
                controller_states["left"]["button_pressed"] = bool(left_controller.grip_button)
                controller_states["left"]["trigger"] = float(left_controller.trigger)

            if right_controller is not None:
                controller_states["right"]["pose"] = controller_pose_matrix(right_controller)
                controller_states["right"]["button_pressed"] = bool(right_controller.grip_button)
                controller_states["right"]["trigger"] = float(right_controller.trigger)

            if left_controller is not None:
                lp = left_controller.location
            else:
                lp = np.zeros(3, dtype=float)

            if right_controller is not None:
                rp = right_controller.location
            else:
                rp = np.zeros(3, dtype=float)

            lt = controller_states["left"]["trigger"]
            rt = controller_states["right"]["trigger"]
            lg = controller_states["left"]["button_pressed"]
            rg = controller_states["right"]["button_pressed"]

            print(
                f"[{time.time():.1f}] "
                f"L: pos=({lp[0]:7.3f}, {lp[1]:7.3f}, {lp[2]:7.3f}) grip={'●' if lg else '○'} trig={lt:.2f} | "
                f"R: pos=({rp[0]:7.3f}, {rp[1]:7.3f}, {rp[2]:7.3f}) grip={'●' if rg else '○'} trig={rt:.2f}",
                flush=True,
            )

            udp.send_dict(controller_states)
    except KeyboardInterrupt:
        print("Keyboard interrupt detected. Exiting...")
    finally:
        session.stop()
