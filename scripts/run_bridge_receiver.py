"""
Simple receiver script that receives controller state dicts from run_vr_bridge.py over UDP.
Run this on the machine that should receive VR controller data (the bridge sends to recv_addr).
"""
import time
import pickle

import numpy as np
from scipy.spatial.transform import Rotation
from udpack import UDP


def _format_delta_segment(label: str, state: dict) -> str:
    rel_loc = state["relative_location"]
    loc = rel_loc if isinstance(rel_loc, (list, tuple)) else [rel_loc.x, rel_loc.y, rel_loc.z]
    rel_quat = state["relative_orientation"]
    delta_rpy = np.rad2deg(
        Rotation.from_quat(rel_quat, scalar_first=True).as_euler("xyz")
    )
    return (
        f"{label}: Δpos=({loc[0]:5.2f}, {loc[1]:5.2f}, {loc[2]:5.2f}) "
        f"Δrpy=({delta_rpy[0]:5.2f}, {delta_rpy[1]:5.2f}, {delta_rpy[2]:5.2f})°"
    )


def _state_label(key: str, state: dict) -> str:
    role = state.get("role")
    if role:
        return role
    name = state.get("name")
    if name:
        return name
    return key


if __name__ == "__main__":
    # Must match the send_addr used by run_vr_bridge.py - receiver listens on this port
    udp = UDP(recv_addr=("0.0.0.0", 11005), send_addr=None)

    print("Waiting for VR bridge data on port 11005... (Ctrl+C to stop)")
    print("-" * 80)

    start_time = time.time()

    while True:
        buffer = udp.recv(bufsize=4096, timeout=1.0)
        controller_states = pickle.loads(buffer)
        if controller_states is None:
            continue

        t = time.time() - start_time
        segments = [
            _format_delta_segment(_state_label(key, state), state)
            for key, state in controller_states.items()
        ]

        print(
            f"[{t:.3f}] {' | '.join(segments)}",
            flush=True,
        )
