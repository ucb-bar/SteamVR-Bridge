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


## Running the script

1. Launch SteamVR application. Make sure the headset and VR controllers can be seen by the base station.

2. Run `run_vr_bridge.py`:

```powershell
uv run ./scripts/run_vr_bridge.py
```

3. Check if the VR controllers are tracked by pressing triggers. The console log should show changing values.
