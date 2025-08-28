import platform
import numpy as np
import xr

from .vive_controller import ViveController

if platform.system() == "Windows":
    import ctypes.wintypes
    from .windows_performance_counter import WindowsPerformanceCounter as PerformanceCounter
else:
    import ctypes
    from .linux_performance_counter import LinuxPerformanceCounter as PerformanceCounter


class SteamVrBridge:
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

        self.performance_counter = PerformanceCounter(self.instance)

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
