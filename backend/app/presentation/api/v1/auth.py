"""Authentication HTTP adapter."""

from fastapi import APIRouter, Depends, HTTPException, status

from app.application.dtos.auth_dtos import ChangePasswordRequest, LoginRequest, LoginResponse
from app.application.use_cases.change_password import ChangePasswordUseCase
from app.application.use_cases.login import LoginUseCase
from app.domain.entities.user import User
from app.presentation.api.dependencies import get_change_password_use_case, get_current_user, get_login_use_case

router = APIRouter(tags=["auth"])

@router.post("/login", response_model=LoginResponse)
def login(payload: LoginRequest, use_case: LoginUseCase = Depends(get_login_use_case)) -> LoginResponse:
    result = use_case.execute(payload.email, payload.password)
    if not result.succeeded:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid credentials")
    return LoginResponse(access_token=result.access_token or "")


@router.post("/change-password")
def change_password(
    payload: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    use_case: ChangePasswordUseCase = Depends(get_change_password_use_case),
) -> dict[str, str]:
    if not use_case.execute(current_user, payload.current_password, payload.new_password):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "current password is invalid or new password matches it")
    return {"message": "Password changed. Please sign in again."}
