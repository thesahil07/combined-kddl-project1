from fastapi.testclient import TestClient

from app.domain.entities.user import User, UserStatus
from app.domain.value_objects.role import Role
from app.infrastructure.security.password_hasher import PasswordHasher
from app.infrastructure.security.token_service import TokenService
from app.main import app
from app.presentation.api.dependencies import TenantScope, get_token_service, get_user_repository
from app.presentation.api.dependencies import get_employee_workspace_use_case
from tests.test_auth import FakeUsers


def _client_for(user: User) -> TestClient:
    app.dependency_overrides[get_user_repository] = lambda: FakeUsers(user, PasswordHasher().hash("password"))
    app.dependency_overrides[get_token_service] = lambda: TokenService("rbac-secret", 30)
    return TestClient(app)


def _headers(user: User) -> dict[str, str]:
    token = TokenService("rbac-secret", 30).issue(user)
    return {"Authorization": f"Bearer {token}"}


def test_tenant_scope_filters_cross_tenant_and_division_records() -> None:
    records = [
        {"tenant_id": 1, "division_id": 2, "employee_id": 1},
        {"tenant_id": 1, "division_id": 3, "employee_id": 2},
        {"tenant_id": 2, "division_id": 2, "employee_id": 3},
    ]
    assert TenantScope(1, None, False).filter_records(records) == records[:2]
    assert TenantScope(1, 2, False).filter_records(records) == records[:1]


def test_admin_and_employee_routes_enforce_role_and_scope() -> None:
    admin = User(1, None, "admin@example.com", Role.PGC_ADMIN, None, None, UserStatus.ACTIVE)
    employee = User(2, 1, "employee@example.com", Role.EMPLOYEE, None, None, UserStatus.ACTIVE)
    client = _client_for(admin)
    assert client.get("/api/v1/admin/tenants", headers=_headers(admin)).status_code == 200
    client.close()
    client = _client_for(employee)
    assert client.get("/api/v1/admin/tenants", headers=_headers(employee)).status_code == 403
    response = client.get("/api/v1/employees", headers=_headers(employee))
    assert response.status_code == 200
    assert response.json()["tenant_id"] == 1
    client.close()
    app.dependency_overrides.clear()


def test_ks_generation_is_exclusively_pgc_admin() -> None:
    roles = list(Role)
    admin = User(1, None, "admin@example.com", Role.PGC_ADMIN, None, None, UserStatus.ACTIVE)
    client = _client_for(admin)
    assert client.get("/api/v1/admin/ks-generation/ping", headers=_headers(admin)).status_code == 200
    client.close()
    for index, role in enumerate(roles):
        if role is Role.PGC_ADMIN:
            continue
        user = User(index + 2, 1, f"{role.value}@example.com", role, None, 2 if role is Role.HR_SPOC else None, UserStatus.ACTIVE)
        client = _client_for(user)
        assert client.get("/api/v1/admin/ks-generation/ping", headers=_headers(user)).status_code == 403
        client.close()
    app.dependency_overrides.clear()


def test_unauthenticated_role_protected_endpoint_is_401() -> None:
    user = User(1, None, "admin@example.com", Role.PGC_ADMIN, None, None, UserStatus.ACTIVE)
    client = _client_for(user)
    assert client.get("/api/v1/admin/tenants").status_code == 401
    client.close()
    app.dependency_overrides.clear()


def test_employee_workspace_is_limited_to_the_authenticated_employee() -> None:
    class FakeEmployeeWorkspace:
        def dashboard(self, tenant_id: int, employee_id: int) -> dict[str, object]:
            return {"tenant_id": tenant_id, "employee_id": employee_id}

    employee = User(2, 1, "employee@example.com", Role.EMPLOYEE, 8, None, UserStatus.ACTIVE)
    manager = User(3, 1, "manager@example.com", Role.HOD_MANAGER, 9, None, UserStatus.ACTIVE)
    client = _client_for(employee)
    app.dependency_overrides[get_employee_workspace_use_case] = lambda: FakeEmployeeWorkspace()
    response = client.get("/api/v1/employee/dashboard", headers=_headers(employee))
    assert response.status_code == 200
    assert response.json() == {"tenant_id": 1, "employee_id": 8}
    client.close()
    client = _client_for(manager)
    app.dependency_overrides[get_employee_workspace_use_case] = lambda: FakeEmployeeWorkspace()
    response = client.get("/api/v1/employee/dashboard", headers=_headers(manager))
    assert response.status_code == 200
    assert response.json() == {"tenant_id": 1, "employee_id": 9}
    client.close()
    app.dependency_overrides.clear()
    
