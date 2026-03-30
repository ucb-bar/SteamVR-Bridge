from dataclasses import dataclass
from typing import List

from .base import BaseConfig, DeviceConfig


@dataclass
class FourPointArmCfg(BaseConfig):
    devices: List[DeviceConfig] = [
        DeviceConfig(name="base_tracker", role="base", kind="tracker"),
        DeviceConfig(name="left_tracker", role="left", kind="tracker"),
        DeviceConfig(name="right_tracker", role="right", kind="tracker"),
        DeviceConfig(name="top_tracker", role="top", kind="tracker"),
    ]
