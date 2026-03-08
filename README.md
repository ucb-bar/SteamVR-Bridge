# SteamVR Bridge

SteamVR Bridge is a library for accessing motion capture data from SteamVR.

This is part of the codebase used for Berkeley Humanoid Lite teleoperation demonstration.


## Requirement

- Ubuntu 24.04 or Windows 10 or Windows 11

- Steam and SteamVR installed


## Setting up the environment

1. Install uv

on Ubuntu:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

on Windows:

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```


2. Create environment and install dependencies

```powershell
uv sync
```


## Setting up VR scene

In SteamVR Room Setup, make sure that the arrow, which represents the -Z axis direction, is pointing towards the **front** of the scene.

### Frame Conversion

SteamVR/OpenXR and this project use different axis conventions.

- SteamVR/OpenXR tracking frame: `X` right, `Y` up, `-Z` forward
- Robotics frame: `X` forward, `Y` left, `Z` up (which maps well to roll-pitch-yaw)

The bridge converts all tracked poses (HMD and controllers) into the robotics frame before exposing them.

Position conversion:

```text
x_robot = -z_vr
y_robot = -x_vr
z_robot =  y_vr
```

Orientation conversion (quaternion in `(w, x, y, z)`):

```text
q_robot = q_R * q_vr * q_R^-1
q_R = (0.5, 0.5, -0.5, -0.5)
```

`q_vr` is the OpenXR pose orientation (device-local -> SteamVR world). The bridge performs a full basis change into the robotics frame.

Quaternion format convention in this repository:

- Canonical order is always `(w, x, y, z)`.
- UDP payloads from `run_vr_bridge.py` use `(w, x, y, z)`.
- If using scipy `Rotation.from_quat`, pass `scalar_first=True` when providing bridge quaternions.

So `location`, `orientation`, `relative_location`, and `relative_orientation` from the bridge are all in the robotics frame.


## Running the script

1. Launch SteamVR application. Make sure the headset and VR controllers can be seen by the base station.

2. Run `run_vr_bridge.py`:

```powershell
uv run ./scripts/run_vr_bridge.py
```

3. Check if the VR controllers are tracked by pressing triggers. The console log should show changing values.


## Controller control modes

Each VIVE controller exposes a **relative pose** (position + orientation delta) in addition to its absolute pose. The relative pose is used for teleoperation (e.g., commanding a robot end-effector offset). The behavior is controlled by the **grip** and **trigger** buttons:

| Action | Result |
|--------|--------|
| **Grip** (press / release) | Toggle between *Following* and *Hold* modes. In Following mode, the relative pose updates every frame as the controller moves. In Hold mode, the relative pose stays fixed at its last value. |
| **Grip + Trigger** (both held, trigger fully pressed) | Reset delta location and rotation to zero and enter Following mode. |

The grip acts as a toggle on each press; grip+trigger always recenters translation and enables Following mode, regardless of the current mode.


## Citation

If you find this code useful, we would appreciate if you would cite our paper:

```
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

## Troubleshoot

### SteamVR Error 307

`IPC Compositor Invalid Connect Response`

This error is most commonly caused by missing 32-bit NVIDIA and/or Vulkan libraries, or by running under the wrong display server (Wayland instead of X11).

Follow the steps below to diagnose and fix the issue.

#### 1. Verify You’re on X11 (Not Wayland)

SteamVR currently requires an X11 session.

Check your session type:

```bash
echo $XDG_SESSION_TYPE
```

The output must be `x11`.

If it returns `wayland`, log out and select an X11 session from your display manager before continuing.

#### 2. Confirm NVIDIA Driver Is Loaded

Verify that the NVIDIA driver is active and matches the installed packages:

```bash
nvidia-smi
```

Example output:

```bash
Sun Mar  1 20:37:15 2026       
+-----------------------------------------------------------------------------------------+
| NVIDIA-SMI 590.48.01              Driver Version: 590.48.01      CUDA Version: 13.1     |
+-----------------------------------------+------------------------+----------------------+
| ... |
```

If this command fails or reports a mismatch, reinstall or fix your NVIDIA drivers before proceeding.

#### 3. Install Required Vulkan Libraries

Install Vulkan tools and runtime libraries:

```bash
sudo apt install vulkan-tools libvulkan1
```

After installation, **reboot your system**.

#### 4. Verify the Active Vulkan Driver

Check which Vulkan driver is being used:

```bash
vulkaninfo | grep driverName
```

Example output:

```bash
	driverName                                           = Intel open-source Mesa driver
	driverName                                           = NVIDIA
	driverName                                           = llvmpipe
```

You should see NVIDIA listed.
