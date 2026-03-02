"""
Simple receiver script that receives controller state dicts from run_vr_bridge.py over UDP.
Run this on the machine that should receive VR controller data (the bridge sends to recv_addr).
"""
import time

from udpack import UDP


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

        def pos_from_pose(pose):
            """Extract translation from a 4x4 homogeneous transform (last column)."""
            if not pose or len(pose) < 3:
                return 0, 0, 0
            return pose[0][3], pose[1][3], pose[2][3]

        lp = pos_from_pose(left.get("pose", []))
        rp = pos_from_pose(right.get("pose", []))
        lg = left.get("button_pressed", False)
        rg = right.get("button_pressed", False)
        lt = left.get("trigger", 0)
        rt = right.get("trigger", 0)

        # relative_pose is [x, y, z, qw, qx, qy, qz]
        l_rel = left.get("relative_pose", [0, 0, 0, 1, 0, 0, 0])
        r_rel = right.get("relative_pose", [0, 0, 0, 1, 0, 0, 0])

        print(
            f"[{time.time():.1f}]  "
            f"L: pos=({lp[0]:7.3f}, {lp[1]:7.3f}, {lp[2]:7.3f})  "
            f"Δ=({l_rel[0]:7.3f}, {l_rel[1]:7.3f}, {l_rel[2]:7.3f})  grip={'●' if lg else '○'}  trig={lt:.2f}  |  "
            f"R: pos=({rp[0]:7.3f}, {rp[1]:7.3f}, {rp[2]:7.3f})  "
            f"Δ=({r_rel[0]:7.3f}, {r_rel[1]:7.3f}, {r_rel[2]:7.3f})  grip={'●' if rg else '○'}  trig={rt:.2f}",
            flush=True,
        )
