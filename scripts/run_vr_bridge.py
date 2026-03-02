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
            "trigger": 0
        },
        "right": {
            "pose": [],
            "button_pressed": False,
            "trigger": 0
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
        left_rot_matrix[:, 0:3] = bridge.left_controller.position.as_numpy()
        right_rot_matrix = np.eye(4)
        right_rot_matrix[:3, :3] = Rotation.from_quat(np.array([
            bridge.right_controller.orientation.w,
            bridge.right_controller.orientation.x,
            bridge.right_controller.orientation.y,
            bridge.right_controller.orientation.z,
        ])).as_matrix()
        right_rot_matrix[:, 0:3] = bridge.right_controller.position.as_numpy()

        controller_states["left"]["pose"] = left_rot_matrix.tolist()
        controller_states["right"]["pose"] = right_rot_matrix.tolist()
        controller_states["left"]["button_pressed"] = bridge.left_controller.grip_button
        controller_states["right"]["button_pressed"] = bridge.right_controller.grip_button
        controller_states["left"]["trigger"] = bridge.left_controller.trigger
        controller_states["right"]["trigger"] = bridge.right_controller.trigger

        lp = bridge.left_controller.position
        rp = bridge.right_controller.position
        lt = controller_states["left"]["trigger"]
        rt = controller_states["right"]["trigger"]
        lg = controller_states["left"]["button_pressed"]
        rg = controller_states["right"]["button_pressed"]

        print(
            f"[{time.time():.1f}]  "
            f"L: pos=({lp.x:7.3f}, {lp.y:7.3f}, {lp.z:7.3f})  grip={'●' if lg else '○'}  trig={lt:.2f}  |  "
            f"R: pos=({rp.x:7.3f}, {rp.y:7.3f}, {rp.z:7.3f})  grip={'●' if rg else '○'}  trig={rt:.2f}",
            flush=True,
        )

        udp.send_dict(controller_states)
