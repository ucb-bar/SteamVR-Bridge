"""
Stream tracked-device state over UDP, with optional live Rerun visualization.
"""

import argparse

from loop_rate_limiters import RateLimiter
from udpack import UDP
from steamvr_bridge import (
    RerunVisualizerConfig,
    SteamVrSession,
)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    parser.add_argument("--host", type=str, default="127.0.0.1")
    parser.add_argument("--port", type=int, default=5000)
    parser.add_argument("--rate", type=int, default=100, help="UDP transmission rate in Hz")
    parser.add_argument("--headless", action="store_true")

    args = parser.parse_args()

    udp = UDP(send_addr=(args.host, args.port))

    visualizer_config = None
    if not args.headless:
        visualizer_config = RerunVisualizerConfig()

    session = SteamVrSession(visualizer_config=visualizer_config)

    rate = RateLimiter(args.rate)

    try:
        while True:
            session.update()
            state_dict = {}

            for device in session.tracked_devices:
                entry = {
                    "kind": device.kind,
                    "name": device.name,
                    "role": device.role,
                    "model_number": device.model_number,
                    "is_connected": device.is_connected,
                    "is_pose_valid": device.is_pose_valid,
                    "location": list(device.location),
                    "orientation": [
                        device.orientation.w,
                        device.orientation.x,
                        device.orientation.y,
                        device.orientation.z,
                    ],
                    "velocity": list(device.velocity),
                    "angular_velocity": list(device.angular_velocity),
                }

                if hasattr(device, "menu_button"):
                    entry.update(
                        {
                            "menu_button": device.menu_button,
                            "trackpad_x": device.trackpad_x,
                            "trackpad_y": device.trackpad_y,
                            "trackpad_button": device.trackpad_button,
                            "trigger": device.trigger,
                            "grip_button": device.grip_button,
                        }
                    )

                state_dict[device.name] = entry

            udp.send_dict(state_dict)

            rate.sleep()

    except KeyboardInterrupt:
        print("Keyboard interrupt detected. Exiting...")

    finally:
        session.stop()
