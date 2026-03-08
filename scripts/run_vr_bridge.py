import time
import pickle

from scipy.spatial.transform import Rotation
import numpy as np
from udpack import UDP
from steamvr_bridge import SteamVrBridge


if __name__ == "__main__":
    bridge = SteamVrBridge()

    udp = UDP(recv_addr=None, send_addr=("0.0.0.0", 11005))

    states = {
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
            states["left"]["location"][:] = bridge.left_controller.location.as_numpy()
            states["left"]["orientation"][:] = bridge.left_controller.orientation.as_numpy()
            states["right"]["location"][:] = bridge.right_controller.location.as_numpy()
            states["right"]["orientation"][:] = bridge.right_controller.orientation.as_numpy()
            states["left"]["relative_location"][:] = bridge.left_controller.relative_location.as_numpy()
            states["left"]["relative_orientation"][:] = bridge.left_controller.relative_orientation.as_numpy()
            states["right"]["relative_location"][:] = bridge.right_controller.relative_location.as_numpy()
            states["right"]["relative_orientation"][:] = bridge.right_controller.relative_orientation.as_numpy()
            states["left"]["grip_button_pressed"] = bridge.left_controller.grip_button_pressed
            states["right"]["grip_button_pressed"] = bridge.right_controller.grip_button_pressed
            states["left"]["trigger"] = bridge.left_controller.trigger
            states["right"]["trigger"] = bridge.right_controller.trigger

            current_time = time.time()
            if current_time - prev_time > (1 / 30.):
                prev_time = current_time
                t = current_time - start_time

                loc_l = states["left"]["location"]
                loc_r = states["right"]["location"]
                trig_l = states["left"]["trigger"]
                trig_r = states["right"]["trigger"]
                grip_l = states["left"]["grip_button_pressed"]
                grip_r = states["right"]["grip_button_pressed"]
                rel_loc_l = states["left"]["relative_location"]
                rel_loc_r = states["right"]["relative_location"]
                ori_l = states["left"]["orientation"]
                ori_r = states["right"]["orientation"]
                rpy_l = np.rad2deg(
                    Rotation.from_quat(ori_l, scalar_first=True).as_euler("xyz")
                )
                rpy_r = np.rad2deg(
                    Rotation.from_quat(ori_r, scalar_first=True).as_euler("xyz")
                )
                print(
                    f"[{t:.3f}] "
                    f"L: pos=({loc_l[0]:5.2f}, {loc_l[1]:5.2f}, {loc_l[2]:5.2f}) "
                    f"rpy=({rpy_l[0]:4.0f}, {rpy_l[1]:4.0f}, {rpy_l[2]:4.0f})° "
                    f"Δ=({rel_loc_l[0]:5.2f}, {rel_loc_l[1]:5.2f}, {rel_loc_l[2]:5.2f}) grip={'●' if grip_l else '○'} trig={trig_l:.2f} ({'●' if trig_l == 1.0 else '○'}) | "
                    f"R: pos=({loc_r[0]:5.2f}, {loc_r[1]:5.2f}, {loc_r[2]:5.2f}) "
                    f"rpy=({rpy_r[0]:4.0f}, {rpy_r[1]:4.0f}, {rpy_r[2]:4.0f})° "
                    f"Δ=({rel_loc_r[0]:5.2f}, {rel_loc_r[1]:5.2f}, {rel_loc_r[2]:5.2f}) grip={'●' if grip_r else '○'} trig={trig_r:.2f} ({'●' if trig_r == 1.0 else '○'})",
                    flush=True,
                )

            # udp.send_dict(states)
            udp.send(pickle.dumps(states))

    except KeyboardInterrupt:
        print("Keyboard interrupt detected. Exiting...")

    finally:
        bridge.exit()
        # udp.close()
