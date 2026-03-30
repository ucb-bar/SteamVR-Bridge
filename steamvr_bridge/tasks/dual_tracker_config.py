from dataclasses import dataclass
from typing import List

from .base import BaseConfig, DeviceConfig


@dataclass
class DualControllerCfg(BaseConfig):
    devices: List[DeviceConfig] = [
        DeviceConfig(name="left_controller", role="left", kind="controller"),
        DeviceConfig(name="right_controller", role="right", kind="controller"),
    ]
