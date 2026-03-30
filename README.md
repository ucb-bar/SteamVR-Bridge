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

In SteamVR Room Setup, make sure that the arrow, which represents the Y axis direction, is pointing towards the **left** of the scene.


## Running the scripts

1. Launch SteamVR application. Make sure the headset and VR controllers can be seen by the base station.

2. Inspect the currently connected tracked devices:

```bash
uv run ./scripts/list_devices.py
```

3. Stream all detected tracked devices over UDP:

```bash
uv run ./scripts/stream.py --host 127.0.0.1 --port 5000
```

4. Visualize all detected tracked devices locally:

```bash
uv run ./scripts/visualize.py --rate 100
```

The session auto-discovers all connected HMDs, controllers, and trackers. Device lookup is based on SteamVR metadata, including `role` and `name`.


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


## Attribution

"Valve Index Lighthouse/Basestation gen2" (https://skfb.ly/6WUwA) by F53 is licensed under Creative Commons Attribution (http://creativecommons.org/licenses/by/4.0/).
