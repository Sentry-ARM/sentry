from __future__ import annotations

import datetime
from collections.abc import Sequence
from typing import TYPE_CHECKING, ClassVar

from django.conf import settings
from django.db import models
from django.db.models import QuerySet
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from sentry.backup.scopes import RelocationScope
from sentry.db.models import (
    BoundedPositiveIntegerField,
    FlexibleForeignKey,
    Model,
    region_silo_model,
    sane_repr,
)
from sentry.db.models.fields.hybrid_cloud_foreign_key import HybridCloudForeignKey
from sentry.db.models.manager.base import BaseManager
from sentry.types.activity import ActivityType
from sentry.types.actor import Actor
from sentry.types.group import GROUP_SUBSTATUS_TO_GROUP_HISTORY_STATUS

if TYPE_CHECKING:
    from sentry.models.group import Group
    from sentry.models.release import Release
    from sentry.models.team import Team
    from sentry.users.models.user import User
    from sentry.users.services.user import RpcUser


class GroupHistoryStatus:
    # Note that we don't record the initial group creation unresolved here to save on creating a row
    # for every group.

    # Prefer to use ONGOING instead of UNRESOLVED. We will be deprecating UNRESOLVED in the future.
    # Use REGRESSED/ESCALATING to specify other substatuses for UNRESOLVED groups.
    UNRESOLVED = 0
    ONGOING = UNRESOLVED

    RESOLVED = 1
    SET_RESOLVED_IN_RELEASE = 11
    SET_RESOLVED_IN_COMMIT = 12
    SET_RESOLVED_IN_PULL_REQUEST = 13
    AUTO_RESOLVED = 2
    IGNORED = 3  # use the ARCHIVED_XXX statuses instead
    UNIGNORED = 4
    ASSIGNED = 5
    UNASSIGNED = 6
    REGRESSED = 7
    DELETED = 8
    DELETED_AND_DISCARDED = 9
    REVIEWED = 10
    ESCALATING = 14

    # Ignored/Archived statuses
    ARCHIVED_UNTIL_ESCALATING = 15
    ARCHIVED_FOREVER = 16
    ARCHIVED_UNTIL_CONDITION_MET = 17

    # Just reserving this for us with queries, we don't store the first time a group is created in
    # `GroupHistoryStatus`
    NEW = 20

    PRIORITY_HIGH = 21
    PRIORITY_MEDIUM = 22
    PRIORITY_LOW = 23


STRING_TO_STATUS_LOOKUP = {
    "unresolved": GroupHistoryStatus.UNRESOLVED,
    "resolved": GroupHistoryStatus.RESOLVED,
    "set_resolved_in_release": GroupHistoryStatus.SET_RESOLVED_IN_RELEASE,
    "set_resolved_in_commit": GroupHistoryStatus.SET_RESOLVED_IN_COMMIT,
    "set_resolved_in_pull_request": GroupHistoryStatus.SET_RESOLVED_IN_PULL_REQUEST,
    "auto_resolved": GroupHistoryStatus.AUTO_RESOLVED,
    "ignored": GroupHistoryStatus.IGNORED,
    "unignored": GroupHistoryStatus.UNIGNORED,
    "assigned": GroupHistoryStatus.ASSIGNED,
    "unassigned": GroupHistoryStatus.UNASSIGNED,
    "regressed": GroupHistoryStatus.REGRESSED,
    "deleted": GroupHistoryStatus.DELETED,
    "deleted_and_discarded": GroupHistoryStatus.DELETED_AND_DISCARDED,
    "reviewed": GroupHistoryStatus.REVIEWED,
    "new": GroupHistoryStatus.NEW,
    "escalating": GroupHistoryStatus.ESCALATING,
    "archived_until_escalating": GroupHistoryStatus.ARCHIVED_UNTIL_ESCALATING,
    "archived_forever": GroupHistoryStatus.ARCHIVED_FOREVER,
    "archived_until_condition_met": GroupHistoryStatus.ARCHIVED_UNTIL_CONDITION_MET,
}
STATUS_TO_STRING_LOOKUP = {status: string for string, status in STRING_TO_STATUS_LOOKUP.items()}


ACTIONED_STATUSES = [
    GroupHistoryStatus.RESOLVED,
    GroupHistoryStatus.SET_RESOLVED_IN_RELEASE,
    GroupHistoryStatus.SET_RESOLVED_IN_COMMIT,
    GroupHistoryStatus.SET_RESOLVED_IN_PULL_REQUEST,
    GroupHistoryStatus.IGNORED,
    GroupHistoryStatus.REVIEWED,
    GroupHistoryStatus.DELETED,
    GroupHistoryStatus.DELETED_AND_DISCARDED,
    GroupHistoryStatus.ARCHIVED_UNTIL_ESCALATING,
]

UNRESOLVED_STATUSES = (
    GroupHistoryStatus.UNRESOLVED,
    GroupHistoryStatus.ONGOING,
    GroupHistoryStatus.REGRESSED,
    GroupHistoryStatus.ESCALATING,
)
RESOLVED_STATUSES = (
    GroupHistoryStatus.RESOLVED,
    GroupHistoryStatus.SET_RESOLVED_IN_RELEASE,
    GroupHistoryStatus.SET_RESOLVED_IN_COMMIT,
    GroupHistoryStatus.SET_RESOLVED_IN_PULL_REQUEST,
    GroupHistoryStatus.AUTO_RESOLVED,
)

PREVIOUS_STATUSES = {
    GroupHistoryStatus.UNRESOLVED: RESOLVED_STATUSES,
    GroupHistoryStatus.ONGOING: RESOLVED_STATUSES
    + (GroupHistoryStatus.REGRESSED, GroupHistoryStatus.ESCALATING, GroupHistoryStatus.IGNORED),
    GroupHistoryStatus.RESOLVED: UNRESOLVED_STATUSES,
    GroupHistoryStatus.SET_RESOLVED_IN_RELEASE: UNRESOLVED_STATUSES,
    GroupHistoryStatus.SET_RESOLVED_IN_COMMIT: UNRESOLVED_STATUSES,
    GroupHistoryStatus.SET_RESOLVED_IN_PULL_REQUEST: UNRESOLVED_STATUSES,
    GroupHistoryStatus.AUTO_RESOLVED: UNRESOLVED_STATUSES,
    GroupHistoryStatus.IGNORED: (GroupHistoryStatus.UNIGNORED,),
    GroupHistoryStatus.UNIGNORED: (GroupHistoryStatus.IGNORED,),
    GroupHistoryStatus.ASSIGNED: (GroupHistoryStatus.UNASSIGNED,),
    GroupHistoryStatus.UNASSIGNED: (GroupHistoryStatus.ASSIGNED,),
    GroupHistoryStatus.REGRESSED: RESOLVED_STATUSES,
    GroupHistoryStatus.ESCALATING: (
        GroupHistoryStatus.ARCHIVED_UNTIL_ESCALATING,
        GroupHistoryStatus.ARCHIVED_UNTIL_CONDITION_MET,
        GroupHistoryStatus.IGNORED,
    ),
}

ACTIVITY_STATUS_TO_GROUP_HISTORY_STATUS = {
    ActivityType.SET_IGNORED.value: GroupHistoryStatus.IGNORED,
    ActivityType.SET_RESOLVED.value: GroupHistoryStatus.RESOLVED,
    ActivityType.SET_RESOLVED_IN_COMMIT.value: GroupHistoryStatus.SET_RESOLVED_IN_COMMIT,
    ActivityType.SET_RESOLVED_IN_RELEASE.value: GroupHistoryStatus.SET_RESOLVED_IN_RELEASE,
    ActivityType.SET_UNRESOLVED.value: GroupHistoryStatus.UNRESOLVED,
    ActivityType.AUTO_SET_ONGOING.value: GroupHistoryStatus.UNRESOLVED,
    ActivityType.SET_ESCALATING.value: GroupHistoryStatus.ESCALATING,
}


class GroupHistoryManager(BaseManager["GroupHistory"]):
    def filter_to_team(self, team: Team) -> QuerySet[GroupHistory]:
        from sentry.models.groupassignee import GroupAssignee
        from sentry.models.project import Project

        project_list = Project.objects.get_for_team_ids(team_ids=[team.id])
        user_ids = list(team.member_set.values_list("user_id", flat=True))
        assigned_groups = (
            GroupAssignee.objects.filter(team=team)
            .union(GroupAssignee.objects.filter(user_id__in=user_ids))
            .values_list("group_id", flat=True)
        )
        return self.filter(
            project__in=project_list,
            group_id__in=assigned_groups,
        )


@region_silo_model
class GroupHistory(Model):
    """
    This model is used to track certain status changes for groups,
    and is designed to power a few types of queries:
    - `resolved_in:release` syntax - we can query for entries with status=REGRESSION and matching release
    - Time to Resolution and Age of Unresolved Issues-style queries
    - Issue Activity/Status over time breakdown (i.e. for each of the last 14 days, how many new, resolved, regressed, unignored, etc. issues were there?)
    """

    __relocation_scope__ = RelocationScope.Excluded

    objects: ClassVar[GroupHistoryManager] = GroupHistoryManager()

    organization = FlexibleForeignKey("sentry.Organization", db_constraint=False)
    group = FlexibleForeignKey("sentry.Group", db_constraint=False)
    project = FlexibleForeignKey("sentry.Project", db_constraint=False)
    release = FlexibleForeignKey("sentry.Release", null=True, db_constraint=False)

    user_id = HybridCloudForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete="SET_NULL")
    team = FlexibleForeignKey("sentry.Team", null=True, on_delete=models.SET_NULL)

    status = BoundedPositiveIntegerField(
        default=0,
        choices=(
            (GroupHistoryStatus.ONGOING, _("Ongoing")),
            (GroupHistoryStatus.RESOLVED, _("Resolved")),
            (GroupHistoryStatus.AUTO_RESOLVED, _("Automatically Resolved")),
            (GroupHistoryStatus.IGNORED, _("Ignored")),
            (GroupHistoryStatus.UNIGNORED, _("Unignored")),
            (GroupHistoryStatus.REGRESSED, _("Regressed")),
            (GroupHistoryStatus.ASSIGNED, _("Assigned")),
            (GroupHistoryStatus.UNASSIGNED, _("Unassigned")),
            (GroupHistoryStatus.DELETED, _("Deleted")),
            (GroupHistoryStatus.DELETED_AND_DISCARDED, _("Deleted and Discarded")),
            (GroupHistoryStatus.REVIEWED, _("Reviewed")),
            (GroupHistoryStatus.SET_RESOLVED_IN_RELEASE, _("Resolved in Release")),
            (GroupHistoryStatus.SET_RESOLVED_IN_COMMIT, _("Resolved in Commit")),
            (GroupHistoryStatus.SET_RESOLVED_IN_PULL_REQUEST, _("Resolved in Pull Request")),
            (GroupHistoryStatus.ESCALATING, _("Escalating")),
        ),
    )
    prev_history = FlexibleForeignKey(
        "sentry.GroupHistory", null=True
    )  # This field has no immediate use, but might be useful.
    prev_history_date = models.DateTimeField(
        null=True
    )  # This field is used to simplify query calculations.
    date_added = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = "sentry_grouphistory"
        app_label = "sentry"
        indexes = (
            models.Index(fields=("project", "status", "release")),
            models.Index(fields=("group", "status")),
            models.Index(fields=("project", "date_added")),
        )

    __repr__ = sane_repr("group_id", "release_id")

    @property
    def owner(self) -> Actor | None:
        """Part of ActorOwned protocol"""
        return Actor.from_id(user_id=self.user_id, team_id=self.team_id)

    @owner.setter
    def owner(self, actor: Actor | None) -> None:
        """Part of ActorOwned protocol"""
        self.team_id = None
        self.user_id = None
        if actor and actor.is_user:
            self.user_id = actor.id
        if actor and actor.is_team:
            self.team_id = actor.id


def get_prev_history(group: Group, status: int) -> GroupHistory | None:
    """
    Finds the most recent row that is the inverse of this history row, if one exists.
    """
    previous_statuses = PREVIOUS_STATUSES.get(status)
    if not previous_statuses:
        return None

    prev_histories = GroupHistory.objects.filter(
        group=group, status__in=previous_statuses
    ).order_by("-date_added")
    return prev_histories.first()


def record_group_history_from_activity_type(
    group: Group,
    activity_type: int,
    actor: RpcUser | User | Team | None = None,
    release: Release | None = None,
) -> GroupHistory | None:
    """
    Writes a `GroupHistory` row for an activity type if there's a relevant `GroupHistoryStatus` that
    maps to it
    """
    status = ACTIVITY_STATUS_TO_GROUP_HISTORY_STATUS.get(activity_type, None)

    # Substatus-based GroupHistory should override activity-based GroupHistory since it's more specific.
    if group.substatus:
        status_str = GROUP_SUBSTATUS_TO_GROUP_HISTORY_STATUS.get(group.substatus, None)
        if status_str is not None:
            status = STRING_TO_STATUS_LOOKUP.get(status_str, status)

    if status is not None:
        return record_group_history(group, status, actor, release)
    return None


def record_group_history(
    group: Group,
    status: int,
    actor: User | RpcUser | Team | None = None,
    release: Release | None = None,
) -> GroupHistory:
    from sentry.models.team import Team
    from sentry.users.models.user import User
    from sentry.users.services.user import RpcUser

    prev_history = get_prev_history(group, status)
    user_id = None
    team_id = None
    if actor:
        if isinstance(actor, RpcUser) or isinstance(actor, User):
            user_id = actor.id
        elif isinstance(actor, Team):
            team_id = actor.id
        else:
            raise ValueError("record_group_history actor argument must be RPCUser or Team")

    return GroupHistory.objects.create(
        organization=group.project.organization,
        group=group,
        project=group.project,
        release=release,
        user_id=user_id,
        team_id=team_id,
        status=status,
        prev_history=prev_history,
        prev_history_date=prev_history.date_added if prev_history else None,
    )


def bulk_record_group_history(
    groups: Sequence[Group],
    status: int,
    actor: User | RpcUser | Team | None = None,
    release: Release | None = None,
) -> list[GroupHistory]:
    from sentry.models.team import Team
    from sentry.users.models.user import User
    from sentry.users.services.user import RpcUser

    def get_prev_history_date(group: Group, status: int) -> datetime.datetime | None:
        prev_history = get_prev_history(group, status)
        return prev_history.date_added if prev_history else None

    user_id: int | None = None
    team_id: int | None = None
    if actor:
        if isinstance(actor, RpcUser) or isinstance(actor, User):
            user_id = actor.id
        elif isinstance(actor, Team):
            team_id = actor.id
        else:
            raise ValueError("record_group_history actor argument must be RPCUser or Team")

    return GroupHistory.objects.bulk_create(
        [
            GroupHistory(
                organization=group.project.organization,
                group=group,
                project=group.project,
                release=release,
                team_id=team_id,
                user_id=user_id,
                status=status,
                prev_history=get_prev_history(group, status),
                prev_history_date=get_prev_history_date(group, status),
            )
            for group in groups
        ]
    )
