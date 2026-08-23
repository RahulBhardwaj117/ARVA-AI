"""User persistence operations."""

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.models.user import User


class UserRepository:
    """Encapsulate user queries behind a small persistence boundary."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def get_by_email(self, email: str) -> User | None:
        """Return an active or inactive user by normalized email."""
        statement = (
            select(User)
            .options(joinedload(User.organization))
            .where(User.email == email.strip().lower())
        )
        return self.session.scalar(statement)

    def get_by_id(self, user_id: uuid.UUID) -> User | None:
        """Return a user and its organization by primary key."""
        statement = (
            select(User)
            .options(joinedload(User.organization))
            .where(User.id == user_id)
        )
        return self.session.scalar(statement)

