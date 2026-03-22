import xr

from .frame_transform import _vr_to_robotics_position, _vr_to_robotics_orientation


class ViveTracker:
    """Pose-only wrapper for a VIVE tracker role exposed via OpenXR."""

    interaction_profile_path = "/interaction_profiles/htc/vive_tracker_htcx"

    def __init__(self, instance: xr.Instance, name: str, role: str, state_key: str | None = None):
        self.instance = instance
        self.name = name
        self.role = role
        self.state_key = state_key or role
        self.kind = "tracker"
        self.tracking_starts_active = True

        self.user_path_string = f"/user/vive_tracker_htcx/role/{role}"
        self.path_array = (xr.Path * 1)(xr.string_to_path(instance, self.user_path_string), )
        self.path = self.path_array[0]

        self._world_location = xr.Vector3f()
        self._world_orientation = xr.Quaternionf()
        self._pose_valid = False

        self._delta_location = xr.Vector3f()
        self._delta_orientation = xr.Quaternionf()
        self._delta_orientation.w = 1.0

        self.reference_space = None
        self.action_space = None

    def register(self, action_set: xr.ActionSet, session: xr.Session):
        role_token = self.role.replace("_", "")
        action_name = f"tracker_{role_token}_pose"

        self.pose_action = xr.create_action(
            action_set=action_set,
            create_info=xr.ActionCreateInfo(
                action_type=xr.ActionType.POSE_INPUT,
                action_name=action_name,
                localized_action_name=f"{self.name} Pose",
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
        try:
            self.action_space = xr.create_action_space(
                session=session,
                create_info=xr.ActionSpaceCreateInfo(
                    action=self.pose_action,
                    subaction_path=self.path,
                ),
            )
        except xr.exception.PathUnsupportedError:
            self.action_space = None

        return (
            xr.ActionSuggestedBinding(
                action=self.pose_action,
                binding=xr.string_to_path(
                    instance=self.instance,
                    path_string=f"{self.user_path_string}/input/grip/pose",
                ),
            ),
        )

    def update(self, session: xr.Session, xr_time_now: xr.Time):
        del session

        if self.action_space is None or self.reference_space is None:
            self._pose_valid = False
            return

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

    @property
    def location(self) -> xr.Vector3f:
        return self._world_location

    @property
    def orientation(self) -> xr.Quaternionf:
        return self._world_orientation

    @property
    def pose_valid(self) -> bool:
        return self._pose_valid

    @property
    def relative_location(self) -> xr.Vector3f:
        return self._delta_location

    @property
    def relative_orientation(self) -> xr.Quaternionf:
        return self._delta_orientation

    @property
    def grip_button_pressed(self) -> bool:
        return False

    @property
    def trigger(self) -> float:
        return 0.0
