from __future__ import annotations

import json
import threading
import time
from collections import defaultdict
from pathlib import Path

import openvr

from .devices import (
    DeviceIdentity,
    ViveController,
    ViveControllerRole,
    ViveHmd,
    ViveTracker,
    ViveTrackerRole,
)
from .visualization import RerunVisualizer, RerunVisualizerConfig

TrackedDevice = ViveHmd | ViveController | ViveTracker


class SteamVrSession:
    def __init__(
        self,
        visualizer_config: RerunVisualizerConfig | None = None,
        update_rate_hz: float = 250.0,
    ):
        self.update_rate_hz = update_rate_hz
        self.is_stopped = threading.Event()
        self._update_thread = None
        self._lock = threading.RLock()
        self._is_shutdown = False
        self._tracker_role_assignments = self._load_tracker_role_assignments()
        self.application_type = None

        init_errors = []
        for application_type in (openvr.VRApplication_Scene, openvr.VRApplication_Other):
            try:
                openvr.init(application_type)
                self.application_type = application_type
                break
            except openvr.OpenVRError as exc:
                init_errors.append(exc)
        else:
            raise RuntimeError(
                "Failed to initialize OpenVR. Make sure SteamVR is running and a headset "
                "or tracking server is available."
            ) from init_errors[-1]

        self.vr_system = openvr.VRSystem()
        self.visualizer = (
            RerunVisualizer(visualizer_config) if visualizer_config is not None else None
        )
        self.tracked_devices: list[TrackedDevice] = []
        self._tracked_devices_by_role: dict[str, list[TrackedDevice]] = {}
        self._tracked_devices_by_name: dict[str, TrackedDevice] = {}
        self.refresh_tracked_devices()

    def _get_string_property(self, device_index: int, prop: int, default: str = "") -> str:
        try:
            return str(self.vr_system.getStringTrackedDeviceProperty(device_index, prop))
        except openvr.OpenVRError:
            return default

    def _get_int32_property(self, device_index: int, prop: int, default: int | None = None) -> int | None:
        try:
            return int(self.vr_system.getInt32TrackedDeviceProperty(device_index, prop))
        except openvr.OpenVRError:
            return default

    @staticmethod
    def _steamvr_settings_candidates() -> list[Path]:
        home = Path.home()
        return [
            home / ".local/share/Steam/config/steamvr.vrsettings",
            home / ".steam/steam/config/steamvr.vrsettings",
            home / "Library/Application Support/Steam/config/steamvr.vrsettings",
            home / "AppData/Local/openvr/steamvr.vrsettings",
            home / "AppData/Local/Steam/config/steamvr.vrsettings",
        ]

    def _load_tracker_role_assignments(self) -> dict[str, ViveTrackerRole]:
        for settings_path in self._steamvr_settings_candidates():
            if not settings_path.exists():
                continue

            try:
                with settings_path.open("r", encoding="utf-8") as settings_file:
                    settings_data = json.load(settings_file)
            except (OSError, json.JSONDecodeError):
                continue

            trackers = settings_data.get("trackers", {})
            if not isinstance(trackers, dict):
                continue

            tracker_role_assignments: dict[str, ViveTrackerRole] = {}
            for key, value in trackers.items():
                if not isinstance(key, str) or not isinstance(value, str):
                    continue

                tracker_role = ViveTracker.tracker_role_from_steamvr_role(value)
                if tracker_role is None:
                    continue

                tracker_role_assignments[key.lower()] = tracker_role

            return tracker_role_assignments

        return {}

    def _detect_controller_role(self, device_index: int) -> str:
        role_map = {
            openvr.TrackedControllerRole_Invalid: ViveControllerRole.INVALID.value,
            openvr.TrackedControllerRole_LeftHand: ViveControllerRole.LEFT.value,
            openvr.TrackedControllerRole_RightHand: ViveControllerRole.RIGHT.value,
            openvr.TrackedControllerRole_OptOut: ViveControllerRole.OPT_OUT.value,
            openvr.TrackedControllerRole_Treadmill: ViveControllerRole.TREADMILL.value,
            openvr.TrackedControllerRole_Stylus: ViveControllerRole.STYLUS.value,
        }

        controller_role = self.vr_system.getControllerRoleForTrackedDeviceIndex(device_index)
        if controller_role in role_map:
            return role_map[controller_role]

        role_hint = self._get_int32_property(
            device_index,
            openvr.Prop_ControllerRoleHint_Int32,
            default=openvr.TrackedControllerRole_Invalid,
        )
        return role_map.get(role_hint, ViveControllerRole.INVALID.value)

    def _detect_tracker_role(self, device_index: int, serial_number: str) -> str:
        controller_type = self._get_string_property(
            device_index,
            openvr.Prop_ControllerType_String,
        )
        tracker_role = ViveTracker.tracker_role_from_controller_type(controller_type)
        if tracker_role is not None:
            return ViveTracker.tracker_role_name(tracker_role)

        registered_device_type = self._get_string_property(
            device_index,
            openvr.Prop_RegisteredDeviceType_String,
        )

        lookup_candidates = {
            registered_device_type.lower(),
            f"/devices/htc/vive_tracker{serial_number}".lower(),
            f"/devices/htc/vive_tracker_{serial_number}".lower(),
            serial_number.lower(),
        }

        for candidate in lookup_candidates:
            if not candidate:
                continue
            tracker_role = self._tracker_role_assignments.get(candidate)
            if tracker_role is not None:
                return ViveTracker.tracker_role_name(tracker_role)

        serial_token = serial_number.lower()
        for device_path, tracker_role in self._tracker_role_assignments.items():
            if serial_token and serial_token in device_path:
                return ViveTracker.tracker_role_name(tracker_role)

        return "disabled"

    def _device_identity_from_index(self, device_index: int) -> DeviceIdentity | None:
        if not self.vr_system.isTrackedDeviceConnected(device_index):
            return None

        device_class = self.vr_system.getTrackedDeviceClass(device_index)
        serial_number = self._get_string_property(
            device_index,
            openvr.Prop_SerialNumber_String,
            default=f"device_{device_index}",
        )
        model_number = self._get_string_property(
            device_index,
            openvr.Prop_ModelNumber_String,
            default=serial_number,
        )

        if device_class == openvr.TrackedDeviceClass_HMD:
            role = "head"
            return DeviceIdentity(
                index=device_index,
                kind="hmd",
                name=serial_number,
                role=role,
                model_number=model_number,
            )

        if device_class == openvr.TrackedDeviceClass_Controller:
            role = self._detect_controller_role(device_index)
            return DeviceIdentity(
                index=device_index,
                kind="controller",
                name=serial_number,
                role=role,
                model_number=model_number,
            )

        if device_class == openvr.TrackedDeviceClass_GenericTracker:
            role = self._detect_tracker_role(device_index, serial_number)
            return DeviceIdentity(
                index=device_index,
                kind="tracker",
                name=serial_number,
                role=role,
                model_number=model_number,
            )

        return None

    def _instantiate_device(self, identity: DeviceIdentity) -> TrackedDevice:
        if identity.kind == "hmd":
            return ViveHmd(self.vr_system, identity)
        if identity.kind == "controller":
            return ViveController(self.vr_system, identity)
        if identity.kind == "tracker":
            return ViveTracker(self.vr_system, identity)
        raise ValueError(f"Unsupported device kind: {identity.kind}")

    def _enumerate_device_identities(self) -> list[DeviceIdentity]:
        detected_identities = []

        for device_index in range(openvr.k_unMaxTrackedDeviceCount):
            identity = self._device_identity_from_index(device_index)
            if identity is None:
                continue
            detected_identities.append(identity)

        return detected_identities

    def _rebuild_device_indexes(self):
        tracked_devices_by_role: dict[str, list[TrackedDevice]] = defaultdict(list)
        tracked_devices_by_name: dict[str, TrackedDevice] = {}

        for device in self.tracked_devices:
            tracked_devices_by_role[device.role.lower()].append(device)
            tracked_devices_by_name[device.name.lower()] = device

        self._tracked_devices_by_role = dict(tracked_devices_by_role)
        self._tracked_devices_by_name = tracked_devices_by_name

    def _refresh_tracked_devices_unlocked(self) -> list[TrackedDevice]:
        detected_identities = self._enumerate_device_identities()
        existing_by_name = {device.name.lower(): device for device in self.tracked_devices}
        refreshed_devices: list[TrackedDevice] = []

        for identity in detected_identities:
            existing_device = existing_by_name.get(identity.name.lower())
            can_reuse = (
                existing_device is not None
                and existing_device.kind == identity.kind
                and existing_device.device_index == identity.index
            )

            if can_reuse:
                existing_device.refresh_identity(identity)
                refreshed_devices.append(existing_device)
                continue

            refreshed_devices.append(self._instantiate_device(identity))

        self.tracked_devices = refreshed_devices
        self._rebuild_device_indexes()
        return list(self.tracked_devices)

    def refresh_tracked_devices(self) -> list[TrackedDevice]:
        with self._lock:
            return self._refresh_tracked_devices_unlocked()

    def get_devices_by_role(self, role: str) -> list[TrackedDevice]:
        with self._lock:
            return list(self._tracked_devices_by_role.get(role.lower(), []))

    def get_device_by_role(self, role: str) -> TrackedDevice:
        devices = self.get_devices_by_role(role)
        if not devices:
            raise ValueError(f"No device found for tracking role {role!r}")
        if len(devices) > 1:
            serial_numbers = ", ".join(device.name for device in devices)
            raise ValueError(
                f"Multiple devices found for tracking role {role!r}: {serial_numbers}"
            )
        return devices[0]

    def get_device_by_serial_number(self, serial_number: str) -> TrackedDevice:
        with self._lock:
            device = self._tracked_devices_by_name.get(serial_number.lower())
        if device is None:
            raise ValueError(f"No device found for serial number {serial_number!r}")
        return device

    def update(self):
        with self._lock:
            self._refresh_tracked_devices_unlocked()
            poses = self.vr_system.getDeviceToAbsoluteTrackingPose(
                openvr.TrackingUniverseStanding,
                0.0,
                openvr.k_unMaxTrackedDeviceCount,
            )

            for device in self.tracked_devices:
                pose = poses[device.device_index]
                controller_state = None

                if isinstance(device, ViveController):
                    try:
                        result, state = self.vr_system.getControllerState(device.device_index)
                    except openvr.OpenVRError:
                        result, state = False, None
                    controller_state = state if result else None

                if isinstance(device, ViveController):
                    device.update(pose, controller_state)
                else:
                    device.update(pose)

            if self.visualizer is not None:
                self.visualizer.log_devices(self.tracked_devices)

    def _update_loop(self):
        period = 1.0 / self.update_rate_hz if self.update_rate_hz > 0 else 0.0
        while not self.is_stopped.is_set():
            self.update()
            if period > 0:
                time.sleep(period)

    def run(self):
        if self._update_thread is not None and self._update_thread.is_alive():
            return

        self.is_stopped.clear()
        self._update_thread = threading.Thread(target=self._update_loop, daemon=True)
        self._update_thread.start()

    def stop(self):
        self.is_stopped.set()
        if self._update_thread is not None:
            self._update_thread.join()
            self._update_thread = None

        if not self._is_shutdown:
            openvr.shutdown()
            self._is_shutdown = True
