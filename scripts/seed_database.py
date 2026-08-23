"""Create the deterministic complete ARVA demo environment."""

from app.auth.passwords import hash_password
from app.config import get_settings
from app.database.session import SessionLocal
from app.models.organization import DeploymentMode, Organization
from app.models.user import User, UserRole
from app.services.platform import seed_environment
from sqlalchemy import select


def seed() -> None:
    """Insert or update six role users and the persistent digital twin."""
    settings = get_settings()
    with SessionLocal.begin() as session:
        organization = session.scalar(
            select(Organization).where(Organization.slug == "arva-labs")
        )
        if organization is None:
            organization = Organization(
                name=settings.demo_organization,
                slug="arva-labs",
                deployment_mode=DeploymentMode.SIMULATION,
                timezone="Asia/Calcutta",
            )
            session.add(organization)
            session.flush()

        users = [
            ("ARVA Administrator", settings.demo_admin_email.lower(), UserRole.ADMINISTRATOR),
            (
                "Infrastructure Operator",
                "operator@arva.local",
                UserRole.INFRASTRUCTURE_OPERATOR,
            ),
            ("AI Engineer", "engineer@arva.local", UserRole.AI_ENGINEER),
            ("Research Scientist", "researcher@arva.local", UserRole.RESEARCHER),
            ("Platform Viewer", "viewer@arva.local", UserRole.VIEWER),
            ("Compliance Auditor", "auditor@arva.local", UserRole.AUDITOR),
        ]
        for name, email, role in users:
            account = session.scalar(
                select(User).where(
                    User.organization_id == organization.id,
                    User.email == email,
                )
            )
            if account is None:
                account = User(
                    organization_id=organization.id,
                    name=name,
                    email=email,
                    password_hash=hash_password(settings.demo_admin_password),
                    role=role,
                    is_active=True,
                )
                session.add(account)
            else:
                account.name = name
                account.password_hash = hash_password(settings.demo_admin_password)
                account.role = role
                account.is_active = True

        seed_environment(session, organization)

    print(
        "Seed complete: 3 clusters, 15 nodes, 3 GPU profiles, 3 teams, "
        f"200 workloads and six users. Administrator: {settings.demo_admin_email}"
    )


if __name__ == "__main__":
    seed()
