"""
Continuously print tracked-device state and log it to the Rerun visualizer.
"""

import argparse
import sys

from loop_rate_limiters import RateLimiter
import numpy as np

from steamvr_bridge import RerunVisualizerConfig, SteamVrSession
from steamvr_bridge.devices import ViveController


def print_device_state(device):
    rpy = np.rad2deg(
        device.orientation.to_euler()
    )
    location = device.location
    # relative_location = device.relative_location
    summary = (
        f"{device.name}: "
        f"role={device.role:12s} "
        f"pos=({location[0]:5.2f}, {location[1]:5.2f}, {location[2]:5.2f}) "
        f"rpy=({rpy[0]:4.0f}, {rpy[1]:4.0f}, {rpy[2]:4.0f})°"
    )
    if isinstance(device, ViveController):
        grip = device.grip_button
        trigger = device.trigger
        summary += (
            f" grip={'●' if grip else '○'} trig={trigger:.2f} ({'●' if trigger == 1.0 else '○'})"
            f" trackpad_x={device.trackpad_x:.2f} trackpad_y={device.trackpad_y:.2f}"
            f" trackpad_button={'●' if device.trackpad_button else '○'}"
        )
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    parser.add_argument("--rate", type=int, default=100, help="UDP transmission rate in Hz")

    args = parser.parse_args()

    session = SteamVrSession(visualizer_config=RerunVisualizerConfig())

    rate = RateLimiter(args.rate)

    has_drawn_output = False
    previous_line_count = 0

    try:
        while True:
            session.update()

            lines = (
                [print_device_state(device) for device in session.tracked_devices]
                if session.tracked_devices
                else ["No tracked devices detected."]
            )
            if has_drawn_output:
                sys.stdout.write(f"\x1b[{previous_line_count}F")
            for line in lines:
                sys.stdout.write("\x1b[2K" + line + "\n")
            for _ in range(max(previous_line_count - len(lines), 0)):
                sys.stdout.write("\x1b[2K\n")
            sys.stdout.flush()
            has_drawn_output = True
            previous_line_count = len(lines)

            rate.sleep()

    except KeyboardInterrupt:
        if has_drawn_output:
            sys.stdout.write("\n")
            sys.stdout.flush()
        print("Keyboard interrupt detected. Exiting...")

    finally:
        session.stop()
