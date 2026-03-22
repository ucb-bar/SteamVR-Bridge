#!/usr/bin/env python3
"""Visualize SteamVR Bridge controller and tracker poses in Rerun.

Examples:
    uv run --with rerun-sdk ./scripts/visualize_rerun.py
    uv run --with rerun-sdk ./scripts/visualize_rerun.py --config TwoControllersFourElbowWristTrackersConfig
    uv run --with rerun-sdk ./scripts/visualize_rerun.py --config FourElbowWristTrackersConfig --show-coordinate-frames
"""

from __future__ import annotations

import argparse
import time

from steamvr_bridge import (
    EXAMPLE_BRIDGE_CONFIGS,
    RerunVisualizer,
    RerunVisualizerConfig,
    SteamVrBridge,
    VisualizationDependencyError,
)

DEFAULT_CONFIG_NAME = "TwoControllersTwoElbowTrackersConfig"


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Visualize SteamVR Bridge telemetry in Rerun.",
    )
    parser.add_argument(
        "--config",
        choices=tuple(EXAMPLE_BRIDGE_CONFIGS),
        default=DEFAULT_CONFIG_NAME,
        help="Tracking config class to use.",
    )
    parser.add_argument(
        "--application-id",
        default="steamvr-bridge",
        help="Rerun application id.",
    )
    parser.add_argument(
        "--no-spawn",
        action="store_true",
        default=False,
        help="Do not spawn a local Rerun viewer.",
    )
    parser.add_argument(
        "--show-coordinate-frames",
        action="store_true",
        default=False,
        help="Render local XYZ frame axes for tracked poses.",
    )
    parser.add_argument(
        "--axis-length",
        type=float,
        default=0.08,
        help="Axis length in meters for rendered coordinate frames.",
    )
    parser.add_argument(
        "--sleep",
        type=float,
        default=0.0,
        help="Optional sleep in seconds between bridge updates.",
    )
    return parser.parse_args()


def _main() -> int:
    args = _parse_args()

    try:
        visualizer = RerunVisualizer(
            RerunVisualizerConfig(
                application_id=args.application_id,
                spawn=not args.no_spawn,
                show_coordinate_frames=args.show_coordinate_frames,
                coordinate_frame_axis_length=args.axis_length,
            )
        )
    except VisualizationDependencyError as exc:
        print(exc)
        return 1

    bridge = SteamVrBridge(config=EXAMPLE_BRIDGE_CONFIGS[args.config])
    frame_index = 0

    try:
        while True:
            bridge.update()
            visualizer.log_bridge(bridge, frame_index=frame_index)
            frame_index += 1
            if args.sleep > 0.0:
                time.sleep(args.sleep)
    except KeyboardInterrupt:
        print("Keyboard interrupt detected. Exiting...")
    finally:
        bridge.exit()

    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
