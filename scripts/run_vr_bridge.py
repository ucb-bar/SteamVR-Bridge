import argparse
import time
import pickle
import sys

from scipy.spatial.transform import Rotation
import numpy as np
from udpack import UDP
from steamvr_bridge import (
    EXAMPLE_BRIDGE_CONFIGS,
    FourElbowWristTrackersConfig,
    SteamVrBridge,
)


ACTIVE_TRACKING_CONFIG = FourElbowWristTrackersConfig
CONFIG_CHOICES = EXAMPLE_BRIDGE_CONFIGS


def _empty_state(device):
    return {
        "key": device.state_key,
        "kind": device.kind,
        "name": device.name,
        "role": getattr(device, "role", None),
        "location": [0, 0, 0],  # (x, y, z) in meters
        "orientation": [1, 0, 0, 0],  # (qw, qx, qy, qz) in quaternion
        "relative_location": [0, 0, 0],
        "relative_orientation": [1, 0, 0, 0],
        "grip_button_pressed": False,
        "trigger": 0,  # 0.0 to 1.0
    }


def _update_state_slot(state_slot, device):
    orientation = device.orientation
    relative_orientation = device.relative_orientation
    state_slot["location"][:] = device.location.as_numpy()
    state_slot["orientation"][:] = [
        orientation.w,
        orientation.x,
        orientation.y,
        orientation.z,
    ]
    state_slot["relative_location"][:] = device.relative_location.as_numpy()
    state_slot["relative_orientation"][:] = [
        relative_orientation.w,
        relative_orientation.x,
        relative_orientation.y,
        relative_orientation.z,
    ]
    state_slot["grip_button_pressed"] = device.grip_button_pressed
    state_slot["trigger"] = device.trigger


def _render_live_output(line_1, line_2, has_drawn):
    if has_drawn:
        sys.stdout.write("\x1b[2F")
    sys.stdout.write("\x1b[2K" + line_1 + "\n")
    sys.stdout.write("\x1b[2K" + line_2 + "\n")
    sys.stdout.flush()
    return True


def _parse_args():
    parser = argparse.ArgumentParser(
        description="Run the SteamVR bridge and stream tracked device state over UDP.",
    )
    parser.add_argument(
        "--config",
        choices=tuple(CONFIG_CHOICES),
        default=ACTIVE_TRACKING_CONFIG.__name__,
        help="Tracking config class to use.",
    )
    return parser.parse_args()


def _format_controller_segment(device, state):
    orientation = state["orientation"]
    rpy = np.rad2deg(
        Rotation.from_quat(orientation, scalar_first=True).as_euler("xyz")
    )
    location = state["location"]
    relative_location = state["relative_location"]
    grip = state["grip_button_pressed"]
    trigger = state["trigger"]
    return (
        f"{device.name}: "
        f"pos=({location[0]:5.2f}, {location[1]:5.2f}, {location[2]:5.2f}) "
        f"rpy=({rpy[0]:4.0f}, {rpy[1]:4.0f}, {rpy[2]:4.0f})° "
        f"Δ=({relative_location[0]:5.2f}, {relative_location[1]:5.2f}, {relative_location[2]:5.2f}) "
        f"grip={'●' if grip else '○'} trig={trigger:.2f} ({'●' if trigger == 1.0 else '○'})"
    )


def _format_tracker_segment(device, state):
    orientation = state["orientation"]
    rpy = np.rad2deg(
        Rotation.from_quat(orientation, scalar_first=True).as_euler("xyz")
    )
    location = state["location"]
    relative_location = state["relative_location"]
    return (
        f"{device.role}: "
        f"pos=({location[0]:5.2f}, {location[1]:5.2f}, {location[2]:5.2f}) "
        f"rpy=({rpy[0]:4.0f}, {rpy[1]:4.0f}, {rpy[2]:4.0f})° "
        f"Δ=({relative_location[0]:5.2f}, {relative_location[1]:5.2f}, {relative_location[2]:5.2f})"
    )


if __name__ == "__main__":
    args = _parse_args()
    bridge = SteamVrBridge(config=CONFIG_CHOICES[args.config])

    udp = UDP(recv_addr=None, send_addr=("0.0.0.0", 11005))

    states = {
        device.state_key: _empty_state(device)
        for device in bridge.tracked_devices
    }

    start_time = time.time()
    prev_time = time.time()
    has_drawn_output = False

    try:
        while True:
            bridge.update()

            # update states
            for device in bridge.tracked_devices:
                _update_state_slot(states[device.state_key], device)

            current_time = time.time()
            if current_time - prev_time > (1 / 30.):
                prev_time = current_time
                t = current_time - start_time

                controller_segments = [
                    _format_controller_segment(controller, states[controller.state_key])
                    for controller in bridge.controllers
                ]
                tracker_segments = [
                    _format_tracker_segment(tracker, states[tracker.state_key])
                    for tracker in bridge.trackers
                ]
                line_1 = (
                    f"[{t:.3f}] Controllers: " + " | ".join(controller_segments)
                    if controller_segments
                    else f"[{t:.3f}] Controllers: none"
                )
                line_2 = (
                    "Trackers: " + " | ".join(tracker_segments)
                    if tracker_segments
                    else "Trackers: none"
                )
                has_drawn_output = _render_live_output(line_1, line_2, has_drawn_output)

            # udp.send_dict(states)
            udp.send(pickle.dumps(states))

    except KeyboardInterrupt:
        if has_drawn_output:
            sys.stdout.write("\n")
            sys.stdout.flush()
        print("Keyboard interrupt detected. Exiting...")

    finally:
        bridge.exit()
        # udp.close()
