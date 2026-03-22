from dataclasses import dataclass


@dataclass(frozen=True)
class ControllerConfig:
    key: str
    name: str
    user_path: str


LEFT_CONTROLLER = ControllerConfig(
    key="left",
    name="Left",
    user_path="/user/hand/left",
)
RIGHT_CONTROLLER = ControllerConfig(
    key="right",
    name="Right",
    user_path="/user/hand/right",
)
TWO_CONTROLLERS = (LEFT_CONTROLLER, RIGHT_CONTROLLER)


@dataclass(frozen=True)
class SteamVrBridgeConfig:
    controllers: tuple[ControllerConfig, ...] = ()
    tracker_roles: tuple[str, ...] | None = None
    name: str = "custom"

    def __post_init__(self):
        controller_keys = [controller.key for controller in self.controllers]
        if len(controller_keys) != len(set(controller_keys)):
            raise ValueError("Controller keys must be unique.")

        if self.tracker_roles is not None and len(self.tracker_roles) != len(set(self.tracker_roles)):
            raise ValueError("Tracker roles must be unique.")


class TwoControllersConfig(SteamVrBridgeConfig):
    def __init__(self):
        super().__init__(
            controllers=TWO_CONTROLLERS,
            tracker_roles=(),
            name="two_controllers",
        )


class TwoControllersTwoElbowTrackersConfig(SteamVrBridgeConfig):
    def __init__(self):
        super().__init__(
            controllers=TWO_CONTROLLERS,
            tracker_roles=("left_elbow", "right_elbow"),
            name="two_controllers_two_elbow_trackers",
        )


class TwoControllersFourElbowWristTrackersConfig(SteamVrBridgeConfig):
    def __init__(self):
        super().__init__(
            controllers=TWO_CONTROLLERS,
            tracker_roles=("left_elbow", "right_elbow", "left_wrist", "right_wrist"),
            name="two_controllers_four_elbow_wrist_trackers",
        )


class FourElbowWristTrackersConfig(SteamVrBridgeConfig):
    def __init__(self):
        super().__init__(
            controllers=(),
            tracker_roles=("left_elbow", "right_elbow", "left_wrist", "right_wrist"),
            name="four_elbow_wrist_trackers",
        )


class TwoControllersFiveFootWaistElbowTrackersConfig(SteamVrBridgeConfig):
    def __init__(self):
        super().__init__(
            controllers=TWO_CONTROLLERS,
            tracker_roles=("left_foot", "right_foot", "waist", "left_elbow", "right_elbow"),
            name="two_controllers_five_foot_waist_elbow_trackers",
        )


EXAMPLE_BRIDGE_CONFIGS = {
    config_cls.__name__: config_cls
    for config_cls in (
        TwoControllersConfig,
        TwoControllersTwoElbowTrackersConfig,
        TwoControllersFourElbowWristTrackersConfig,
        FourElbowWristTrackersConfig,
        TwoControllersFiveFootWaistElbowTrackersConfig,
    )
}

DEFAULT_BRIDGE_CONFIG = TwoControllersTwoElbowTrackersConfig()


def resolve_bridge_config(
    config: SteamVrBridgeConfig | type[SteamVrBridgeConfig] | None = None,
    tracker_roles=None,
) -> SteamVrBridgeConfig:
    if tracker_roles is not None:
        if config is not None:
            raise ValueError("Pass either config or tracker_roles, not both.")
        return SteamVrBridgeConfig(
            controllers=TWO_CONTROLLERS,
            tracker_roles=tuple(tracker_roles),
            name="legacy_tracker_roles",
        )

    if config is None:
        return DEFAULT_BRIDGE_CONFIG

    if isinstance(config, SteamVrBridgeConfig):
        return config

    if isinstance(config, type) and issubclass(config, SteamVrBridgeConfig):
        return config()

    raise TypeError("config must be a SteamVrBridgeConfig instance or subclass.")


def resolve_named_bridge_config(name: str) -> type[SteamVrBridgeConfig]:
    try:
        return EXAMPLE_BRIDGE_CONFIGS[name]
    except KeyError as exc:
        valid = ", ".join(EXAMPLE_BRIDGE_CONFIGS)
        raise ValueError(f"Unknown bridge config '{name}'. Valid choices: {valid}.") from exc
