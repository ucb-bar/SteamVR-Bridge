"""
Modified from the example code at https://github.com/cmbruns/pyopenxr_examples/blob/main/xr_examples/headless.py
"""

import platform
import xr

from .vive_controller import ViveController

if platform.system() == "Windows":
    import ctypes.wintypes
    from .windows_performance_counter import WindowsPerformanceCounter as PerformanceCounter
else:
    import ctypes
    from .linux_performance_counter import LinuxPerformanceCounter as PerformanceCounter

from .frame_transform import _vr_to_robotics_position, _vr_to_robotics_orientation, _quat_multiply


class SteamVrBridge:
    """
    This class creates a headless OpenXR extension that communicates with SteamVR and retrieves
    the state of the headset and controllers.
    """
    def __init__(self, *, recenter_resets_rotation: bool = False):
        """
        Args:
            recenter_resets_rotation: If True, grip+trigger recenter resets both translation
                and orientation. If False (default), only translation is reset.
        """
        # enumerate the required instance extensions
        extensions = [xr.MND_HEADLESS_EXTENSION_NAME]  # Permits use without a graphics display

        # tracking controllers in headless mode requires a way to get the current XrTime
        if platform.system() == "Windows":
            extensions.append(xr.KHR_WIN32_CONVERT_PERFORMANCE_COUNTER_TIME_EXTENSION_NAME)
        else:  # Linux
            extensions.append(xr.KHR_CONVERT_TIMESPEC_TIME_EXTENSION_NAME)

        # create instance for headless use
        self.instance = xr.create_instance(xr.InstanceCreateInfo(
            enabled_extension_names=extensions,
        ))

        system_id = xr.get_system(self.instance, xr.SystemGetInfo(form_factor=xr.FormFactor.HEAD_MOUNTED_DISPLAY))
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

        self.left_controller = ViveController(self.instance, "Left", "/user/hand/left")
        self.right_controller = ViveController(self.instance, "Right", "/user/hand/right")

        self.controllers = [
            self.left_controller,
            self.right_controller,
        ]

        # create bindings and action sets for the controllers, so that we can receive events from them
        suggested_bindings = []
        for controller in self.controllers:
            suggested_bindings.extend(controller.register(self.action_set, self.session))

        vive_bindings = (xr.ActionSuggestedBinding * len(suggested_bindings))(
            *suggested_bindings
        )

        xr.suggest_interaction_profile_bindings(
            instance=self.instance,
            suggested_bindings=xr.InteractionProfileSuggestedBinding(
                interaction_profile=xr.string_to_path(
                    self.instance,
                    "/interaction_profiles/htc/vive_controller",
                ),
                count_suggested_bindings=len(vive_bindings),
                suggested_bindings=vive_bindings,
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

        self.recenter_resets_rotation = recenter_resets_rotation

        # initialize the session state
        self.session_state = xr.SessionState.UNKNOWN

        # internal state of the HMD
        self._hmd_position = xr.Vector3f()
        self._hmd_orientation = xr.Quaternionf()

        # relative-transform tracking (one entry per controller)
        self._grip_last = [False] * len(self.controllers)
        self._trigger_full_last = [False] * len(self.controllers)
        self._tracking_active = [False] * len(self.controllers)
        self._anchor_position = [xr.Vector3f() for _ in self.controllers]
        self._anchor_orientation = [xr.Quaternionf() for _ in self.controllers]

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

        # update the controller states, convert to robotics frame, and compute relative transforms
        for i, controller in enumerate(self.controllers):
            controller.update(self.session, xr_time_now)

            grip = controller.grip_button
            trigger_full = controller.trigger >= 1.0

            # Grip rising edge: toggle between streaming and frozen tracking
            if grip and not self._grip_last[i]:
                self._tracking_active[i] = not self._tracking_active[i]
                if self._tracking_active[i]:
                    # Place anchor so the existing accumulated delta is preserved
                    prev_rp = controller.relative_position
                    ap = xr.Vector3f()
                    ap.x = controller.position.x - prev_rp.x
                    ap.y = controller.position.y - prev_rp.y
                    ap.z = controller.position.z - prev_rp.z
                    self._anchor_position[i] = ap

                    # q_anchor = q_prev_delta^{-1} * q_current
                    prev_rq = controller.relative_orientation
                    aw, ax, ay, az = _quat_multiply(
                        (prev_rq.w, -prev_rq.x, -prev_rq.y, -prev_rq.z),
                        (controller.orientation.w, controller.orientation.x,
                         controller.orientation.y, controller.orientation.z),
                    )
                    aq = xr.Quaternionf()
                    aq.w = aw
                    aq.x = ax
                    aq.y = ay
                    aq.z = az
                    self._anchor_orientation[i] = aq

            # Grip held + trigger reaches 1.0: clear delta and force tracking on
            if grip and trigger_full and not self._trigger_full_last[i]:
                controller._delta_position = xr.Vector3f()
                if self.recenter_resets_rotation:
                    controller._delta_orientation = xr.Quaternionf()
                    controller._delta_orientation.w = 1.0
                self._tracking_active[i] = True
                ap = xr.Vector3f()
                ap.x = controller.position.x
                ap.y = controller.position.y
                ap.z = controller.position.z
                self._anchor_position[i] = ap
                if self.recenter_resets_rotation:
                    aq = xr.Quaternionf()
                    aq.w = controller.orientation.w
                    aq.x = controller.orientation.x
                    aq.y = controller.orientation.y
                    aq.z = controller.orientation.z
                    self._anchor_orientation[i] = aq

            # Continuously compute delta while tracking is active
            if self._tracking_active[i]:
                ap = self._anchor_position[i]
                rp = xr.Vector3f()
                rp.x = controller.position.x - ap.x
                rp.y = controller.position.y - ap.y
                rp.z = controller.position.z - ap.z
                controller._delta_position = rp

                # q_delta = q_current * q_anchor^{-1}
                aq = self._anchor_orientation[i]
                w, x, y, z = _quat_multiply(
                    (controller.orientation.w, controller.orientation.x,
                     controller.orientation.y, controller.orientation.z),
                    (aq.w, -aq.x, -aq.y, -aq.z),
                )
                rq = xr.Quaternionf()
                rq.w = w
                rq.x = x
                rq.y = y
                rq.z = z
                controller._delta_orientation = rq

            self._grip_last[i] = grip
            self._trigger_full_last[i] = trigger_full

    def exit(self):
        # clean up
        xr.destroy_action_set(self.action_set)
        xr.destroy_instance(self.instance)
