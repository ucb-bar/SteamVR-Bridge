"""
Modified from the example code at https://github.com/cmbruns/pyopenxr_examples/blob/main/xr_examples/headless.py
"""

import ctypes
import platform
import xr

from ._openxr_utils import check_raw_result
from .config import DEFAULT_BRIDGE_CONFIG, resolve_bridge_config
from .vive_controller import ViveController
from .vive_tracker import ViveTracker

if platform.system() == "Windows":
    import ctypes.wintypes
    from .windows_performance_counter import WindowsPerformanceCounter as PerformanceCounter
else:
    from .linux_performance_counter import LinuxPerformanceCounter as PerformanceCounter

from .frame_transform import _vr_to_robotics_position, _vr_to_robotics_orientation, _quat_multiply


class SteamVrBridge:
    """
    This class creates a headless OpenXR extension that communicates with SteamVR and retrieves
    the state of the headset and controllers.

    Frame convention used by this bridge:
    - OpenXR/SteamVR tracking is converted into a robotics frame once per update.
    - Public poses (`hmd`, tracked-device `location`, tracked-device `orientation`, and relative deltas)
      are all expressed in the robotics frame.
    """
    DEFAULT_CONFIG = DEFAULT_BRIDGE_CONFIG

    def __init__(self, config=None, tracker_roles=None):
        self.config = resolve_bridge_config(config=config, tracker_roles=tracker_roles)
        self.instance = None
        self.session = None
        self.performance_counter = None
        self.action_set = None
        self.reference_space = None
        self.view_reference_space = None
        self.left_controller = None
        self.right_controller = None
        self.controllers = []
        self.trackers = []
        self.tracked_devices = []
        self.tracker_1 = None
        self.tracker_2 = None
        self._vive_tracker_supported = False

        try:
            # enumerate the required instance extensions
            extensions = [xr.MND_HEADLESS_EXTENSION_NAME]  # Permits use without a graphics display
            available_extensions = {
                prop.extension_name.decode().rstrip("\x00")
                for prop in xr.enumerate_instance_extension_properties()
            }
            self._vive_tracker_supported = (
                xr.HTCX_VIVE_TRACKER_INTERACTION_EXTENSION_NAME in available_extensions
            )

            # tracking controllers in headless mode requires a way to get the current XrTime
            if platform.system() == "Windows":
                extensions.append(xr.KHR_WIN32_CONVERT_PERFORMANCE_COUNTER_TIME_EXTENSION_NAME)
            else:  # Linux
                extensions.append(xr.KHR_CONVERT_TIMESPEC_TIME_EXTENSION_NAME)
            if self._vive_tracker_supported:
                extensions.append(xr.HTCX_VIVE_TRACKER_INTERACTION_EXTENSION_NAME)

            # create instance for headless use
            self.instance = xr.create_instance(xr.InstanceCreateInfo(
                enabled_extension_names=extensions,
            ))

            system_id = xr.get_system(
                self.instance,
                xr.SystemGetInfo(form_factor=xr.FormFactor.HEAD_MOUNTED_DISPLAY),
            )
            self.session = xr.create_session(
                self.instance,
                xr.SessionCreateInfo(
                    system_id=system_id,
                    next=None,  # no GraphicsBinding structure is required here in HEADLESS mode
                )
            )

            # create the performance counter used to get accurate system time
            self.performance_counter = PerformanceCounter(self.instance)

            # set up controller tracking, as one possible legitimate headless activity
            self.action_set = xr.create_action_set(
                instance=self.instance,
                create_info=xr.ActionSetCreateInfo(
                    action_set_name="action_set",
                    localized_action_set_name="Action Set",
                    priority=0,
                ),
            )

            self.controllers = self._create_controllers()
            self.left_controller = self._find_controller("left")
            self.right_controller = self._find_controller("right")
            self.trackers = self._create_trackers(self.config.tracker_roles)
            self.tracked_devices = [*self.controllers, *self.trackers]
            self.devices_by_key = {
                device.state_key: device
                for device in self.tracked_devices
            }
            self.tracker_1 = self.trackers[0] if len(self.trackers) > 0 else None
            self.tracker_2 = self.trackers[1] if len(self.trackers) > 1 else None

            # create bindings and action sets for tracked devices, so that we can receive events from them
            bindings_by_profile = {}
            for device in self.tracked_devices:
                bindings = device.register(self.action_set, self.session)
                bindings_by_profile.setdefault(device.interaction_profile_path, []).extend(bindings)

            for interaction_profile, suggested_bindings in bindings_by_profile.items():
                profile_bindings = (xr.ActionSuggestedBinding * len(suggested_bindings))(
                    *suggested_bindings
                )
                xr.suggest_interaction_profile_bindings(
                    instance=self.instance,
                    suggested_bindings=xr.InteractionProfileSuggestedBinding(
                        interaction_profile=xr.string_to_path(
                            self.instance,
                            interaction_profile,
                        ),
                        count_suggested_bindings=len(profile_bindings),
                        suggested_bindings=profile_bindings,
                    ),
                )
            xr.attach_session_action_sets(
                session=self.session,
                attach_info=xr.SessionActionSetsAttachInfo(
                    action_sets=[self.action_set],
                ),
            )

            # create the reference coordinate spaces
            self.reference_space = xr.create_reference_space(
                session=self.session,
                create_info=xr.ReferenceSpaceCreateInfo(
                    reference_space_type=xr.ReferenceSpaceType.STAGE,
                ),
            )
            self.view_reference_space = xr.create_reference_space(
                session=self.session,
                create_info=xr.ReferenceSpaceCreateInfo(
                    reference_space_type=xr.ReferenceSpaceType.VIEW,
                ),
            )

            # initialize the session state
            self.session_state = xr.SessionState.UNKNOWN

            # internal state of the HMD
            self._hmd_position = xr.Vector3f()
            self._hmd_orientation = xr.Quaternionf()

            # Relative-transform tracking state (one entry per tracked device).
            # All values below are in the robotics frame.
            self._grip_last = [False] * len(self.tracked_devices)
            self._trigger_full_last = [False] * len(self.tracked_devices)
            self._tracking_active = [False] * len(self.tracked_devices)
            self._anchor_position = [xr.Vector3f() for _ in self.tracked_devices]
            self._anchor_orientation = [xr.Quaternionf() for _ in self.tracked_devices]
        except Exception:
            self.exit()
            raise

    def _enumerate_vive_tracker_paths(self):
        if not self._vive_tracker_supported:
            return []

        try:
            enumerate_paths = ctypes.cast(
                xr.get_instance_proc_addr(self.instance, "xrEnumerateViveTrackerPathsHTCX"),
                xr.PFN_xrEnumerateViveTrackerPathsHTCX,
            )
        except Exception:
            return []

        path_count = ctypes.c_uint32(0)
        result = check_raw_result(enumerate_paths(
            self.instance,
            0,
            ctypes.byref(path_count),
            None,
        ))
        if result.is_exception():
            return []
        if path_count.value == 0:
            return []

        paths = (xr.ViveTrackerPathsHTCX * path_count.value)(
            *(xr.ViveTrackerPathsHTCX(
                type=xr.StructureType.VIVE_TRACKER_PATHS_HTCX,
                next=None,
            ) for _ in range(path_count.value))
        )
        result = check_raw_result(enumerate_paths(
            self.instance,
            path_count.value,
            ctypes.byref(path_count),
            paths,
        ))
        if result.is_exception():
            return []

        return list(paths[:path_count.value])

    def _discover_tracker_roles(self):
        roles = []
        for tracker_paths in self._enumerate_vive_tracker_paths():
            role_path = tracker_paths.role_path
            if role_path == xr.NULL_PATH:
                continue
            try:
                role_path_string = xr.path_to_string(self.instance, role_path)
            except Exception:
                continue
            prefix = "/user/vive_tracker_htcx/role/"
            if not role_path_string.startswith(prefix):
                continue
            role = role_path_string.removeprefix(prefix)
            if role and role not in roles:
                roles.append(role)
        return roles

    def _create_controllers(self):
        controllers = []
        for controller_config in self.config.controllers:
            controllers.append(
                ViveController(
                    self.instance,
                    controller_config.name,
                    controller_config.user_path,
                    state_key=controller_config.key,
                )
            )
        return controllers

    def _find_controller(self, key):
        for controller in self.controllers:
            if controller.state_key == key:
                return controller
        return None

    def _create_trackers(self, tracker_roles):
        if not self._vive_tracker_supported:
            return []

        roles = list(tracker_roles) if tracker_roles is not None else self._discover_tracker_roles()

        trackers = []
        for role in roles:
            tracker_label = f"Tracker ({role.replace('_', ' ')})"
            trackers.append(
                ViveTracker(
                    self.instance,
                    tracker_label.title(),
                    role,
                    state_key=role,
                )
            )
        return trackers

    def update(self):
        while True:
            # poll session state changed events
            try:
                event_buffer = xr.poll_event(self.instance)
                event_type = xr.StructureType(event_buffer.type)
                if event_type == xr.StructureType.EVENT_DATA_SESSION_STATE_CHANGED:
                    event = ctypes.cast(
                        ctypes.byref(event_buffer),
                        ctypes.POINTER(xr.EventDataSessionStateChanged)).contents
                    self.session_state = xr.SessionState(event.state)

                    print(f"OpenXR session state changed to xr.SessionState.{self.session_state.name}")

                    if self.session_state == xr.SessionState.READY:
                        xr.begin_session(
                            self.session,
                            xr.SessionBeginInfo(
                                # TODO: zero should be allowed here...
                                primary_view_configuration_type=xr.ViewConfigurationType.PRIMARY_MONO,
                            ),
                        )
                    elif self.session_state == xr.SessionState.STOPPING:
                        xr.destroy_session(self.session)
                        self.session = None
                        self.reference_space = None
                        self.view_reference_space = None
                        for device in self.tracked_devices:
                            if hasattr(device, "reference_space"):
                                device.reference_space = None
                            if hasattr(device, "action_space"):
                                device.action_space = None
            except xr.EventUnavailable:
                break  # there is no event in the queue at this moment

        if self.session is None:
            return

        # Skip wait_frame: it can block indefinitely when the SteamVR compositor
        # isn't advancing (e.g. vrmonitor/libQt5 issues). Headless polling works
        # without it; we use the performance counter for xrTime instead.
        # xr.wait_frame(session=self.session)

        xr_time_now = self.performance_counter.get()

        # sync actions
        active_action_set = xr.ActiveActionSet(
            action_set=self.action_set,
            subaction_path=xr.NULL_PATH,
        )
        xr.sync_actions(
            session=self.session,
            sync_info=xr.ActionsSyncInfo(
                active_action_sets=[active_action_set],
            ),
        )

        # get the location of the headset
        hmd_state = xr.locate_space(
            space=self.view_reference_space,
            base_space=self.reference_space,
            time=xr_time_now,
        )
        if hmd_state.location_flags & xr.SPACE_LOCATION_POSITION_VALID_BIT:
            steamvr_position = hmd_state.pose.position
            steamvr_orientation = hmd_state.pose.orientation
            self._hmd_position = _vr_to_robotics_position(steamvr_position)
            self._hmd_orientation = _vr_to_robotics_orientation(steamvr_orientation)

        # Update tracked-device states and relative transforms.
        # device.location/orientation are already converted to the robotics frame in update().
        for i, device in enumerate(self.tracked_devices):
            device.update(self.session, xr_time_now)

            if (
                device.tracking_starts_active
                and not self._tracking_active[i]
                and device.pose_valid
            ):
                device._delta_location = xr.Vector3f()
                device._delta_orientation = xr.Quaternionf()
                device._delta_orientation.w = 1.0
                self._tracking_active[i] = True

                ap = xr.Vector3f()
                ap.x = device.location.x
                ap.y = device.location.y
                ap.z = device.location.z
                self._anchor_position[i] = ap

                aq = xr.Quaternionf()
                aq.w = device.orientation.w
                aq.x = device.orientation.x
                aq.y = device.orientation.y
                aq.z = device.orientation.z
                self._anchor_orientation[i] = aq

            grip = device.grip_button_pressed
            trigger_full = device.trigger >= 1.0

            # Grip rising edge: toggle between streaming and frozen tracking
            if grip and not self._grip_last[i]:
                self._tracking_active[i] = not self._tracking_active[i]
                if self._tracking_active[i]:
                    # Place anchor so the existing accumulated delta is preserved
                    prev_rp = device.relative_location
                    ap = xr.Vector3f()
                    ap.x = device.location.x - prev_rp.x
                    ap.y = device.location.y - prev_rp.y
                    ap.z = device.location.z - prev_rp.z
                    self._anchor_position[i] = ap

                    # Preserve the existing relative rotation when toggling tracking on:
                    # q_delta = q_current * q_anchor^{-1}
                    # => q_anchor = q_delta^{-1} * q_current
                    prev_rq = device.relative_orientation
                    aw, ax, ay, az = _quat_multiply(
                        (prev_rq.w, -prev_rq.x, -prev_rq.y, -prev_rq.z),
                        (device.orientation.w, device.orientation.x,
                         device.orientation.y, device.orientation.z),
                    )
                    aq = xr.Quaternionf()
                    aq.w = aw
                    aq.x = ax
                    aq.y = ay
                    aq.z = az
                    self._anchor_orientation[i] = aq

            # Grip held + trigger reaches 1.0: clear delta and force tracking on
            if grip and trigger_full and not self._trigger_full_last[i]:
                device._delta_location = xr.Vector3f()
                device._delta_orientation = xr.Quaternionf()
                device._delta_orientation.w = 1.0
                self._tracking_active[i] = True
                ap = xr.Vector3f()
                ap.x = device.location.x
                ap.y = device.location.y
                ap.z = device.location.z
                self._anchor_position[i] = ap
                aq = xr.Quaternionf()
                aq.w = device.orientation.w
                aq.x = device.orientation.x
                aq.y = device.orientation.y
                aq.z = device.orientation.z
                self._anchor_orientation[i] = aq

            # Continuously compute delta while tracking is active
            if self._tracking_active[i] and device.pose_valid:
                ap = self._anchor_position[i]
                rp = xr.Vector3f()
                rp.x = device.location.x - ap.x
                rp.y = device.location.y - ap.y
                rp.z = device.location.z - ap.z
                device._delta_location = rp

                # Relative rotation from the anchor frame to the current frame.
                # Quaternion convention is Hamilton product in (w, x, y, z).
                aq = self._anchor_orientation[i]
                w, x, y, z = _quat_multiply(
                    (device.orientation.w, device.orientation.x,
                     device.orientation.y, device.orientation.z),
                    (aq.w, -aq.x, -aq.y, -aq.z),
                )
                rq = xr.Quaternionf()
                rq.w = w
                rq.x = x
                rq.y = y
                rq.z = z
                device._delta_orientation = rq

            self._grip_last[i] = grip
            self._trigger_full_last[i] = trigger_full

    def exit(self):
        # clean up in reverse creation order, allowing partial initialization.
        if self.session is not None:
            for device in self.tracked_devices:
                action_space = getattr(device, "action_space", None)
                if action_space is not None:
                    xr.destroy_space(action_space)
                    device.action_space = None

                reference_space = getattr(device, "reference_space", None)
                if reference_space is not None:
                    xr.destroy_space(reference_space)
                    device.reference_space = None

            if self.view_reference_space is not None:
                xr.destroy_space(self.view_reference_space)
                self.view_reference_space = None

            if self.reference_space is not None:
                xr.destroy_space(self.reference_space)
                self.reference_space = None

            xr.destroy_session(self.session)
            self.session = None

        if self.action_set is not None:
            xr.destroy_action_set(self.action_set)
            self.action_set = None

        if self.instance is not None:
            xr.destroy_instance(self.instance)
            self.instance = None
