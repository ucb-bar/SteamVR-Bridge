"""
Blocking SteamVR session that visualizes the device information through rerun visualizer.
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

    args = parser.parse_args()

    task_config = eval(args.task)

    session = SteamVrSession(task_config=task_config, visualizer_config=RerunVisualizerConfig())

    rate = RateLimiter(args.rate)

    try:
        while True:
            session.update()
            rate.sleep()

    except KeyboardInterrupt:
        session.stop()
