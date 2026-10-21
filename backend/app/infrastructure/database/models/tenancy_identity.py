"""ORM home for tenants, divisions, and users."""

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Enum, String
from sqlalchemy.orm import Mapped, mapped_column

from app.domain.entities.user import UserRole, UserStatus
from app.infrastructure.database.models.base import Base


class UserModel(Base):
    """Mapping used by authentication; full schema is created by Alembic DDL."""

    __tablename__ = "users"
    user_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    tenant_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    email: Mapped[str] = mapped_column(String(150), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(Enum(UserRole), nullable=False)
    employee_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    division_scope_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    status: Mapped[UserStatus] = mapped_column(Enum(UserStatus), nullable=False)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class AdminConsoleAccessModel(Base):
    __tablename__ = "admin_console_access"
    access_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    tenant_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False)


class ExecutiveReviewAccessModel(Base):
    """Explicit grant for the tenant-wide Executive Review dashboard."""

    __tablename__ = "executive_review_access"
    access_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    tenant_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
