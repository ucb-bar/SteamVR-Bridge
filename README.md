# SteamVR Bridge

This is the codebase used for Berkeley Humanoid Lite teleoperation demonstration.

## Requirement

- Windows 10 or Windows 11

- Steam and SteamVR install


## Setting up VR scene

In SteamVR Room Setup, make sure that the arrow, which represents the Y axis direction, is pointing towards left of the world.

## Setting up the environment

1. Install uv

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

2. Create environment and install dependencies

```powershell
uv sync
```

## Running the script

1. Make sure the headset and VR controllers can be seen by the base station.

2. Run `run_vr_bridge.py`:

```powershell
uv run ./scripts/run_vr_bridge.py
```

3. Check if the VR controllers are tracked by pressing triggers. The console log should show changing values.

## Errata

When running the script for the first time, it will automatically launch the SteamVR application. However, SteamVR will need to spend some time to detect and connect to the controllers. This might leads to the Python code unable to retrieve the controller. If this happens, re-run the Python code after SteamVR application is ready.
