"""Typed ORM mappings used by Module B import workflows."""

from datetime import date, datetime
from typing import Any

from sqlalchemy import BigInteger, Boolean, Date, DateTime, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database.models.base import Base


class TenantModel(Base):
    __tablename__ = "tenants"
    tenant_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    client_name: Mapped[str] = mapped_column(String(150))


class EntityModel(Base):
    __tablename__ = "entities"
    entity_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    tenant_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("tenants.tenant_id"))
    name: Mapped[str] = mapped_column(String(100))
    code: Mapped[str] = mapped_column(String(20))


class DivisionModel(Base):
    __tablename__ = "divisions"
    division_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    tenant_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("tenants.tenant_id"))
    entity_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("entities.entity_id"))
    name: Mapped[str] = mapped_column(String(100))


class GradeBandModel(Base):
    __tablename__ = "grade_bands"
    grade_band_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    tenant_id: Mapped[int] = mapped_column(BigInteger)
    band_code: Mapped[str] = mapped_column(String(10))


class FunctionModel(Base):
    __tablename__ = "functions"
    function_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    tenant_id: Mapped[int] = mapped_column(BigInteger)
    division_id: Mapped[int] = mapped_column(BigInteger)
    name: Mapped[str] = mapped_column(String(100))


class DepartmentModel(Base):
    __tablename__ = "departments"
    department_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    tenant_id: Mapped[int] = mapped_column(BigInteger)
    division_id: Mapped[int] = mapped_column(BigInteger)
    function_id: Mapped[int] = mapped_column(BigInteger)
    name: Mapped[str] = mapped_column(String(100))


class RoleModel(Base):
    __tablename__ = "roles"
    role_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    tenant_id: Mapped[int] = mapped_column(BigInteger)
    division_id: Mapped[int] = mapped_column(BigInteger)
    function_id: Mapped[int] = mapped_column(BigInteger)
    title: Mapped[str] = mapped_column(String(150))
    description_status: Mapped[str] = mapped_column(String(20), default="NOT_STARTED")


class RoleDescriptionModel(Base):
    __tablename__ = "role_descriptions"
    role_description_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    role_id: Mapped[int] = mapped_column(BigInteger)
    version: Mapped[int] = mapped_column(Integer)
    people_count: Mapped[int | None] = mapped_column(Integer)
    role_definition: Mapped[str] = mapped_column(Text)
    key_responsibilities: Mapped[str] = mapped_column(Text)
    kpis: Mapped[str] = mapped_column(Text)
    education_certifications: Mapped[str] = mapped_column(Text)
    minimum_relevant_experience: Mapped[str] = mapped_column(Text)
    knowledge_required: Mapped[str] = mapped_column(Text)
    skills_required: Mapped[str] = mapped_column(Text)
    attitudes_behaviours: Mapped[str] = mapped_column(Text)
    specifications_experience: Mapped[str] = mapped_column(Text)
    equipment_process_refs: Mapped[str | None] = mapped_column(Text)
    ai_refined: Mapped[bool] = mapped_column(Boolean, default=False)
    validated_by_employee_id: Mapped[int | None] = mapped_column(BigInteger)
    validated_at: Mapped[datetime | None] = mapped_column(DateTime)


class EmployeeModel(Base):
    __tablename__ = "employees"
    employee_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    tenant_id: Mapped[int] = mapped_column(BigInteger)
    division_id: Mapped[int] = mapped_column(BigInteger)
    employee_code: Mapped[str] = mapped_column(String(30))
    full_name: Mapped[str] = mapped_column(String(150))
    grade_band_id: Mapped[int] = mapped_column(BigInteger)
    designation: Mapped[str] = mapped_column(String(100))
    function_id: Mapped[int] = mapped_column(BigInteger)
    department_id: Mapped[int | None] = mapped_column(BigInteger)
    role_id: Mapped[int | None] = mapped_column(BigInteger)
    manager_employee_id: Mapped[int | None] = mapped_column(BigInteger)
    date_of_birth: Mapped[date | None] = mapped_column(Date)
    tenure_start_date: Mapped[date | None] = mapped_column(Date)
    qualification: Mapped[str | None] = mapped_column(String(150))
    date_of_joining: Mapped[date | None] = mapped_column(Date)
    last_promotion_date: Mapped[date | None] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(20))
    name_collision_flag: Mapped[bool] = mapped_column(Boolean, default=False)


class EmployeeUploadBatchModel(Base):
    __tablename__ = "employee_upload_batches"
    batch_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    tenant_id: Mapped[int] = mapped_column(BigInteger)
    uploaded_by_user_id: Mapped[int] = mapped_column(BigInteger)
    status: Mapped[str] = mapped_column(String(20))
    rejection_reason: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime)
    published_at: Mapped[datetime | None] = mapped_column(DateTime)


class EmployeeUploadRowModel(Base):
    __tablename__ = "employee_upload_rows"
    upload_row_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    batch_id: Mapped[int] = mapped_column(BigInteger)
    row_number: Mapped[int] = mapped_column(Integer)
    employee_code: Mapped[str | None] = mapped_column(String(30))
    raw_json: Mapped[dict[str, Any]] = mapped_column(JSON)
    validation_error: Mapped[str | None] = mapped_column(Text)
    accepted: Mapped[bool] = mapped_column(Boolean)
    staged_role_title: Mapped[str | None] = mapped_column(String(150))
