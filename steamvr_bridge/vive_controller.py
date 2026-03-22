import xr

from .frame_transform import _vr_to_robotics_position, _vr_to_robotics_orientation


class ViveController:
    """
    A class representing a VIVE Controller (2018).

    For more information, please refer to the VIVE Controller (2018) product documentation:
    https://www.vive.com/us/support/vive-pro2/category_howto/about-the-controllers---2018.html
    """
    def __init__(self, instance: xr.Instance, name: str, path: str, state_key: str | None = None):
        self.instance = instance
        self.name = name
        self.state_key = state_key or name.lower()
        self.kind = "controller"
        self.interaction_profile_path = "/interaction_profiles/htc/vive_controller"
        self.tracking_starts_active = False
        self.user_path_string = path
        self.path_array = (xr.Path * 1)(xr.string_to_path(instance, path), )
        self.path = self.path_array[0]

        # controller states
        self._world_location = xr.Vector3f()
        self._world_orientation = xr.Quaternionf()
        self._pose_valid = False
        self._menu_button = False
        self._trackpad_x = 0.0
        self._trackpad_y = 0.0
        self._trackpad_button = False
        self._trigger = 0.0
        self._grip_button = False

        # relative transform (toggled on/off by grip; cleared to zero by grip+trigger)
        self._delta_location = xr.Vector3f()
        self._delta_orientation = xr.Quaternionf()
        self._delta_orientation.w = 1.0
        self.reference_space = None
        self.action_space = None

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
        """
        Synchronize the controller state with OpenXR.

        Args:
            session: The OpenXR session.
            xr_time_now: The current time in the OpenXR time domain.
        """
        space_location = xr.locate_space(
            space=self.action_space,
            base_space=self.reference_space,
            time=xr_time_now,
        )
        if space_location.location_flags & xr.SPACE_LOCATION_POSITION_VALID_BIT:
            steamvr_position = space_location.pose.position
            steamvr_orientation = space_location.pose.orientation
            self._world_location = _vr_to_robotics_position(steamvr_position)
            self._world_orientation = _vr_to_robotics_orientation(steamvr_orientation)
            self._pose_valid = True
        else:
            self._pose_valid = False

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
    def location(self) -> xr.Vector3f:
        """
        Get the controller location in the world frame in meters.

        To get each element of the location, use `location.x`, `location.y`, and `location.z`.
        To get the location as a numpy array, use `location.as_numpy()`.

        Returns:
            The controller location as a `Vector3f` struct.
        """
        return self._world_location

    @property
    def orientation(self) -> xr.Quaternionf:
        """
        Get the controller orientation in the world frame as a quaternion.

        To get each element of the orientation, use `orientation.w`, `orientation.x`, `orientation.y`, and
        `orientation.z`.
        To get the orientation as a numpy array, use `orientation.as_numpy()`. Pay special attention that
        OpenXR uses scalar-last format (`[x, y, z, w]`) for quaternions.
        In this repository, quaternion serialization and math convention is scalar-first `(w, x, y, z)`.

        Returns:
            The controller orientation as a `Quaternionf` struct.
        """
        return self._world_orientation

    @property
    def pose_valid(self) -> bool:
        """Return whether the most recent pose sample was valid."""
        return self._pose_valid

    @property
    def relative_location(self) -> xr.Vector3f:
        """
        Get the relative controller location delta (meters).  Grip toggles streaming
        on/off; grip + trigger (fully pressed) resets to zero.

        Returns:
            The relative location as a ``Vector3f`` struct.
        """
        return self._delta_location

    @property
    def relative_orientation(self) -> xr.Quaternionf:
        """
        Get the relative controller orientation delta.  Grip toggles streaming
        on/off; grip + trigger (fully pressed) resets to identity.

        Returns:
            The relative orientation as a ``Quaternionf`` struct.
        """
        return self._delta_orientation

    @property
    def menu_button_pressed(self) -> bool:
        """
        Get the state of the menu button.

        Returns:
            The state of the menu button as a boolean.
        """
        return self._menu_button.current_state

    @property
    def trackpad_x(self) -> float:
        """
        Get the state of the trackpad x axis.

        Returns:
            The state of the trackpad x axis as a float.
        """
        return self._trackpad_x.current_state

    @property
    def trackpad_y(self) -> float:
        """
        Get the state of the trackpad y axis.

        Returns:
            The state of the trackpad y axis as a float.
        """
        return self._trackpad_y.current_state

    @property
    def trackpad_button_pressed(self) -> bool:
        """
        Get the state of the trackpad button.

        Returns:
            The state of the trackpad button as a boolean.
        """
        return self._trackpad_button.current_state

    @property
    def trigger(self) -> float:
        """
        Get the state of the trigger.

        Returns:
            The state of the trigger as a float.
        """
        return self._trigger.current_state

    @property
    def grip_button_pressed(self) -> bool:
        """
        Get the state of the grip button.

        Returns:
            The state of the grip button as a boolean.
        """
        return self._grip_button.current_state
