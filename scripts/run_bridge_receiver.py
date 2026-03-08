"""
Simple receiver script that receives controller state dicts from run_vr_bridge.py over UDP.
Run this on the machine that should receive VR controller data (the bridge sends to recv_addr).
"""
import time

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
        controller_states = udp.recv_dict(timeout=1.0)
        if controller_states is None:
            continue

        left = controller_states.get("left", {})
        right = controller_states.get("right", {})

        loc_l = left.get("location", [0, 0, 0])
        loc_r = right.get("location", [0, 0, 0])
        trig_l = left.get("trigger", 0)
        trig_r = right.get("trigger", 0)
        grip_l = left.get("button_pressed", False)
        grip_r = right.get("button_pressed", False)
        rel_loc_l = left.get("relative_location", [0, 0, 0])
        rel_loc_r = right.get("relative_location", [0, 0, 0])
        ori_l = left.get("orientation", [1, 0, 0, 0])
        ori_r = right.get("orientation", [1, 0, 0, 0])
        rpy_l = np.rad2deg(
            Rotation.from_quat([ori_l.x, ori_l.y, ori_l.z, ori_l.w]).as_euler("xyz")
        )
        rpy_r = np.rad2deg(
            Rotation.from_quat([ori_r.x, ori_r.y, ori_r.z, ori_r.w]).as_euler("xyz")
        )
        t = time.time() - start_time

        print(
            f"[{t:.3f}] "
            f"L: pos=({loc_l.x:5.2f}, {loc_l.y:5.2f}, {loc_l.z:5.2f}) "
            f"rpy=({rpy_l[0]:4.0f}, {rpy_l[1]:4.0f}, {rpy_l[2]:4.0f})° "
            f"Δ=({rel_loc_l.x:5.2f}, {rel_loc_l.y:5.2f}, {rel_loc_l.z:5.2f}) grip={'●' if grip_l else '○'} trig={trig_l:.2f} ({'●' if trig_l == 1.0 else '○'}) | "
            f"R: pos=({loc_r.x:5.2f}, {loc_r.y:5.2f}, {loc_r.z:5.2f}) "
            f"rpy=({rpy_r[0]:4.0f}, {rpy_r[1]:4.0f}, {rpy_r[2]:4.0f})° "
            f"Δ=({rel_loc_r.x:5.2f}, {rel_loc_r.y:5.2f}, {rel_loc_r.z:5.2f}) grip={'●' if grip_r else '○'} trig={trig_r:.2f} ({'●' if trig_r == 1.0 else '○'})",
            flush=True,
        )
