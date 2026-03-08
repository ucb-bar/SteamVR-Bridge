"""
Simple receiver script that receives controller state dicts from run_vr_bridge.py over UDP.
Run this on the machine that should receive VR controller data (the bridge sends to recv_addr).
"""
import time
import pickle

import numpy as np
from scipy.spatial.transform import Rotation
from udpack import UDP


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

        left = controller_states["left"]
        right = controller_states["right"]

        rel_loc_l = left["relative_location"]
        rel_loc_r = right["relative_location"]
        # Bridge sends lists [x,y,z]; normalize to indexable
        loc_l = rel_loc_l if isinstance(rel_loc_l, (list, tuple)) else [rel_loc_l.x, rel_loc_l.y, rel_loc_l.z]
        loc_r = rel_loc_r if isinstance(rel_loc_r, (list, tuple)) else [rel_loc_r.x, rel_loc_r.y, rel_loc_r.z]
        rel_quat_l = left["relative_orientation"]
        rel_quat_r = right["relative_orientation"]
        delta_rpy_l = np.rad2deg(Rotation.from_quat(rel_quat_l, scalar_first=True).as_euler("xyz"))
        delta_rpy_r = np.rad2deg(Rotation.from_quat(rel_quat_r, scalar_first=True).as_euler("xyz"))
        t = time.time() - start_time

        print(
            f"[{t:.3f}] "
            f"L: Δpos=({loc_l[0]:5.2f}, {loc_l[1]:5.2f}, {loc_l[2]:5.2f}) "
            f"Δrpy=({delta_rpy_l[0]:5.2f}, {delta_rpy_l[1]:5.2f}, {delta_rpy_l[2]:5.2f})° | "
            f"R: Δpos=({loc_r[0]:5.2f}, {loc_r[1]:5.2f}, {loc_r[2]:5.2f}) "
            f"Δrpy=({delta_rpy_r[0]:5.2f}, {delta_rpy_r[1]:5.2f}, {delta_rpy_r[2]:5.2f})°",
            flush=True,
        )
