"""Empty API router reserved for future v1 endpoints."""

from fastapi import APIRouter

from app.presentation.api.v1.auth import router as auth_router
from app.presentation.api.v1.me import router as me_router
from app.presentation.api.v1.rbac_examples import router as rbac_examples_router
from app.presentation.api.v1.roles import router as roles_router
from app.presentation.api.v1.skip_manager import router as skip_manager_router
from app.presentation.api.v1.employee import router as employee_router
from app.presentation.api.v1.admin_console import router as admin_console_router
from app.presentation.api.v1.executive_review import router as executive_review_router

router = APIRouter()
# Route prefixes are owned here, at the v1 composition boundary.  Individual
# controllers define resource operations only, keeping the public URI shape
# consistent across modules.
router.include_router(auth_router, prefix="/auth")
router.include_router(me_router)
router.include_router(rbac_examples_router)
router.include_router(roles_router, prefix="/roles")
router.include_router(skip_manager_router, prefix="/skip-manager")
router.include_router(employee_router, prefix="/employee")
router.include_router(admin_console_router, prefix="/admin-console")
router.include_router(executive_review_router, prefix="/executive-review")
