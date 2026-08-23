"""Role permission matrix."""

from enum import StrEnum

from app.models.user import UserRole


class Permission(StrEnum):
    """Foundation permissions used by protected API endpoints."""

    MANAGE_USERS = "manage_users"
    OPERATE_INFRASTRUCTURE = "operate_infrastructure"
    SUBMIT_WORKLOAD = "submit_workload"
    VIEW_PLATFORM = "view_platform"
    VIEW_AUDIT = "view_audit"
    MANAGE_POLICIES = "manage_policies"
    MANAGE_SIMULATION = "manage_simulation"
    MANAGE_DECISIONS = "manage_decisions"
    RUN_EXPERIMENTS = "run_experiments"


ROLE_PERMISSIONS: dict[UserRole, frozenset[Permission]] = {
    UserRole.ADMINISTRATOR: frozenset(Permission),
    UserRole.INFRASTRUCTURE_OPERATOR: frozenset(
        {
            Permission.OPERATE_INFRASTRUCTURE,
            Permission.SUBMIT_WORKLOAD,
            Permission.VIEW_PLATFORM,
            Permission.VIEW_AUDIT,
            Permission.MANAGE_SIMULATION,
            Permission.MANAGE_DECISIONS,
            Permission.RUN_EXPERIMENTS,
        }
    ),
    UserRole.AI_ENGINEER: frozenset(
        {
            Permission.SUBMIT_WORKLOAD,
            Permission.VIEW_PLATFORM,
            Permission.RUN_EXPERIMENTS,
        }
    ),
    UserRole.RESEARCHER: frozenset(
        {
            Permission.SUBMIT_WORKLOAD,
            Permission.VIEW_PLATFORM,
            Permission.RUN_EXPERIMENTS,
        }
    ),
    UserRole.VIEWER: frozenset({Permission.VIEW_PLATFORM}),
    UserRole.AUDITOR: frozenset({Permission.VIEW_PLATFORM, Permission.VIEW_AUDIT}),
}


def role_has_permission(role: UserRole, permission: Permission) -> bool:
    """Return whether a role grants the requested permission."""
    return permission in ROLE_PERMISSIONS[role]
