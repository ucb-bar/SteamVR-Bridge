import numpy as np
import xr


class ViveController:
    def __init__(self, instance: xr.Instance, name: str, path: str):
        self.instance = instance
        self.name = name
        self.path_array = (xr.Path * 1)(xr.string_to_path(instance, path), )
        self.path = self.path_array[0]

        self._position = xr.Vector3f()
        self._orientation = xr.Quaternionf()
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
            self._orientation = space_location.pose.orientation

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
    def pose(self) -> np.ndarray:
        pos = self.position.as_numpy()
        quat = np.array([
            self.orientation.w,
            self.orientation.x,
            self.orientation.y,
            self.orientation.z,
        ])
        return np.concatenate((pos, quat), axis=0)

    @property
    def position(self) -> xr.Vector3f:
        return self._position

    @property
    def orientation(self) -> xr.Quaternionf:
        return self._orientation

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
