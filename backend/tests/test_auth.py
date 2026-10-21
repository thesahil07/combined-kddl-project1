from datetime import datetime, timedelta, timezone

import jwt
from fastapi.testclient import TestClient

from app.domain.entities.user import User, UserRole, UserStatus
from app.domain.interfaces.user_repository import UserRepository
from app.application.use_cases.login import LoginUseCase
from app.infrastructure.security.password_hasher import PasswordHasher
from app.infrastructure.security.token_service import InvalidTokenError, TokenService
from app.main import app
from app.presentation.api.dependencies import get_token_service, get_user_repository


class FakeUsers(UserRepository):
    def __init__(self, user: User, password_hash: str) -> None:
        self.user, self.password_hash, self.last_login = user, password_hash, None

    def get_by_email(self, email: str) -> tuple[User, str] | None:
        return (self.user, self.password_hash) if email == self.user.email else None

    def get_by_id(self, user_id: int) -> User | None:
        return self.user if user_id == self.user.user_id else None

    def create(self, user: User, password_hash: str) -> User:
        self.user, self.password_hash = user, password_hash
        return user

    def update_last_login(self, user_id: int) -> None:
        self.last_login = user_id


def test_password_hasher_never_returns_plaintext() -> None:
    hasher = PasswordHasher()
    hashed = hasher.hash("safe-password")
    assert hashed != "safe-password"
    assert hasher.verify("safe-password", hashed)
    assert not hasher.verify("wrong-password", hashed)


def test_token_rejects_expiry_and_tampering() -> None:
    tokens = TokenService("test-secret", 1)
    user = User(1, 10, "user@example.com", UserRole.EMPLOYEE, None, None, UserStatus.ACTIVE)
    valid = tokens.issue(user)
    assert tokens.verify(valid)["sub"] == "1"
    expired = jwt.encode({"sub": "1", "exp": datetime.now(timezone.utc) - timedelta(seconds=1)}, "test-secret", algorithm="HS256")
    for token in (expired, valid + "x"):
        try:
            tokens.verify(token)
            assert False, "invalid token must be rejected"
        except InvalidTokenError:
            pass


def test_login_use_case_handles_success_and_all_generic_failures() -> None:
    user = User(1, 10, "user@example.com", UserRole.EMPLOYEE, None, None, UserStatus.ACTIVE)
    users = FakeUsers(user, PasswordHasher().hash("correct-password"))
    use_case = LoginUseCase(users, PasswordHasher(), TokenService("test-secret", 30))
    assert use_case.execute(user.email, "correct-password").succeeded
    assert not use_case.execute(user.email, "wrong-password").succeeded
    assert not use_case.execute("unknown@example.com", "wrong-password").succeeded
    disabled = User(1, 10, user.email, UserRole.EMPLOYEE, None, None, UserStatus.DISABLED)
    disabled_use_case = LoginUseCase(FakeUsers(disabled, users.password_hash), PasswordHasher(), TokenService("test-secret", 30))
    assert not disabled_use_case.execute(user.email, "correct-password").succeeded


def test_login_and_authenticated_me_end_to_end() -> None:
    from unittest.mock import MagicMock
    from app.presentation.api.dependencies import get_session

    user = User(1, 10, "user@example.com", UserRole.EMPLOYEE, 7, None, UserStatus.ACTIVE)
    users = FakeUsers(user, PasswordHasher().hash("correct-password"))
    mock_session = MagicMock()
    mock_session.scalar.return_value = None
    app.dependency_overrides[get_session] = lambda: mock_session
    app.dependency_overrides[get_user_repository] = lambda: users
    app.dependency_overrides[get_token_service] = lambda: TokenService("test-secret", 30)
    client = TestClient(app)
    login = client.post("/api/v1/auth/login", json={"email": user.email, "password": "correct-password"})
    assert login.status_code == 200
    token = login.json()["access_token"]
    profile = client.get("/api/v1/me", headers={"Authorization": f"Bearer {token}"})
    assert profile.status_code == 200
    assert profile.json()["email"] == user.email
    assert client.get("/api/v1/me").status_code == 401
    assert client.get("/api/v1/me", headers={"Authorization": "Bearer garbage"}).status_code == 401
    client.close()
    app.dependency_overrides.clear()


def test_login_failures_are_generic_and_rate_limited() -> None:
    from app.infrastructure.security.rate_limiter import InMemoryRateLimiter

    user = User(1, 10, "user@example.com", UserRole.EMPLOYEE, None, None, UserStatus.ACTIVE)
    users = FakeUsers(user, PasswordHasher().hash("correct-password"))
    app.dependency_overrides[get_user_repository] = lambda: users
    app.dependency_overrides[get_token_service] = lambda: TokenService("test-secret", 30)
    app.state.rate_limiter = InMemoryRateLimiter(limit=5)
    client = TestClient(app)
    for payload in ({"email": user.email, "password": "wrong"}, {"email": "none@example.com", "password": "wrong"}):
        response = client.post("/api/v1/auth/login", json=payload)
        assert response.status_code == 401
        assert response.json()["detail"] == "invalid credentials"
    for _ in range(3):
        assert client.post("/api/v1/auth/login", json={"email": user.email, "password": "wrong"}).status_code == 401
    assert client.post("/api/v1/auth/login", json={"email": user.email, "password": "wrong"}).status_code == 429
    client.close()
    app.dependency_overrides.clear()
