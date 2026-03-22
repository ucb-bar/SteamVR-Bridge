"""Optional real-time visualization helpers for SteamVR Bridge."""

from __future__ import annotations

import importlib
from dataclasses import dataclass
from types import ModuleType
from typing import cast

from scipy.spatial.transform import Rotation


class VisualizationDependencyError(RuntimeError):
    """Raised when optional visualization dependencies are missing."""


@dataclass(frozen=True, slots=True)
class RerunVisualizerConfig:
    application_id: str = "steamvr-bridge"
    spawn: bool = True
    hmd_radius: float = 0.03
    controller_radius: float = 0.025
    tracker_radius: float = 0.025
    hmd_color: tuple[int, int, int] = (255, 220, 0)
    controller_color: tuple[int, int, int] = (64, 128, 255)
    tracker_color: tuple[int, int, int] = (255, 128, 64)
    show_coordinate_frames: bool = False
    coordinate_frame_axis_length: float = 0.08
    show_world_axes: bool = True


class RerunVisualizer:
    """Visualizer that logs SteamVR Bridge telemetry to `rerun`."""

    def __init__(self, config: RerunVisualizerConfig | None = None) -> None:
        self._config = config or RerunVisualizerConfig()
        self._rr = self._import_rerun()
        self._rr.init(self._config.application_id, spawn=self._config.spawn)
        if self._config.show_world_axes:
            self._log_pose_axes(
                "world/frame_axes",
                position=(0.0, 0.0, 0.0),
                quaternion=(0.0, 0.0, 0.0, 1.0),
            )

    def log_bridge(self, bridge, frame_index: int | None = None) -> None:
        if frame_index is not None:
            set_time_sequence = getattr(self._rr, "set_time_sequence", None)
            if callable(set_time_sequence):
                set_time_sequence("frame", frame_index)

        hmd_position = getattr(bridge, "_hmd_position", None)
        hmd_orientation = getattr(bridge, "_hmd_orientation", None)
        if hmd_position is not None and hmd_orientation is not None:
            position = (hmd_position.x, hmd_position.y, hmd_position.z)
            self._log_points(
                "world/hmd",
                [position],
                radius=self._config.hmd_radius,
                color=self._config.hmd_color,
            )
            if self._config.show_coordinate_frames:
                self._log_pose_axes(
                    "world/hmd_axes",
                    position=position,
                    quaternion=(
                        hmd_orientation.x,
                        hmd_orientation.y,
                        hmd_orientation.z,
                        hmd_orientation.w,
                    ),
                )

        for controller in bridge.controllers:
            self._log_device(
                path=f"world/controllers/{controller.state_key}",
                position=(controller.location.x, controller.location.y, controller.location.z),
                quaternion=(
                    controller.orientation.x,
                    controller.orientation.y,
                    controller.orientation.z,
                    controller.orientation.w,
                ),
                radius=self._config.controller_radius,
                color=self._config.controller_color,
                draw_axes=controller.pose_valid,
            )

        for tracker in bridge.trackers:
            self._log_device(
                path=f"world/trackers/{tracker.state_key}",
                position=(tracker.location.x, tracker.location.y, tracker.location.z),
                quaternion=(
                    tracker.orientation.x,
                    tracker.orientation.y,
                    tracker.orientation.z,
                    tracker.orientation.w,
                ),
                radius=self._config.tracker_radius,
                color=self._config.tracker_color,
                draw_axes=tracker.pose_valid,
            )

    def _log_device(
        self,
        *,
        path: str,
        position: tuple[float, float, float],
        quaternion: tuple[float, float, float, float],
        radius: float,
        color: tuple[int, int, int],
        draw_axes: bool,
    ) -> None:
        self._log_points(path, [position], radius=radius, color=color)
        if self._config.show_coordinate_frames and draw_axes:
            self._log_pose_axes(f"{path}/axes", position=position, quaternion=quaternion)

    def _log_points(
        self,
        path: str,
        points: list[tuple[float, float, float]],
        *,
        radius: float,
        color: tuple[int, int, int],
    ) -> None:
        self._rr.log(
            path,
            self._rr.Points3D(
                points,
                radii=[radius] * len(points),
                colors=[color] * len(points),
            ),
        )

    def _log_pose_axes(
        self,
        path: str,
        *,
        position: tuple[float, float, float],
        quaternion: tuple[float, float, float, float],
    ) -> None:
        px, py, pz = position
        qx, qy, qz, qw = quaternion
        rotation = Rotation.from_quat([qx, qy, qz, qw])
        axis_length = self._config.coordinate_frame_axis_length
        local_axes = (
            (axis_length, 0.0, 0.0),
            (0.0, axis_length, 0.0),
            (0.0, 0.0, axis_length),
        )
        axis_colors = ([255, 0, 0], [0, 255, 0], [0, 128, 255])
        segments = []
        for axis in local_axes:
            dx, dy, dz = rotation.apply(axis)
            segments.append(
                [
                    [px, py, pz],
                    [px + dx, py + dy, pz + dz],
                ]
            )

        if hasattr(self._rr, "LineStrips3D"):
            self._rr.log(path, self._rr.LineStrips3D(segments, colors=axis_colors))
            return

        fallback_points = [point for segment in segments for point in segment]
        fallback_colors = [
            axis_colors[0],
            axis_colors[0],
            axis_colors[1],
            axis_colors[1],
            axis_colors[2],
            axis_colors[2],
        ]
        self._rr.log(
            path,
            self._rr.Points3D(
                fallback_points,
                radii=[self._config.tracker_radius] * len(fallback_points),
                colors=fallback_colors,
            ),
        )

    @staticmethod
    def _import_rerun() -> ModuleType:
        try:
            return cast(ModuleType, importlib.import_module("rerun"))
        except ModuleNotFoundError as exc:
            raise VisualizationDependencyError(
                "rerun-sdk is required for visualization. Install it with "
                "`uv add rerun-sdk` or run the script with `uv run --with rerun-sdk`."
            ) from exc
