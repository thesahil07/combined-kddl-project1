"""Fixed platform roles; no generic administrator role exists."""

from enum import StrEnum


class Role(StrEnum):
    PGC_ADMIN = "PGC_ADMIN"
    HR_SPOC = "HR_SPOC"
    HOD_MANAGER = "HOD_MANAGER"
    EMPLOYEE = "EMPLOYEE"
    SKIP_MANAGER = "SKIP_MANAGER"
    SPONSOR_VIEWER = "SPONSOR_VIEWER"
