from dataclasses import dataclass

from mathutils import Matrix, Quaternion, Vector

try:
    import rerun as rr
except ImportError:  # pragma: no cover - optional dependency at runtime
    rr = None


@dataclass
class RerunVisualizerConfig:
    app_name: str = "steamvr_bridge"
    spawn: bool = True


class RerunVisualizer:
    def __init__(self, config: RerunVisualizerConfig):
        if rr is None:
            raise RuntimeError(
                "Rerun visualizer requested, but the `rerun-sdk` package is not installed."
            )

        self.config = config
        self._logged_model_paths: set[str] = set()
        rr.init(config.app_name, spawn=config.spawn)
        rr.log("world", rr.ViewCoordinates.FLU, static=True)

    @staticmethod
    def _xyzw(quaternion: Quaternion) -> list[float]:
        return [quaternion.x, quaternion.y, quaternion.z, quaternion.w]

    @staticmethod
    def _color_for_kind(kind: str) -> list[int]:
        if kind == "controller":
            return [80, 200, 120, 255]
        if kind == "tracker":
            return [240, 160, 60, 255]
        if kind == "hmd":
            return [70, 140, 255, 255]
        if kind == "base_station":
            return [230, 230, 120, 255]
        return [220, 220, 220, 255]

    @staticmethod
    def _local_axes(axis_length: float = 0.08) -> list[list[float]]:
        basis = (
            Vector((axis_length, 0.0, 0.0)),
            Vector((0.0, axis_length, 0.0)),
            Vector((0.0, 0.0, axis_length)),
        )
        return [list(axis) for axis in basis]

    @staticmethod
    def _device_model_transform(device) -> Matrix:
        return device.device_to_local_transform.inverted()

    def _log_device_model(self, device, device_path: str):
        asset_path = device.visualization_asset_path()
        if asset_path is None or not asset_path.exists():
            return

        model_path = f"{device_path}/model"
        if model_path not in self._logged_model_paths:
            rr.log(model_path, rr.Asset3D(path=asset_path), static=True)
            self._logged_model_paths.add(model_path)

        model_transform = self._device_model_transform(device)
        rr.log(
            model_path,
            rr.Transform3D(
                translation=list(model_transform.to_translation()),
                # quaternion=rr.Quaternion(xyzw=self._xyzw(model_transform.to_quaternion())),
            ),
            static=True,
        )

    def _log_world_axes(self):
        rr.log(
            "world/axes",
            rr.Arrows3D(
                origins=[[0.0, 0.0, 0.0]] * 3,
                vectors=self._local_axes(axis_length=0.25),
                colors=[
                    [255, 80, 80, 255],
                    [80, 255, 120, 255],
                    [80, 140, 255, 255],
                ],
                labels=["world_x", "world_y", "world_z"],
                show_labels=True,
            ),
            static=True,
        )

    def log_devices(self, devices):
        self._log_world_axes()
        for device in devices:
            device_path = f"devices/{device.name}"
            color = self._color_for_kind(device.kind)

            rr.log(
                device_path,
                rr.Transform3D(
                    translation=list(device.location),
                    quaternion=rr.Quaternion(xyzw=self._xyzw(device.orientation)),
                ),
            )
            self._log_device_model(device, device_path)
            rr.log(
                f"{device_path}/marker",
                rr.Points3D(
                    [[0.0, 0.0, 0.0]],
                    radii=[0.03],
                    colors=[color],
                    labels=[device.name],
                    show_labels=True,
                ),
            )
            rr.log(
                f"{device_path}/axes",
                rr.Arrows3D(
                    origins=[[0.0, 0.0, 0.0]] * 3,
                    vectors=self._local_axes(),
                    colors=[
                        [255, 80, 80, 255],
                        [80, 255, 120, 255],
                        [80, 140, 255, 255],
                    ],
                ),
            )
