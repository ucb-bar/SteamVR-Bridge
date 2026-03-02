"""
Low-level OpenXR API: prints controller positions for 30 frames.

Uses headless extension (no display required). Skips xr.wait_frame to avoid
blocking when SteamVR compositor isn't advancing (e.g. vrmonitor/libQt5 issues).

Modified from https://github.com/cmbruns/pyopenxr_examples/blob/main/xr_examples/track_controller.py
"""

import ctypes
import platform
import time

import xr


def _create_performance_counter(instance):
    """Get xr.Time from system clock. Required for headless controller tracking."""
    if platform.system() == "Windows":
        import ctypes.wintypes as wintypes

        pc_time = wintypes.LARGE_INTEGER()
        kernel32 = ctypes.WinDLL("kernel32")
        fn = ctypes.cast(
            xr.get_instance_proc_addr(instance, "xrConvertWin32PerformanceCounterToTimeKHR"),
            xr.PFN_xrConvertWin32PerformanceCounterToTimeKHR,
        )

        def get():
            kernel32.QueryPerformanceCounter(ctypes.byref(pc_time))
            result = xr.Time()
            fn(instance, ctypes.pointer(pc_time), ctypes.byref(result))
            return result

    else:
        ts = xr.timespec()
        fn = ctypes.cast(
            xr.get_instance_proc_addr(instance, "xrConvertTimespecTimeToTimeKHR"),
            xr.PFN_xrConvertTimespecTimeToTimeKHR,
        )

        def get():
            t = time.clock_gettime(time.CLOCK_MONOTONIC)
            ts.tv_sec = int(t)
            ts.tv_nsec = int((t % 1) * 1e9)
            result = xr.Time()
            fn(instance, ctypes.pointer(ts), ctypes.byref(result))
            return result

    return get


print("Connecting to SteamVR (headless OpenXR)...", flush=True)

extensions = [xr.MND_HEADLESS_EXTENSION_NAME]
if platform.system() == "Windows":
    extensions.append(xr.KHR_WIN32_CONVERT_PERFORMANCE_COUNTER_TIME_EXTENSION_NAME)
else:
    extensions.append(xr.KHR_CONVERT_TIMESPEC_TIME_EXTENSION_NAME)

instance = xr.create_instance(xr.InstanceCreateInfo(enabled_extension_names=extensions))
system_id = xr.get_system(instance, xr.SystemGetInfo(form_factor=xr.FormFactor.HEAD_MOUNTED_DISPLAY))
session = xr.create_session(instance, xr.SessionCreateInfo(system_id=system_id, next=None))

get_xr_time = _create_performance_counter(instance)

action_set = xr.create_action_set(
    instance=instance,
    create_info=xr.ActionSetCreateInfo(
        action_set_name="track_controllers",
        localized_action_set_name="Track Controllers",
        priority=0,
    ),
)

controller_paths = (
    xr.string_to_path(instance, "/user/hand/left"),
    xr.string_to_path(instance, "/user/hand/right"),
)

pose_action = xr.create_action(
    action_set=action_set,
    create_info=xr.ActionCreateInfo(
        action_type=xr.ActionType.POSE_INPUT,
        action_name="hand_pose",
        localized_action_name="Hand Pose",
        count_subaction_paths=2,
        subaction_paths=(xr.Path * 2)(controller_paths[0], controller_paths[1]),
    ),
)

bindings = (
    xr.ActionSuggestedBinding(
        action=pose_action,
        binding=xr.string_to_path(instance, "/user/hand/left/input/grip/pose"),
    ),
    xr.ActionSuggestedBinding(
        action=pose_action,
        binding=xr.string_to_path(instance, "/user/hand/right/input/grip/pose"),
    ),
)
xr.suggest_interaction_profile_bindings(
    instance=instance,
    suggested_bindings=xr.InteractionProfileSuggestedBinding(
        interaction_profile=xr.string_to_path(instance, "/interaction_profiles/htc/vive_controller"),
        count_suggested_bindings=2,
        suggested_bindings=bindings,
    ),
)
xr.attach_session_action_sets(
    session=session,
    attach_info=xr.SessionActionSetsAttachInfo(action_sets=[action_set]),
)

reference_space = xr.create_reference_space(
    session=session,
    create_info=xr.ReferenceSpaceCreateInfo(reference_space_type=xr.ReferenceSpaceType.STAGE),
)

action_spaces = (
    xr.create_action_space(
        session=session,
        create_info=xr.ActionSpaceCreateInfo(action=pose_action, subaction_path=controller_paths[0]),
    ),
    xr.create_action_space(
        session=session,
        create_info=xr.ActionSpaceCreateInfo(action=pose_action, subaction_path=controller_paths[1]),
    ),
)

session_state = xr.SessionState.UNKNOWN
session_began = False

try:
    for frame in range(1000):
        while True:
            try:
                buf = xr.poll_event(instance)
                if xr.StructureType(buf.type) == xr.StructureType.EVENT_DATA_SESSION_STATE_CHANGED:
                    ev = ctypes.cast(ctypes.byref(buf), ctypes.POINTER(xr.EventDataSessionStateChanged)).contents
                    session_state = xr.SessionState(ev.state)
                    if session_state == xr.SessionState.READY:
                        xr.begin_session(
                            session,
                            xr.SessionBeginInfo(primary_view_configuration_type=xr.ViewConfigurationType.PRIMARY_MONO),
                        )
                        session_began = True
                    elif session_state == xr.SessionState.STOPPING:
                        session = None
                        break
            except xr.EventUnavailable:
                break

        if session is None:
            break

        if session_began:
            # Skip wait_frame: blocks indefinitely when SteamVR compositor
            # isn't advancing (vrmonitor/libQt5 issues).
            xr_time = get_xr_time()

            active = xr.ActiveActionSet(action_set=action_set, subaction_path=xr.NULL_PATH)
            xr.sync_actions(session=session, sync_info=xr.ActionsSyncInfo(active_action_sets=[active]))

            found = 0
            for i, space in enumerate(action_spaces):
                loc = xr.locate_space(space=space, base_space=reference_space, time=xr_time)
                if loc.location_flags & xr.SPACE_LOCATION_POSITION_VALID_BIT:
                    hand = "left" if i == 0 else "right"
                    p = loc.pose.position
                    print(f"  {hand}: ({p.x:.3f}, {p.y:.3f}, {p.z:.3f})", flush=True)
                    found += 1

            if found == 0:
                print("  no controllers active", flush=True)

            if frame >= 30:
                break

        time.sleep(0.05)

    if not session_began:
        print("Session never reached READY. Is SteamVR running?", flush=True)
        exit(1)

finally:
    xr.destroy_action_set(action_set)
    xr.destroy_instance(instance)

