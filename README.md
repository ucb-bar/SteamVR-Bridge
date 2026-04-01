# SteamVR Bridge

`steamvr-bridge` is a small Python library for reading tracked-device state from SteamVR/OpenVR and exposing it as a robotics-friendly API.

It is used in the Berkeley Humanoid Lite teleoperation stack and is designed for:

- enumerating tracked SteamVR devices
- reading poses, velocities, and controller inputs
- streaming device state over UDP
- visualizing live tracking data with Rerun

## Requirements

- Python 3.10 or newer
- Steam and SteamVR installed
- Ubuntu 24.04, Windows 10, or Windows 11

## Installation

This repository uses `uv` for environment and dependency management.

1. Install [uv](https://docs.astral.sh/uv/getting-started/installation/).

2. Sync the project environment

```bash
uv sync
```

3. Run scripts

```bash
uv run ./scripts/list_devices.py
```

```bash
uv run ./scripts/visualize.py
```

```bash
uv run ./scripts/stream.py --host 127.0.0.1 --port 5000 --rate 100
```

A deprecated compatibility wrapper for the older controller-only UDP payload is still available for BHL project:

```bash
uv run ./scripts/deprecated_run_vr_bridge.py
```

## Coordinate Convention

SteamVR Bridge converts raw SteamVR poses into a standard robotics frame:

- `+X` forward
- `+Y` left
- `+Z` up

The coordinate frames of the SteamVR devices are defined as follows:

<table>
  <tr>
    <td align="center">
      <img src="https://github.com/user-attachments/assets/19e4d02b-abd5-4c4a-b4a2-329967ce4052" height="200"/><br/>
      Vive Controller
    </td>
    <td align="center">
      <img src="https://github.com/user-attachments/assets/acc924cd-9e4d-436f-92c6-fc964866aefa" height="200"/><br/>
      Vive Tracker
    </td>
    <td align="center">
      <img src="https://github.com/user-attachments/assets/d8942896-b0bf-4875-a0f4-538e3c653598" height="200"/><br/>
      Vive Base Station
    </td>
    <td align="center">
      <img src="https://github.com/user-attachments/assets/dd404d9a-a932-417a-9247-3e5914539dd1" height="200"/><br/>
      Vive Pro HMD
    </td>
  </tr>
</table>

Note that the SteamVR standing-space origin and heading still come from SteamVR Room Setup. If you re-run Room Setup, the reported world frame can change accordingly.

## Device Discovery And Roles

`SteamVrSession` auto-discovers connected tracked devices and currently exposes:

- HMDs
- controllers
- trackers
- base stations / tracking references

Controller roles come from SteamVR hand-role metadata such as `left` and `right`.

Tracker roles are resolved from SteamVR tracker assignments when available. For example, a tracker assigned in SteamVR as waist or left foot is exposed through the corresponding `role` string.

## Quick Start

```python
from steamvr_bridge import SteamVrSession

session = SteamVrSession()

try:
    session.update()

    for device in session.tracked_devices:
        print(device.name, device.kind, device.role, tuple(device.location))

    left_controller = session.get_device_by_role("left")
    print(left_controller.trigger)
finally:
    session.stop()
```

## Troubleshooting

### SteamVR Error 307

`IPC Compositor Invalid Connect Response`

This is commonly caused by missing Vulkan/NVIDIA runtime pieces on Linux or by launching SteamVR from an unsupported display-server session.

#### 1. Verify that you are on X11, not Wayland

SteamVR currently requires an X11 session on Linux.

```bash
echo $XDG_SESSION_TYPE
```

The output must be `x11`.

#### 2. Confirm that the NVIDIA driver is active

```bash
nvidia-smi
```

If this fails or shows a driver mismatch, fix the driver installation first.

#### 3. Install the required Vulkan runtime packages

```bash
sudo apt install vulkan-tools libvulkan1
```

Reboot after installation.

#### 4. Check the active Vulkan driver stack

```bash
vulkaninfo | grep driverName
```

You should see the NVIDIA driver in the reported list.

## Citation

If you find this code useful, we would appreciate it if you would cite our paper:

```bibtex
@article{chi2025demonstrating,
  title={Demonstrating Berkeley Humanoid Lite: An Open-source, Accessible, and Customizable 3D-printed Humanoid Robot},
  author={Yufeng Chi and Qiayuan Liao and Junfeng Long and Xiaoyu Huang and Sophia Shao and Borivoje Nikolic and Zhongyu Li and Koushil Sreenath},
  year={2025},
  eprint={2504.17249},
  archivePrefix={arXiv},
  primaryClass={cs.RO},
  url={https://arxiv.org/abs/2504.17249}, 
}
```

## Attribution

### 3D Models

Vive Controller and Vive Tracker models are sourced from [ViveInputUtility-Unity](https://github.com/ViveSoftware/ViveInputUtility-Unity/tree/develop/Assets/HTC.UnityPlugin/ViveInputUtility/Resources/Models).

"Valve Index Lighthouse/Basestation gen2" (https://skfb.ly/6WUwA) by F53 is licensed under Creative Commons Attribution (http://creativecommons.org/licenses/by/4.0/).

"HTC Vive Pro" (https://skfb.ly/6vU6x) by Eternal Realm is licensed under Creative Commons Attribution (http://creativecommons.org/licenses/by/4.0/).
