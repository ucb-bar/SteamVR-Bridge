from dataclasses import dataclass
from typing import List


@dataclass
class DeviceConfig:
    name: str
    role: str
    kind: str


@dataclass
class BaseConfig:

    enable_hmd: bool = False

    devices: List[DeviceConfig] = []
