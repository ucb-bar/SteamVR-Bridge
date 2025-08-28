import time

from scipy.spatial.transform import Rotation
import numpy as np
from cc.udp import UDP
from steamvr_bridge import SteamVrBridge


if __name__ == "__main__":
    bridge = SteamVrBridge()

    udp = UDP(recv_addr=("0.0.0.0", 11005), send_addr=("172.28.0.5", 11005))

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

        print(f"{time.time():.2f}", controller_states["left"]["button_pressed"], controller_states["left"]["trigger"], controller_states["right"]["button_pressed"], controller_states["right"]["trigger"])

        udp.send_dict(controller_states)
