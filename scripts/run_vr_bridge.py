import time

from scipy.spatial.transform import Rotation
import numpy as np
from udpack import UDP
from steamvr_bridge import SteamVrBridge


if __name__ == "__main__":
    bridge = SteamVrBridge()

    udp = UDP(recv_addr=None, send_addr=("0.0.0.0", 11005))

    controller_states = {
        "left": {
            "pose": [],
            "button_pressed": False,
            "trigger": 0,
            "relative_pose": [0, 0, 0, 1, 0, 0, 0],
        },
        "right": {
            "pose": [],
            "button_pressed": False,
            "trigger": 0,
            "relative_pose": [0, 0, 0, 1, 0, 0, 0],
        }
    }

    while True:
        bridge.update()

        # Create rotation matrix
        left_rot_matrix = np.eye(4)
        left_rot_matrix[:3, :3] = Rotation.from_quat(np.array([
            bridge.left_controller.orientation.w,
            bridge.left_controller.orientation.x,
            bridge.left_controller.orientation.y,
            bridge.left_controller.orientation.z,
        ])).as_matrix()
        left_rot_matrix[:3, 3] = bridge.left_controller.position.as_numpy()
        right_rot_matrix = np.eye(4)
        right_rot_matrix[:3, :3] = Rotation.from_quat(np.array([
            bridge.right_controller.orientation.w,
            bridge.right_controller.orientation.x,
            bridge.right_controller.orientation.y,
            bridge.right_controller.orientation.z,
        ])).as_matrix()
        right_rot_matrix[:3, 3] = bridge.right_controller.position.as_numpy()

        controller_states["left"]["pose"] = left_rot_matrix.tolist()
        controller_states["right"]["pose"] = right_rot_matrix.tolist()
        controller_states["left"]["button_pressed"] = bridge.left_controller.grip_button
        controller_states["right"]["button_pressed"] = bridge.right_controller.grip_button
        controller_states["left"]["trigger"] = bridge.left_controller.trigger
        controller_states["right"]["trigger"] = bridge.right_controller.trigger
        controller_states["left"]["relative_pose"] = bridge.left_controller.relative_pose.tolist()
        controller_states["right"]["relative_pose"] = bridge.right_controller.relative_pose.tolist()

        lp = bridge.left_controller.position
        rp = bridge.right_controller.position
        lt = controller_states["left"]["trigger"]
        rt = controller_states["right"]["trigger"]
        lg = controller_states["left"]["button_pressed"]
        rg = controller_states["right"]["button_pressed"]
        ldp = bridge.left_controller.relative_position
        rdp = bridge.right_controller.relative_position
        lo = bridge.left_controller.orientation
        ro = bridge.right_controller.orientation
        lrpy = np.rad2deg(
            Rotation.from_quat([lo.x, lo.y, lo.z, lo.w]).as_euler("xyz")
        )
        rrpy = np.rad2deg(
            Rotation.from_quat([ro.x, ro.y, ro.z, ro.w]).as_euler("xyz")
        )

        print(
            f"[{time.time():.1f}]  "
            f"L: pos=({lp.x:5.2f}, {lp.y:5.2f}, {lp.z:5.2f})  "
            f"rpy=({lrpy[0]:5.0f}, {lrpy[1]:5.0f}, {lrpy[2]:5.0f})°  "
            f"Δ=({ldp.x:5.2f}, {ldp.y:5.2f}, {ldp.z:5.2f})  grip={'●' if lg else '○'}  trig={lt:.2f} ({'●' if lt == 1.0 else '○'}) |  "
            f"R: pos=({rp.x:5.2f}, {rp.y:5.2f}, {rp.z:5.2f})  "
            f"rpy=({rrpy[0]:5.0f}, {rrpy[1]:5.0f}, {rrpy[2]:5.0f})°  "
            f"Δ=({rdp.x:5.2f}, {rdp.y:5.2f}, {rdp.z:5.2f})  grip={'●' if rg else '○'}  trig={rt:.2f} ({'●' if rt == 1.0 else '○'})",
            flush=True,
        )

        udp.send_dict(controller_states)
