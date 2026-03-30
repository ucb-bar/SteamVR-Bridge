from dataclasses import dataclass

import rerun as rr


@dataclass
class RerunVisualizerConfig:
    app_name: str = "steamvr_bridge"


class RerunVisualizer:
    def __init__(self, config: RerunVisualizerConfig):
        pass
