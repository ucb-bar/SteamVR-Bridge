"""
Simple receiver script that receives controller state dicts from run_vr_bridge.py over UDP.
Run this on the machine that should receive VR controller data (the bridge sends to recv_addr).
"""
import time

from cc.udp import UDP


if __name__ == "__main__":
    # Must match the send_addr used by run_vr_bridge.py - receiver listens on this port
    udp = UDP(recv_addr=("0.0.0.0", 11005), send_addr=None)

    print("Waiting for VR bridge data on port 11005... (Ctrl+C to stop)")
    print("-" * 80)

    while True:
        controller_states = udp.recv_dict(timeout=1.0)
        if controller_states is None:
            continue

        left = controller_states.get("left", {})
        right = controller_states.get("right", {})

        # Extract position from 4x4 pose matrix (last column is position in some conventions,
        # but run_vr_bridge uses position in columns 0:3 - check structure)
        # Pose matrix: left_rot_matrix[:, 0:3] has position in first 3 rows of cols 0-2
        # Actually looking at run_vr_bridge: left_rot_matrix[:, 0:3] = position - that assigns
        # to columns 0,1,2. So position is in pose[:3, 0], pose[:3, 1], pose[:3, 2]
        def pos_from_pose(pose):
            if not pose or len(pose) < 3:
                return 0, 0, 0
            return pose[0][0], pose[1][0], pose[2][0]

        lp = pos_from_pose(left.get("pose", []))
        rp = pos_from_pose(right.get("pose", []))
        lg = left.get("button_pressed", False)
        rg = right.get("button_pressed", False)
        lt = left.get("trigger", 0)
        rt = right.get("trigger", 0)

        print(
            f"[{time.time():.1f}]  "
            f"L: pos=({lp[0]:7.3f}, {lp[1]:7.3f}, {lp[2]:7.3f})  grip={'●' if lg else '○'}  trig={lt:.2f}  |  "
            f"R: pos=({rp[0]:7.3f}, {rp[1]:7.3f}, {rp[2]:7.3f})  grip={'●' if rg else '○'}  trig={rt:.2f}",
            flush=True,
        )
