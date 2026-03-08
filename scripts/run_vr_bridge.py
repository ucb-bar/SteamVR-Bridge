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
            "location": [0, 0, 0],  # (x, y, z) in meters
            "orientation": [1, 0, 0, 0],  # (qw, qx, qy, qz) in quaternion
            "relative_location": [0, 0, 0],
            "relative_orientation": [1, 0, 0, 0],
            "grip_button_pressed": False,
            "trigger": 0,  # 0.0 to 1.0
        },
        "right": {
            "location": [0, 0, 0],
            "orientation": [1, 0, 0, 0],
            "relative_location": [0, 0, 0],
            "relative_orientation": [1, 0, 0, 0],
            "grip_button_pressed": False,
            "trigger": 0,
        }
    }

    start_time = time.time()
    prev_time = time.time()

    try:
        while True:
            bridge.update()

            # update states
            controller_states["left"]["location"] = bridge.left_controller.location.as_numpy().tolist()
            controller_states["left"]["orientation"] = [
                bridge.left_controller.orientation.w,
                bridge.left_controller.orientation.x,
                bridge.left_controller.orientation.y,
                bridge.left_controller.orientation.z,
            ]
            controller_states["right"]["location"] = bridge.right_controller.location.as_numpy().tolist()
            controller_states["right"]["orientation"] = [
                bridge.right_controller.orientation.w,
                bridge.right_controller.orientation.x,
                bridge.right_controller.orientation.y,
                bridge.right_controller.orientation.z,
            ]
            controller_states["left"]["relative_location"] = bridge.left_controller.relative_location.as_numpy().tolist()
            controller_states["left"]["relative_orientation"] = [
                bridge.left_controller.relative_orientation.w,
                bridge.left_controller.relative_orientation.x,
                bridge.left_controller.relative_orientation.y,
                bridge.left_controller.relative_orientation.z,
            ]
            controller_states["right"]["relative_location"] = bridge.right_controller.relative_location.as_numpy().tolist()
            controller_states["right"]["relative_orientation"] = [
                bridge.right_controller.relative_orientation.w,
                bridge.right_controller.relative_orientation.x,
                bridge.right_controller.relative_orientation.y,
                bridge.right_controller.relative_orientation.z,
            ]
            controller_states["left"]["button_pressed"] = bridge.left_controller.grip_button_pressed
            controller_states["right"]["button_pressed"] = bridge.right_controller.grip_button_pressed
            controller_states["left"]["trigger"] = bridge.left_controller.trigger
            controller_states["right"]["trigger"] = bridge.right_controller.trigger

            loc_l = bridge.left_controller.location
            loc_r = bridge.right_controller.location
            trig_l = controller_states["left"]["trigger"]
            trig_r = controller_states["right"]["trigger"]
            grip_l = controller_states["left"]["button_pressed"]
            grip_r = controller_states["right"]["button_pressed"]
            rel_loc_l = bridge.left_controller.relative_location
            rel_loc_r = bridge.right_controller.relative_location
            ori_l = bridge.left_controller.orientation
            ori_r = bridge.right_controller.orientation
            rpy_l = np.rad2deg(
                Rotation.from_quat([ori_l.x, ori_l.y, ori_l.z, ori_l.w]).as_euler("xyz")
            )
            rpy_r = np.rad2deg(
                Rotation.from_quat([ori_r.x, ori_r.y, ori_r.z, ori_r.w]).as_euler("xyz")
            )
            current_time = time.time()
            if current_time - prev_time > (1 / 30.):
                prev_time = current_time
                t = current_time - start_time

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

            udp.send_dict(controller_states)

    except KeyboardInterrupt:
        print("Keyboard interrupt detected. Exiting...")

    finally:
        bridge.exit()
        # udp.close()
