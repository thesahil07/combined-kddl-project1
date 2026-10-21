"""The sole presentation-layer wiring point for infrastructure services."""

from collections.abc import Generator

from dataclasses import dataclass
from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import Engine, create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from app.config import settings
from app.application.use_cases.login import LoginUseCase
from app.application.use_cases.change_password import ChangePasswordUseCase
from app.application.use_cases.get_admin_console import GetAdminConsoleUseCase
from app.application.use_cases.get_executive_review import GetExecutiveReviewUseCase
from app.domain.entities.user import User, UserStatus
from app.domain.value_objects.role import Role
from app.domain.interfaces.user_repository import UserRepository
from app.infrastructure.repositories.user_repository_impl import SqlAlchemyUserRepository
from app.infrastructure.security.password_hasher import PasswordHasher
from app.infrastructure.security.token_service import InvalidTokenError, TokenService
from app.infrastructure.database.models.module_b import EmployeeModel, TenantModel
from app.infrastructure.database.models.tenancy_identity import AdminConsoleAccessModel, ExecutiveReviewAccessModel
from app.infrastructure.repositories.role_description_repository_impl import SqlAlchemyRoleDescriptionRepository
from app.infrastructure.repositories.role_repository_impl import SqlAlchemyRoleRepository
from app.infrastructure.external_services.ai_gateway import UnavailableRoleDescriptionAIGateway
from app.infrastructure.external_services.role_description_refiner import RoleDescriptionRefiner
from app.application.use_cases.create_role import CreateRoleUseCase
from app.application.use_cases.save_role_description import SaveRoleDescriptionUseCase
from app.application.use_cases.validate_role_description import ValidateRoleDescriptionUseCase
from app.application.use_cases.refine_role_description import RefineRoleDescriptionUseCase
from app.application.use_cases.list_roles import ListRolesUseCase
from app.application.use_cases.get_skip_manager_dashboard import GetSkipManagerDashboardUseCase
from app.application.use_cases.submit_role_description import SubmitRoleDescriptionUseCase
from app.application.use_cases.save_manager_assessment import SaveManagerAssessmentUseCase
from app.infrastructure.repositories.skip_manager_dashboard_repository_impl import SqlAlchemySkipManagerDashboardRepository
from app.infrastructure.repositories.employee_workspace_repository_impl import SqlAlchemyEmployeeWorkspaceRepository
from app.infrastructure.repositories.admin_console_repository_impl import SqlAlchemyAdminConsoleRepository
from app.infrastructure.repositories.executive_review_repository_impl import SqlAlchemyExecutiveReviewRepository
from app.infrastructure.repositories.assessment_notification_repository_impl import SqlAlchemyAssessmentNotificationRepository
from app.infrastructure.external_services.smtp_email_sender import SmtpEmailSender
from app.application.services.assessment_submission_notifier import AssessmentSubmissionNotifier
from app.application.use_cases.get_employee_workspace import GetEmployeeWorkspaceUseCase
from app.application.use_cases.start_employee_assessment import StartEmployeeAssessmentUseCase
from app.application.use_cases.save_employee_assessment import SaveEmployeeAssessmentUseCase
from app.domain.exceptions.application_errors import AuthorizationError

_bearer = HTTPBearer(auto_error=False)
_engine: Engine | None = None


def initialize_database_engine() -> None:
    global _engine
    if not settings.database_url:
        return
    _engine = create_engine(settings.database_url, pool_pre_ping=True)


def dispose_database_engine() -> None:
    global _engine
    if _engine is not None:
        _engine.dispose()
        _engine = None
def get_session() -> Generator[Session, None, None]:
    if _engine is None:
        raise RuntimeError("DATABASE_URL must be configured.")
    session = sessionmaker(bind=_engine)()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_user_repository(session: Session = Depends(get_session)) -> UserRepository:
    return SqlAlchemyUserRepository(session)


def get_role_repository(session: Session = Depends(get_session)) -> SqlAlchemyRoleRepository:
    return SqlAlchemyRoleRepository(session)


def get_role_description_repository(session: Session = Depends(get_session)) -> SqlAlchemyRoleDescriptionRepository:
    return SqlAlchemyRoleDescriptionRepository(session)


def get_create_role_use_case(roles: SqlAlchemyRoleRepository = Depends(get_role_repository)) -> CreateRoleUseCase:
    return CreateRoleUseCase(roles)


def get_save_role_description_use_case(
    roles: SqlAlchemyRoleRepository = Depends(get_role_repository),
    descriptions: SqlAlchemyRoleDescriptionRepository = Depends(get_role_description_repository),
) -> SaveRoleDescriptionUseCase:
    return SaveRoleDescriptionUseCase(descriptions, roles)


def get_submit_role_description_use_case(
    save_draft: SaveRoleDescriptionUseCase = Depends(get_save_role_description_use_case),
    roles: SqlAlchemyRoleRepository = Depends(get_role_repository),
) -> SubmitRoleDescriptionUseCase:
    return SubmitRoleDescriptionUseCase(save_draft, roles)


def get_validate_role_description_use_case(
    roles: SqlAlchemyRoleRepository = Depends(get_role_repository),
    descriptions: SqlAlchemyRoleDescriptionRepository = Depends(get_role_description_repository),
) -> ValidateRoleDescriptionUseCase:
    return ValidateRoleDescriptionUseCase(descriptions, roles)


def get_role_description_refiner() -> RoleDescriptionRefiner:
    return RoleDescriptionRefiner(UnavailableRoleDescriptionAIGateway())


def get_list_roles_use_case(roles: SqlAlchemyRoleRepository = Depends(get_role_repository)) -> ListRolesUseCase:
    return ListRolesUseCase(roles)


def get_skip_manager_dashboard_use_case(
    session: Session = Depends(get_session),
) -> GetSkipManagerDashboardUseCase:
    return GetSkipManagerDashboardUseCase(SqlAlchemySkipManagerDashboardRepository(session))


def get_executive_review_use_case(
    session: Session = Depends(get_session),
) -> GetExecutiveReviewUseCase:
    return GetExecutiveReviewUseCase(SqlAlchemyExecutiveReviewRepository(session))


def get_save_manager_assessment_use_case(
    session: Session = Depends(get_session),
) -> SaveManagerAssessmentUseCase:
    notifier = AssessmentSubmissionNotifier(
        SqlAlchemyAssessmentNotificationRepository(session), SmtpEmailSender(session),
    )
    return SaveManagerAssessmentUseCase(
        SqlAlchemySkipManagerDashboardRepository(session), notifier,
    )


def get_employee_workspace_repository(
    session: Session = Depends(get_session),
) -> SqlAlchemyEmployeeWorkspaceRepository:
    return SqlAlchemyEmployeeWorkspaceRepository(session)


def get_employee_workspace_use_case(
    repository: SqlAlchemyEmployeeWorkspaceRepository = Depends(get_employee_workspace_repository),
) -> GetEmployeeWorkspaceUseCase:
    return GetEmployeeWorkspaceUseCase(repository)


def get_start_employee_assessment_use_case(
    repository: SqlAlchemyEmployeeWorkspaceRepository = Depends(get_employee_workspace_repository),
) -> StartEmployeeAssessmentUseCase:
    return StartEmployeeAssessmentUseCase(repository)


def get_save_employee_assessment_use_case(
    repository: SqlAlchemyEmployeeWorkspaceRepository = Depends(get_employee_workspace_repository),
    session: Session = Depends(get_session),
) -> SaveEmployeeAssessmentUseCase:
    notifier = AssessmentSubmissionNotifier(
        SqlAlchemyAssessmentNotificationRepository(session), SmtpEmailSender(session),
    )
    return SaveEmployeeAssessmentUseCase(repository, notifier)


def get_refine_role_description_use_case(
    descriptions: SqlAlchemyRoleDescriptionRepository = Depends(get_role_description_repository),
    refiner: RoleDescriptionRefiner = Depends(get_role_description_refiner),
) -> RefineRoleDescriptionUseCase:
    return RefineRoleDescriptionUseCase(descriptions, refiner)


def get_token_service() -> TokenService:
    secret, expiry = settings.require_jwt_settings()
    return TokenService(secret, expiry)


def get_login_use_case(
    users: UserRepository = Depends(get_user_repository),
    tokens: TokenService = Depends(get_token_service),
) -> LoginUseCase:
    return LoginUseCase(users, PasswordHasher(), tokens)


def get_change_password_use_case(
    users: UserRepository = Depends(get_user_repository),
) -> ChangePasswordUseCase:
    return ChangePasswordUseCase(users, PasswordHasher())


def get_admin_console_use_case(session: Session = Depends(get_session)) -> GetAdminConsoleUseCase:
    return GetAdminConsoleUseCase(SqlAlchemyAdminConsoleRepository(session))


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    users: UserRepository = Depends(get_user_repository),
    tokens: TokenService = Depends(get_token_service),
) -> User:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid authentication credentials")
    try:
        claims = tokens.verify(credentials.credentials)
        user_id = int(str(claims["sub"]))
    except (InvalidTokenError, KeyError, ValueError):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid authentication credentials") from None
    user = users.get_by_id(user_id)
    if user is None or user.status is not UserStatus.ACTIVE:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid authentication credentials")
    return user


def require_role(*allowed_roles: Role):
    """Compose with routes as ``Depends(require_role(Role.HR_SPOC))``."""
    if not allowed_roles:
        raise ValueError("at least one allowed role is required")

    def dependency(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed_roles:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "forbidden")
        return current_user

    return dependency


@dataclass(frozen=True, slots=True)
class TenantScope:
    """Trusted, server-derived filter for every tenant-scoped query.

    Future routes combine e.g. ``Depends(require_role(Role.HR_SPOC))``
    with ``Depends(require_tenant_scope)`` and pass this scope to their
    application use case/repository. Never take tenant_id from a route.
    """

    tenant_id: int | None
    division_scope_id: int | None
    is_platform_admin: bool

    def filter_records(self, records: list[dict[str, object]]) -> list[dict[str, object]]:
        if self.is_platform_admin:
            return records
        return [
            record for record in records
            if record.get("tenant_id") == self.tenant_id
            and (self.division_scope_id is None or record.get("division_id") == self.division_scope_id)
        ]


@dataclass(frozen=True, slots=True)
class SkipManagerScope:
    """Trusted request context for the Skip Manager workspace."""

    tenant_id: int
    manager_employee_id: int
    user_id: int


@dataclass(frozen=True, slots=True)
class EmployeeScope:
    """Trusted request context for the signed-in employee's own records."""

    tenant_id: int
    employee_id: int
    user_id: int


def require_admin_console_access(
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> TenantScope:
    if current_user.tenant_id is None:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "tenant-scoped access is required")
    permitted = current_user.role is Role.HR_SPOC or session.scalar(
        select(AdminConsoleAccessModel.access_id).where(
            AdminConsoleAccessModel.tenant_id == current_user.tenant_id,
            AdminConsoleAccessModel.user_id == current_user.user_id,
        )
    ) is not None
    if not permitted:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "admin console access has not been granted")
    return TenantScope(current_user.tenant_id, current_user.division_scope_id, False)


def require_executive_review_access(
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> TenantScope:
    if current_user.role is Role.PGC_ADMIN:
        return TenantScope(current_user.tenant_id or 1, None, True)
    if current_user.tenant_id is None:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "tenant-scoped access is required")
    permitted = session.scalar(select(ExecutiveReviewAccessModel.access_id).where(
        ExecutiveReviewAccessModel.tenant_id == current_user.tenant_id,
        ExecutiveReviewAccessModel.user_id == current_user.user_id,
    )) is not None
    if not permitted and current_user.role is not Role.SPONSOR_VIEWER:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "executive review access has not been granted")
    return TenantScope(current_user.tenant_id, current_user.division_scope_id, False)


def require_tenant_scope(current_user: User = Depends(get_current_user)) -> TenantScope:
    if current_user.role is Role.PGC_ADMIN:
        return TenantScope(None, None, True)
    if current_user.tenant_id is None:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "tenant scope unavailable")
    division_scope = current_user.division_scope_id if current_user.role is Role.HR_SPOC else None
    return TenantScope(current_user.tenant_id, division_scope, False)


def require_skip_manager_scope(
    current_user: User = Depends(get_current_user),
    scope: TenantScope = Depends(require_tenant_scope),
    session: Session = Depends(get_session),
) -> SkipManagerScope:
    if scope.tenant_id is None or current_user.employee_id is None:
        raise AuthorizationError("manager employee profile is required")
    has_direct_reports = session.scalar(
        select(EmployeeModel.employee_id).where(
            EmployeeModel.tenant_id == scope.tenant_id,
            EmployeeModel.manager_employee_id == current_user.employee_id,
            EmployeeModel.status == "ACTIVE",
        ).limit(1)
    )
    if has_direct_reports is None:
        raise AuthorizationError("manager workspace requires at least one active direct report")
    return SkipManagerScope(scope.tenant_id, current_user.employee_id, current_user.user_id)


def require_employee_scope(
    current_user: User = Depends(get_current_user),
    scope: TenantScope = Depends(require_tenant_scope),
) -> EmployeeScope:
    if scope.tenant_id is None or current_user.employee_id is None:
        raise AuthorizationError("employee profile is required")
    return EmployeeScope(scope.tenant_id, current_user.employee_id, current_user.user_id)


def require_target_tenant_scope(
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
    target_tenant_id: int | None = Header(default=None, alias="X-Target-Tenant-ID"),
) -> TenantScope:
    """Uses server identity; PGC must explicitly select a real tenant."""
    if current_user.role is not Role.PGC_ADMIN:
        return require_tenant_scope(current_user)
    if target_tenant_id is None or session.get(TenantModel, target_tenant_id) is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "a valid target tenant is required")
    return TenantScope(target_tenant_id, None, False)
