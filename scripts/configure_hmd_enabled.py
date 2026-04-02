"""
Toggle SteamVR HMD requirements in the Linux SteamVR configuration files.
"""

import argparse
import json
from pathlib import Path


STEAMVR_DEFAULT_SETTINGS_PATH = "~/.steam/steam/steamapps/common/SteamVR/drivers/null/resources/settings/default.vrsettings"
STEAMVR_CONFIG_PATH = "~/.steam/steam/config/steamvr.vrsettings"


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("is_hmd_enabled", type=int)
    args = parser.parse_args()

    steamvr_default_settings_path = Path(STEAMVR_DEFAULT_SETTINGS_PATH).expanduser()
    steamvr_config_path = Path(STEAMVR_CONFIG_PATH).expanduser()

    # update default driver
    default_settings = json.load(open(steamvr_default_settings_path))

    if args.is_hmd_enabled:
        default_settings["driver_null"]["enable"] = False
    else:
        default_settings["driver_null"]["enable"] = True

    with open(steamvr_default_settings_path, "w") as f:
        json.dump(default_settings, f, indent=4)

    # update steamvr config file
    config = json.load(open(steamvr_config_path))

    if args.is_hmd_enabled:
        config["steamvr"]["requireHmd"] = True
        config["steamvr"]["forcedDriver"] = ""
        config["steamvr"]["activateMultipleDrivers"] = True
    else:
        config["steamvr"]["requireHmd"] = False
        config["steamvr"]["forcedDriver"] = "null"
        config["steamvr"]["activateMultipleDrivers"] = False

    with open(steamvr_config_path, "w") as f:
        json.dump(config, f, indent=4)

    if args.is_hmd_enabled:
        print("HMD Enabled")
    else:
        print("HMD Disabled")

    print("Successfully updated the configuration files:")
    print(f"  {steamvr_default_settings_path}")
    print(f"  {steamvr_config_path}")
