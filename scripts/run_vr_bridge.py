import time

import openvr
import numpy as np
from scipy.spatial.transform import Rotation
from cc.udp import UDP


class SteamVrBridge:
    def __init__(self):
        self.vr_system = openvr.init(openvr.VRApplication_Scene)
        self.left_controller_index = self.vr_system.getTrackedDeviceIndexForControllerRole(openvr.TrackedControllerRole_LeftHand)
        self.right_controller_index = self.vr_system.getTrackedDeviceIndexForControllerRole(openvr.TrackedControllerRole_RightHand)

        print(f"Initialized controllers: {self.left_controller_index} and {self.right_controller_index}")

        self.controller_states = {
            "left": {
                "pose": np.eye(4),
                "button_pressed": False,
                "trigger": 0
            },
            "right": {
                "pose": np.eye(4),
                "button_pressed": False,
                "trigger": 0
            }
        }

    def get_controller_pose(self, controller_index: int) -> np.ndarray:
        _, _, tracked_device_pose = self.vr_system.getControllerStateWithPose(openvr.TrackingUniverseStanding, controller_index)
        device_pose = np.array(tracked_device_pose.mDeviceToAbsoluteTracking._getArray(), dtype=np.float32)
        return np.concatenate((device_pose, [[0, 0, 0, 1]]), axis=0)

    def get_controller_state(self, controller_index: int) -> tuple[bool, float]:
        _, controller_state, _ = self.vr_system.getControllerStateWithPose(openvr.TrackingUniverseStanding, controller_index)
        button_pressed = bool(controller_state.ulButtonPressed & 4)
        trigger = controller_state.rAxis[openvr.k_eControllerAxis_TrackPad].x  # I am not sure why, but this is the trigger value
        return button_pressed, trigger

    def update(self):
        left_controller_pose = self.get_controller_pose(self.left_controller_index)
        right_controller_pose = self.get_controller_pose(self.right_controller_index)

        # Create rotation matrix
        rot = Rotation.from_rotvec([np.pi/2, 0, 0])
        rot_matrix = np.eye(4)
        rot_matrix[:3, :3] = rot.as_matrix()

        # rotate by 90 degrees around the x axis
        self.controller_states["left"]["pose"] = (rot_matrix @ left_controller_pose).tolist()
        self.controller_states["right"]["pose"] = (rot_matrix @ right_controller_pose).tolist()

        left_controller_button_pressed, left_controller_trigger = self.get_controller_state(self.left_controller_index)
        right_controller_button_pressed, right_controller_trigger = self.get_controller_state(self.right_controller_index)

        self.controller_states["left"]["button_pressed"] = left_controller_button_pressed
        self.controller_states["right"]["button_pressed"] = right_controller_button_pressed
        self.controller_states["left"]["trigger"] = left_controller_trigger
        self.controller_states["right"]["trigger"] = right_controller_trigger

        return self.controller_states

    def __del__(self):
        openvr.shutdown()


if __name__ == "__main__":
    bridge = SteamVrBridge()

    udp = UDP(recv_addr=("0.0.0.0", 11005), send_addr=("172.28.0.5", 11005))

    while True:
        bridge.update()

        print(f"{time.time():.2f}", bridge.controller_states["left"]["button_pressed"], bridge.controller_states["left"]["trigger"], bridge.controller_states["right"]["button_pressed"], bridge.controller_states["right"]["trigger"])

        udp.send_dict(bridge.controller_states)
