"""
Non-blocking SteamVR session that sends the device information through UDP.
"""

import argparse

from udpack import UDP
from steamvr_bridge import SteamVrSession
from loop_rate_limiters import RateLimiter


if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    parser.add_argument("--task", type=str, required=True)
    parser.add_argument("--host", type=str, default="127.0.0.1")
    parser.add_argument("--port", type=int, default=5000)
    parser.add_argument("--rate", type=int, default=100, help="UDP transmission rate in Hz")
    parser.add_argument("--headless", action="store_true")

    args = parser.parse_args()

    task_config = eval(args.task)

    udp = UDP(send_addr=(args.host, args.port))

    visualizer_config = None
    if not args.headless:
        visualizer_config = RerunVisualizerConfig()

    session = SteamVrSession(task_config=task_config, visualizer_config=visualizer_config)
    session.run()

    state_dict = {}

    rate = RateLimiter(args.rate)

    try:
        while True:
            session.update()

            for device in session.devices:
                # TODO

            udp.send(state_dict)

            rate.sleep()

    except KeyboardInterrupt:
        session.stop()
