import threading
from dataclasses import dataclass

import openvr

from .tasks import BaseConfig
from .visualization import RerunVisualizerConfig

from .devices import ViveHmd, ViveController, ViveTracker


class SteamVrSession:

    def __init__(self, task_config: BaseConfig, visualizer_config: RerunVisualizerConfig | None = None):
        self.is_stopped = threading.Event()
        self.update_thread = None

        self.devices = []

        # initialize all devices
        # TODO

    def enumerate_devices(self) -> list[ViveHmd | ViveController | ViveTracker]:
        """
        Enumerate and find all the connected devices.
        """
        # TODO: not sure if this should be a class method
        detected_devices = []
        # TODO: detect all devices

        return detected_devices

    def get_device_by_name(self, name: str) -> ViveHmd | ViveController | ViveTracker:
        for device in self.devices:
            if device.name == name:
                return device
        raise ValueError(f"Device {name} not found")

    def get_device_by_role(self, role: str) -> ViveHmd | ViveController | ViveTracker:
        for device in self.devices:
            if device.role == role:
                return device
        raise ValueError(f"Device with role {role} not found")

    def update(self):
        # TODO: properly implement this

        for device in self.devices:
            device.update(self.session, self.xr_time_now)

    def update_thread(self):
        while not self.is_stopped.is_set():
            self.update()
            # delay?

    def run(self):
        self.update_thread = threading.Thread(target=self.update_thread)
        self.update_thread.start()

    def stop(self):
        self.is_stopped.set()
        self.update_thread.join()
