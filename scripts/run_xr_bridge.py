import platform
import time

if platform.system() == "Windows":
    import ctypes.wintypes
else:
    import ctypes

import numpy as np
import xr


if platform.system() == "Windows":
    class WindowsPerformanceCounter:
        def __init__(self, instance: xr.Instance):
            self.instance = instance
            self.pc_time = ctypes.wintypes.LARGE_INTEGER()
            self.kernel32 = ctypes.WinDLL("kernel32")
            self.pxrConvertWin32PerformanceCounterToTimeKHR = ctypes.cast(
                xr.get_instance_proc_addr(
                    instance=self.instance,
                    name="xrConvertWin32PerformanceCounterToTimeKHR",
                ),
                xr.PFN_xrConvertWin32PerformanceCounterToTimeKHR,
            )

        def time_from_perf_counter(self, performance_counter: ctypes.wintypes.LARGE_INTEGER) -> xr.Time:
            xr_time = xr.Time()
            result = self.pxrConvertWin32PerformanceCounterToTimeKHR(
                self.instance,
                ctypes.pointer(performance_counter),
                ctypes.byref(xr_time),
            )
            result = xr.check_result(result)
            if result.is_exception():
                raise result
            return xr_time

        def get(self):
            self.kernel32.QueryPerformanceCounter(ctypes.byref(self.pc_time))
            return self.time_from_perf_counter(self.instance, self.pc_time)

else:
    class LinuxPerformanceCounter:
        def __init__(self, instance: xr.Instance):
            self.instance = instance
            self.timespecTime = xr.timespec()
            self.pxrConvertTimespecTimeToTimeKHR = ctypes.cast(
                xr.get_instance_proc_addr(
                    instance=self.instance,
                    name="xrConvertTimespecTimeToTimeKHR",
                ),
                xr.PFN_xrConvertTimespecTimeToTimeKHR,
            )

        def time_from_timespec(self, timespec_time: xr.timespec) -> xr.Time:
            xr_time = xr.Time()
            result = self.pxrConvertTimespecTimeToTimeKHR(
                self.instance,
                ctypes.pointer(timespec_time),
                ctypes.byref(xr_time),
            )
            result = xr.check_result(result)
            if result.is_exception():
                raise result
            return xr_time

        def get(self):
            time_float = time.clock_gettime(time.CLOCK_MONOTONIC)
            self.timespecTime.tv_sec = int(time_float)
            self.timespecTime.tv_nsec = int((time_float % 1) * 1e9)
            return self.time_from_timespec(self.timespecTime)


class ViveController:
    def __init__(self, instance: xr.Instance, name: str, path: str):
        self.instance = instance
        self.name = name
        self.path_array = (xr.Path * 1)(xr.string_to_path(instance, path), )
        self.path = self.path_array[0]

        self._position = xr.Vector3f()
        self._rotation = xr.Quaternionf()
        self._menu_button = False
        self._trackpad_x = 0.0
        self._trackpad_y = 0.0
        self._trackpad_button = False
        self._trigger = 0.0
        self._grip_button = False

    def register(self, action_set: xr.ActionSet, session: xr.Session):
        name_lower = f"{self.name.lower()}"

        self.pose_action = xr.create_action(
            action_set=action_set,
            create_info=xr.ActionCreateInfo(
                action_type=xr.ActionType.POSE_INPUT,
                action_name=f"{name_lower}_pose",
                localized_action_name=f"{self.name} Pose",
                count_subaction_paths=1,
                subaction_paths=self.path_array,
            ),
        )

        self.menu_button_action = xr.create_action(
            action_set=action_set,
            create_info=xr.ActionCreateInfo(
                action_type=xr.ActionType.BOOLEAN_INPUT,
                action_name=f"{name_lower}_menu_button",
                localized_action_name=f"{self.name} Menu Button",
                count_subaction_paths=1,
                subaction_paths=self.path_array,
            ),
        )
        self.trackpad_x_action = xr.create_action(
            action_set=action_set,
            create_info=xr.ActionCreateInfo(
                action_type=xr.ActionType.FLOAT_INPUT,
                action_name=f"{name_lower}_trackpad_x",
                localized_action_name=f"{self.name} Trackpad X",
                count_subaction_paths=1,
                subaction_paths=self.path_array,
            ),
        )
        self.trackpad_y_action = xr.create_action(
            action_set=action_set,
            create_info=xr.ActionCreateInfo(
                action_type=xr.ActionType.FLOAT_INPUT,
                action_name=f"{name_lower}_trackpad_y",
                localized_action_name=f"{self.name} Trackpad Y",
                count_subaction_paths=1,
                subaction_paths=self.path_array,
            ),
        )
        self.trackpad_button_action = xr.create_action(
            action_set=action_set,
            create_info=xr.ActionCreateInfo(
                action_type=xr.ActionType.BOOLEAN_INPUT,
                action_name=f"{name_lower}_trackpad_button",
                localized_action_name=f"{self.name} Trackpad Click",
                count_subaction_paths=1,
                subaction_paths=self.path_array,
            ),
        )
        self.trigger_action = xr.create_action(
            action_set=action_set,
            create_info=xr.ActionCreateInfo(
                action_type=xr.ActionType.FLOAT_INPUT,
                action_name=f"{name_lower}_trigger",
                localized_action_name=f"{self.name} Trigger",
                count_subaction_paths=1,
                subaction_paths=self.path_array,
            ),
        )
        self.grip_button_action = xr.create_action(
            action_set=action_set,
            create_info=xr.ActionCreateInfo(
                action_type=xr.ActionType.BOOLEAN_INPUT,
                action_name=f"{name_lower}_grip_button",
                localized_action_name=f"{self.name} Grip Button",
                count_subaction_paths=1,
                subaction_paths=self.path_array,
            ),
        )

        self.reference_space = xr.create_reference_space(
            session=session,
            create_info=xr.ReferenceSpaceCreateInfo(
                reference_space_type=xr.ReferenceSpaceType.STAGE,
            ),
        )
        self.action_space = xr.create_action_space(
            session=session,
            create_info=xr.ActionSpaceCreateInfo(
                action=self.pose_action,
                subaction_path=self.path,
            ),
        )

        return (
            xr.ActionSuggestedBinding(
                action=self.pose_action,
                binding=xr.string_to_path(
                    instance=self.instance,
                    path_string=f"/user/hand/{name_lower}/input/grip/pose",
                ),
            ),
            xr.ActionSuggestedBinding(
                action=self.menu_button_action,
                binding=xr.string_to_path(
                    instance=self.instance,
                    path_string=f"/user/hand/{name_lower}/input/menu/click",
                ),
            ),
            xr.ActionSuggestedBinding(
                action=self.trackpad_x_action,
                binding=xr.string_to_path(
                    instance=self.instance,
                    path_string=f"/user/hand/{name_lower}/input/trackpad/x",
                ),
            ),
            xr.ActionSuggestedBinding(
                action=self.trackpad_y_action,
                binding=xr.string_to_path(
                    instance=self.instance,
                    path_string=f"/user/hand/{name_lower}/input/trackpad/y",
                ),
            ),
            xr.ActionSuggestedBinding(
                action=self.trackpad_button_action,
                binding=xr.string_to_path(
                    instance=self.instance,
                    path_string=f"/user/hand/{name_lower}/input/trackpad/click",
                ),
            ),

            xr.ActionSuggestedBinding(
                action=self.trigger_action,
                binding=xr.string_to_path(
                    instance=self.instance,
                    path_string=f"/user/hand/{name_lower}/input/trigger/value",
                ),
            ),
            xr.ActionSuggestedBinding(
                action=self.grip_button_action,
                binding=xr.string_to_path(
                    instance=self.instance,
                    path_string=f"/user/hand/{name_lower}/input/squeeze/click",
                ),
            ),
        )

    def update(self, session: xr.Session, xr_time_now: xr.Time):
        space_location = xr.locate_space(
            space=self.action_space,
            base_space=self.reference_space,
            time=xr_time_now,
        )
        if space_location.location_flags & xr.SPACE_LOCATION_POSITION_VALID_BIT:
            self._position = space_location.pose.position
            self._rotation = space_location.pose.orientation

        self._menu_button = xr.get_action_state_boolean(
            session=session,
            get_info=xr.ActionStateGetInfo(self.menu_button_action, self.path)
        )
        self._trackpad_x = xr.get_action_state_float(
            session=session,
            get_info=xr.ActionStateGetInfo(self.trackpad_x_action, self.path)
        )
        self._trackpad_y = xr.get_action_state_float(
            session=session,
            get_info=xr.ActionStateGetInfo(self.trackpad_y_action, self.path)
        )
        self._trackpad_button = xr.get_action_state_boolean(
            session=session,
            get_info=xr.ActionStateGetInfo(self.trackpad_button_action, self.path)
        )
        self._trigger = xr.get_action_state_float(
            session=session,
            get_info=xr.ActionStateGetInfo(self.trigger_action, self.path)
        )
        self._grip_button = xr.get_action_state_boolean(
            session=session,
            get_info=xr.ActionStateGetInfo(self.grip_button_action, self.path)
        )

    @property
    def position(self) -> xr.Vector3f:
        return self._position

    @property
    def rotation(self) -> xr.Quaternionf:
        return self._rotation

    @property
    def menu_button(self) -> bool:
        return self._menu_button.current_state

    @property
    def trackpad_x(self) -> float:
        return self._trackpad_x.current_state

    @property
    def trackpad_y(self) -> float:
        return self._trackpad_y.current_state

    @property
    def trackpad_button(self) -> bool:
        return self._trackpad_button.current_state

    @property
    def trigger(self) -> float:
        return self._trigger.current_state

    @property
    def grip_button(self) -> bool:
        return self._grip_button.current_state


class HeadlessSession:
    def __init__(self):
        # Enumerate the required instance extensions
        extensions = [xr.MND_HEADLESS_EXTENSION_NAME]  # Permits use without a graphics display

        # Tracking controllers in headless mode requires a way to get the current XrTime
        if platform.system() == "Windows":
            extensions.append(xr.KHR_WIN32_CONVERT_PERFORMANCE_COUNTER_TIME_EXTENSION_NAME)
        else:  # Linux
            extensions.append(xr.KHR_CONVERT_TIMESPEC_TIME_EXTENSION_NAME)

        # Create instance for headless use
        self.instance = xr.create_instance(xr.InstanceCreateInfo(
            enabled_extension_names=extensions,
        ))
        self.system = xr.get_system(
            self.instance,
            # Presumably the form factor is irrelevant in headless mode...
            xr.SystemGetInfo(form_factor=xr.FormFactor.HEAD_MOUNTED_DISPLAY),
        )
        self.session = xr.create_session(
            self.instance,
            xr.SessionCreateInfo(
                system_id=self.system,
                next=None,  # No GraphicsBinding structure is required here in HEADLESS mode
            )
        )

        if platform.system() == "Windows":
            self.performance_counter = WindowsPerformanceCounter(self.instance)
        else:
            self.performance_counter = LinuxPerformanceCounter(self.instance)

        # Set up controller tracking, as one possible legitimate headless activity
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

        self.session_state = xr.SessionState.UNKNOWN
        # Loop over session frames

    def update(self):
        # Poll session state changed events
        while True:
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
                break  # There is no event in the queue at this moment

        # wait_frame()/begin_frame()/end_frame() are not required in headless mode
        xr.wait_frame(session=self.session)  # Helps SteamVR show application name better

        xr_time_now = self.performance_counter.get()

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
        hmd_location = xr.locate_space(
            space=self.view_reference_space,
            base_space=self.reference_space,
            time=xr_time_now,
        )
        # if hmd_location.location_flags & xr.SPACE_LOCATION_POSITION_VALID_BIT:
        #     print(f"HMD location: {hmd_location.pose}")

        for controller in self.controllers:
            controller.update(self.session, xr_time_now)

    def exit(self):
        # Clean up
        system = xr.NULL_SYSTEM_ID
        xr.destroy_action_set(self.action_set)
        self.action_set = None
        xr.destroy_instance(self.instance)
        self.instance = None


session = HeadlessSession()

while True:
    session.update()
    print("LT:", session.left_controller.trigger, "RT:", session.right_controller.trigger)
    print("LT:", session.left_controller.position, "RT:", session.right_controller.position)
