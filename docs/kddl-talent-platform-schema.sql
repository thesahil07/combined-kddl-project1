-- ============================================================================
-- KDDL Dials Talent Transformation Platform — Database Schema (MySQL 8.x)
-- ============================================================================
-- Assumption: this schema follows the same conventions used on the CXO Compass
-- build (multi-tenant via a tenant_id column on every table, a single scoring/
-- line-item table with a discriminator column rather than parallel tables per
-- item type, and dedicated tables per role instead of a generic users/role flag
-- where the role carries meaningfully different fields). Confirm tech stack
-- (MySQL vs. another engine) before treating this as final — see the
-- accompanying Technical Design Document, Section 1.
--
-- Naming: PGC = Planet Ganges Consulting (platform operator, one tenant per
-- client, KDDL is the first tenant). snake_case throughout. Every business
-- table carries tenant_id for isolation; cross-tenant queries must never be
-- possible at the application layer even for PGC_ADMIN (see TDD Section 6).
-- ============================================================================

SET FOREIGN_KEY_CHECKS = 0;

-- ----------------------------------------------------------------------------
-- 1. TENANCY & IDENTITY
-- ----------------------------------------------------------------------------

CREATE TABLE tenants (
  tenant_id        BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  client_name       VARCHAR(150) NOT NULL,
  status            ENUM('ACTIVE','SUSPENDED') NOT NULL DEFAULT 'ACTIVE',
  created_at        DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at        DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB;

CREATE TABLE entities (
  entity_id         BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  tenant_id         BIGINT UNSIGNED NOT NULL,
  name              VARCHAR(100) NOT NULL,
  code              VARCHAR(20) NOT NULL,
  created_at        DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_entities_tenant FOREIGN KEY (tenant_id) REFERENCES tenants(tenant_id),
  UNIQUE KEY uq_entity_code (tenant_id, code)
) ENGINE=InnoDB;

CREATE TABLE divisions (
  division_id       BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  tenant_id         BIGINT UNSIGNED NOT NULL,
  entity_id         BIGINT UNSIGNED NOT NULL,
  name              VARCHAR(100) NOT NULL,           -- e.g. 'Dials 1 - Parwanoo', 'Dials 2 - Derabassi'
  code              VARCHAR(20)  NOT NULL,
  created_at        DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_divisions_tenant FOREIGN KEY (tenant_id) REFERENCES tenants(tenant_id),
  CONSTRAINT fk_divisions_entity FOREIGN KEY (entity_id) REFERENCES entities(entity_id),
  UNIQUE KEY uq_division_code (tenant_id, code)
) ENGINE=InnoDB;

CREATE TABLE users (
  user_id           BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  tenant_id         BIGINT UNSIGNED NULL,             -- NULL for PGC_ADMIN (cross-tenant operator account)
  email             VARCHAR(150) NOT NULL,
  password_hash     VARCHAR(255) NOT NULL,
  role              ENUM('PGC_ADMIN','HR_SPOC','HOD_MANAGER','EMPLOYEE','SKIP_MANAGER','SPONSOR_VIEWER') NOT NULL,
  employee_id       BIGINT UNSIGNED NULL,             -- set for roles that map to a person record (see employees FK added below)
  division_scope_id BIGINT UNSIGNED NULL,             -- for HR_SPOC: restricts to one division; NULL = all divisions in tenant
  status            ENUM('ACTIVE','DISABLED') NOT NULL DEFAULT 'ACTIVE',
  last_login_at     DATETIME NULL,
  created_at        DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_users_tenant FOREIGN KEY (tenant_id) REFERENCES tenants(tenant_id),
  CONSTRAINT fk_users_division FOREIGN KEY (division_scope_id) REFERENCES divisions(division_id),
  UNIQUE KEY uq_users_email (email)
) ENGINE=InnoDB;

-- Confidential: explicit, tenant-scoped grants for the read-only Executive Review dashboard.
CREATE TABLE executive_review_access (
  access_id         BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  tenant_id         BIGINT UNSIGNED NOT NULL,
  user_id           BIGINT UNSIGNED NOT NULL,
  granted_by_user_id BIGINT UNSIGNED NULL,
  created_at        DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_executive_review_access_tenant FOREIGN KEY (tenant_id) REFERENCES tenants(tenant_id),
  CONSTRAINT fk_executive_review_access_user FOREIGN KEY (user_id) REFERENCES users(user_id),
  CONSTRAINT fk_executive_review_access_granted_by FOREIGN KEY (granted_by_user_id) REFERENCES users(user_id),
  UNIQUE KEY uq_executive_review_access_user (tenant_id, user_id)
) ENGINE=InnoDB;

-- ----------------------------------------------------------------------------
-- 2. ORG, GRADE & FUNCTION REFERENCE DATA
-- ----------------------------------------------------------------------------

CREATE TABLE grade_bands (
  grade_band_id     BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  tenant_id         BIGINT UNSIGNED NOT NULL,
  band_code         VARCHAR(10) NOT NULL,             -- S3, E1..E4, M1..M4, LM1, LM2, A1..A3, S1..S3 (workmen)
  band_group        ENUM('WORKMEN','SUB_STAFF','EXECUTIVE','MANAGERIAL','LEADERSHIP','APEX') NOT NULL,
  designation_label VARCHAR(100) NOT NULL,
  sort_order        SMALLINT NOT NULL,
  CONSTRAINT fk_gradeband_tenant FOREIGN KEY (tenant_id) REFERENCES tenants(tenant_id),
  UNIQUE KEY uq_gradeband_code (tenant_id, band_code)
) ENGINE=InnoDB;

CREATE TABLE functions (
  function_id       BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  tenant_id         BIGINT UNSIGNED NOT NULL,
  division_id       BIGINT UNSIGNED NOT NULL,
  name              VARCHAR(100) NOT NULL,            -- Operations, Production, PPC, Design, NPD, Quality, Tool Room, Maintenance, ...
  CONSTRAINT fk_functions_tenant FOREIGN KEY (tenant_id) REFERENCES tenants(tenant_id),
  CONSTRAINT fk_functions_division FOREIGN KEY (division_id) REFERENCES divisions(division_id),
  UNIQUE KEY uq_function_division_name (tenant_id, division_id, name)
) ENGINE=InnoDB;

CREATE TABLE departments (
  department_id     BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  tenant_id         BIGINT UNSIGNED NOT NULL,
  division_id       BIGINT UNSIGNED NOT NULL,
  function_id       BIGINT UNSIGNED NOT NULL,
  department_id     BIGINT UNSIGNED NULL,              -- NULL means applicable across the function
  name              VARCHAR(100) NOT NULL,            -- e.g. Mechanical, EPD, Assembly, Index under Production
  CONSTRAINT fk_department_tenant FOREIGN KEY (tenant_id) REFERENCES tenants(tenant_id),
  CONSTRAINT fk_departments_division FOREIGN KEY (division_id) REFERENCES divisions(division_id),
  CONSTRAINT fk_department_function FOREIGN KEY (function_id) REFERENCES functions(function_id)
) ENGINE=InnoDB;

-- ----------------------------------------------------------------------------
-- 3. ROLES & ROLE DESCRIPTIONS
-- ----------------------------------------------------------------------------

CREATE TABLE roles (
  role_id           BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  tenant_id         BIGINT UNSIGNED NOT NULL,
  division_id       BIGINT UNSIGNED NOT NULL,
  function_id       BIGINT UNSIGNED NOT NULL,
  title             VARCHAR(150) NOT NULL,
  description_status ENUM('NOT_STARTED','DRAFT','SUBMITTED','VALIDATED') NOT NULL DEFAULT 'NOT_STARTED',
  ask_status        ENUM('NOT_MAPPED','MAPPED') NOT NULL DEFAULT 'NOT_MAPPED',
  tier              ENUM('NONE','TIER1','TIER2','TIER3','TIER4') NOT NULL DEFAULT 'NONE',
  merged_into_role_id BIGINT UNSIGNED NULL,           -- set by the overlap/duplicate audit (Module E) when merged
  created_at        DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at        DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  CONSTRAINT fk_roles_tenant FOREIGN KEY (tenant_id) REFERENCES tenants(tenant_id),
  CONSTRAINT fk_roles_division FOREIGN KEY (division_id) REFERENCES divisions(division_id),
  CONSTRAINT fk_roles_function FOREIGN KEY (function_id) REFERENCES functions(function_id),
  CONSTRAINT fk_roles_merged_into FOREIGN KEY (merged_into_role_id) REFERENCES roles(role_id)
) ENGINE=InnoDB;

CREATE TABLE role_descriptions (
  role_description_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  role_id           BIGINT UNSIGNED NOT NULL,
  version           SMALLINT NOT NULL DEFAULT 1,
  people_count      INT UNSIGNED NULL,                 -- captured from the RD template; 0 is valid for a planned role
  role_definition   TEXT NOT NULL,
  key_responsibilities TEXT NOT NULL,
  kpis              TEXT NOT NULL,
  education_certifications TEXT NOT NULL,
  minimum_relevant_experience TEXT NOT NULL,
  knowledge_required TEXT NOT NULL,
  skills_required TEXT NOT NULL,
  attitudes_behaviours TEXT NOT NULL,
  specifications_experience TEXT NOT NULL,
  equipment_process_refs TEXT NULL,                  -- ISO/5S/TPM, machinery references
  ai_refined        BOOLEAN NOT NULL DEFAULT FALSE,   -- whether the client-visible AI refine action was used
  validated_by_employee_id BIGINT UNSIGNED NULL,
  validated_at      DATETIME NULL,
  created_at        DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_roledesc_role FOREIGN KEY (role_id) REFERENCES roles(role_id),
  UNIQUE KEY uq_role_version (role_id, version)
) ENGINE=InnoDB;

-- ----------------------------------------------------------------------------
-- 4. EMPLOYEES & VACANCIES
-- ----------------------------------------------------------------------------

CREATE TABLE employees (
  employee_id       BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  tenant_id         BIGINT UNSIGNED NOT NULL,
  division_id       BIGINT UNSIGNED NOT NULL,
  employee_code     VARCHAR(30) NOT NULL,             -- system-of-truth key; never key downstream tables by name
  full_name         VARCHAR(150) NOT NULL,
  grade_band_id     BIGINT UNSIGNED NOT NULL,
  designation       VARCHAR(100) NOT NULL,
  function_id       BIGINT UNSIGNED NOT NULL,
  department_id     BIGINT UNSIGNED NULL,
  role_id           BIGINT UNSIGNED NULL,
  manager_employee_id BIGINT UNSIGNED NULL,
  tenure_start_date DATE NULL,
  date_of_birth    DATE NULL,                        -- Restricted-PII; Module B import field
  qualification     VARCHAR(150) NULL,
  date_of_joining   DATE NULL,
  last_promotion_date DATE NULL,
  retirement_date   DATE NULL,                        -- computed/entered; drives the retirement risk register
  status            ENUM('ACTIVE','SEPARATED') NOT NULL DEFAULT 'ACTIVE',
  name_collision_flag BOOLEAN NOT NULL DEFAULT FALSE,  -- set by upload validation when two employees share a name
  created_at        DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at        DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  CONSTRAINT fk_employees_tenant FOREIGN KEY (tenant_id) REFERENCES tenants(tenant_id),
  CONSTRAINT fk_employees_division FOREIGN KEY (division_id) REFERENCES divisions(division_id),
  CONSTRAINT fk_employees_gradeband FOREIGN KEY (grade_band_id) REFERENCES grade_bands(grade_band_id),
  CONSTRAINT fk_employees_function FOREIGN KEY (function_id) REFERENCES functions(function_id),
  CONSTRAINT fk_employees_department FOREIGN KEY (department_id) REFERENCES departments(department_id),
  CONSTRAINT fk_employees_role FOREIGN KEY (role_id) REFERENCES roles(role_id),
  CONSTRAINT fk_employees_manager FOREIGN KEY (manager_employee_id) REFERENCES employees(employee_id),
  UNIQUE KEY uq_employee_code (tenant_id, employee_code)
) ENGINE=InnoDB;

-- users.employee_id now resolvable — add FK after employees exists
ALTER TABLE users
  ADD CONSTRAINT fk_users_employee FOREIGN KEY (employee_id) REFERENCES employees(employee_id);

-- Explicit role-definition work allocation.  A manager sees only roles mapped
-- here, rather than every role held by their reporting line.
CREATE TABLE role_definition_assignments (
  assignment_id      BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  tenant_id          BIGINT UNSIGNED NOT NULL,
  manager_employee_id BIGINT UNSIGNED NOT NULL,
  role_id            BIGINT UNSIGNED NOT NULL,
  assigned_by_user_id BIGINT UNSIGNED NULL,
  created_at         DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_rd_assignment_tenant FOREIGN KEY (tenant_id) REFERENCES tenants(tenant_id),
  CONSTRAINT fk_rd_assignment_manager FOREIGN KEY (manager_employee_id) REFERENCES employees(employee_id),
  CONSTRAINT fk_rd_assignment_role FOREIGN KEY (role_id) REFERENCES roles(role_id),
  CONSTRAINT fk_rd_assignment_actor FOREIGN KEY (assigned_by_user_id) REFERENCES users(user_id),
  UNIQUE KEY uq_rd_assignment_manager_role (tenant_id, manager_employee_id, role_id)
) ENGINE=InnoDB;

CREATE TABLE vacant_positions (
  vacancy_id        BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  tenant_id         BIGINT UNSIGNED NOT NULL,
  division_id       BIGINT UNSIGNED NOT NULL,
  role_id           BIGINT UNSIGNED NOT NULL,
  grade_band_id     BIGINT UNSIGNED NOT NULL,
  designation       VARCHAR(100) NOT NULL,
  qualification_required VARCHAR(150) NULL,
  target_start_date DATE NULL,
  status            ENUM('OPEN','FILLED','WITHDRAWN') NOT NULL DEFAULT 'OPEN',
  created_at        DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_vacancy_tenant FOREIGN KEY (tenant_id) REFERENCES tenants(tenant_id),
  CONSTRAINT fk_vacancy_division FOREIGN KEY (division_id) REFERENCES divisions(division_id),
  CONSTRAINT fk_vacancy_role FOREIGN KEY (role_id) REFERENCES roles(role_id),
  CONSTRAINT fk_vacancy_gradeband FOREIGN KEY (grade_band_id) REFERENCES grade_bands(grade_band_id)
) ENGINE=InnoDB;

-- ----------------------------------------------------------------------------
-- 5. ASK FRAMEWORK: SUCCESS BEHAVIOURS, FUNCTIONAL SKILLS, DESIRED LEVELS
-- ----------------------------------------------------------------------------

CREATE TABLE proficiency_scale_levels (
  scale_level_id    BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  tenant_id         BIGINT UNSIGNED NOT NULL,
  scale_type        ENUM('BEHAVIOUR','FUNCTIONAL') NOT NULL,
  level             TINYINT NOT NULL,                 -- 1-4
  title             VARCHAR(50) NOT NULL,              -- Learning / Doing with Support / ... or Foundation / Applied / ...
  description       TEXT NOT NULL,
  CONSTRAINT fk_scalelevel_tenant FOREIGN KEY (tenant_id) REFERENCES tenants(tenant_id),
  UNIQUE KEY uq_scale_level (tenant_id, scale_type, level)
) ENGINE=InnoDB;

CREATE TABLE success_behaviours (
  behaviour_id      BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  tenant_id         BIGINT UNSIGNED NOT NULL,
  code              VARCHAR(10) NOT NULL,              -- SB01..SB05
  name              VARCHAR(150) NOT NULL,
  definition        TEXT NOT NULL,
  defined_via_fgd_at DATE NULL,                        -- date the off-platform focus-group discussion produced this
  created_by_user_id BIGINT UNSIGNED NULL,              -- PGC admin who entered it (Module F)
  CONSTRAINT fk_behaviour_tenant FOREIGN KEY (tenant_id) REFERENCES tenants(tenant_id),
  UNIQUE KEY uq_behaviour_code (tenant_id, code)
) ENGINE=InnoDB;

CREATE TABLE functional_skills (
  skill_id          BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  tenant_id         BIGINT UNSIGNED NOT NULL,
  division_id       BIGINT UNSIGNED NOT NULL,
  function_id       BIGINT UNSIGNED NOT NULL,
  department_id     BIGINT UNSIGNED NULL,              -- scope functional skill to a department
  code              VARCHAR(10) NOT NULL,              -- D001, D002, ...
  name              VARCHAR(150) NOT NULL,
  definition        TEXT NOT NULL,
  source            ENUM('AI_GENERATED','MANUAL') NOT NULL DEFAULT 'MANUAL',
  ai_generation_id  BIGINT UNSIGNED NULL,               -- FK added after ai_generation_log exists
  CONSTRAINT fk_skill_tenant FOREIGN KEY (tenant_id) REFERENCES tenants(tenant_id),
  CONSTRAINT fk_functional_skills_division FOREIGN KEY (division_id) REFERENCES divisions(division_id),
  CONSTRAINT fk_skill_function FOREIGN KEY (function_id) REFERENCES functions(function_id),
  CONSTRAINT fk_skill_department FOREIGN KEY (department_id) REFERENCES departments(department_id),
  UNIQUE KEY uq_skill_division_code (tenant_id, division_id, code)
) ENGINE=InnoDB;

CREATE TABLE desired_level_matrix (
  matrix_id         BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  tenant_id         BIGINT UNSIGNED NOT NULL,
  division_id       BIGINT UNSIGNED NOT NULL,
  item_type         ENUM('BEHAVIOUR','SKILL') NOT NULL,
  item_id           BIGINT UNSIGNED NOT NULL,           -- behaviour_id or skill_id, disambiguated by item_type
  grade_band_id     BIGINT UNSIGNED NOT NULL,
  role_id           BIGINT UNSIGNED NULL,               -- optional role-specific override of the band-level default
  department_id     BIGINT UNSIGNED NULL,               -- optional department-specific override for functional skills
  desired_level     TINYINT NOT NULL,                   -- 1-4
  CONSTRAINT fk_matrix_tenant FOREIGN KEY (tenant_id) REFERENCES tenants(tenant_id),
  CONSTRAINT fk_desired_level_matrix_division FOREIGN KEY (division_id) REFERENCES divisions(division_id),
  CONSTRAINT fk_matrix_gradeband FOREIGN KEY (grade_band_id) REFERENCES grade_bands(grade_band_id),
  CONSTRAINT fk_matrix_role FOREIGN KEY (role_id) REFERENCES roles(role_id),
  CONSTRAINT fk_matrix_department FOREIGN KEY (department_id) REFERENCES departments(department_id),
  UNIQUE KEY uq_matrix_division_item_band_role (tenant_id, division_id, item_type, item_id, grade_band_id, role_id)
) ENGINE=InnoDB;

CREATE TABLE ask_dictionary_versions (
  version_id        BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  tenant_id         BIGINT UNSIGNED NOT NULL,
  version_no        SMALLINT NOT NULL,
  status            ENUM('DRAFT','IN_REVIEW','APPROVED','LOCKED') NOT NULL DEFAULT 'DRAFT',
  approved_by_user_id BIGINT UNSIGNED NULL,
  approved_at       DATETIME NULL,
  generated_report_url VARCHAR(500) NULL,
  created_at        DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_askversion_tenant FOREIGN KEY (tenant_id) REFERENCES tenants(tenant_id),
  UNIQUE KEY uq_ask_version (tenant_id, version_no)
) ENGINE=InnoDB;

-- ----------------------------------------------------------------------------
-- 6. AI GENERATION (PGC-hidden — Module G) & AUDIT
-- ----------------------------------------------------------------------------

CREATE TABLE ai_generation_log (
  generation_id     BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  tenant_id         BIGINT UNSIGNED NOT NULL,
  actor_user_id     BIGINT UNSIGNED NOT NULL,           -- must resolve to role = PGC_ADMIN; enforced at application layer
  module            ENUM('ROLE_DESC_REFINE','KS_CLUSTER_GEN','OVERLAP_DETECTION') NOT NULL,
  prompt_version    VARCHAR(30) NOT NULL,
  input_ref         TEXT NOT NULL,                      -- pointer to source role description(s)
  output_ref        TEXT NOT NULL,                      -- pointer to generated draft content
  status            ENUM('DRAFT','PUBLISHED','REJECTED') NOT NULL DEFAULT 'DRAFT',
  reviewed_by_user_id BIGINT UNSIGNED NULL,
  published_at      DATETIME NULL,
  created_at        DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_aigen_tenant FOREIGN KEY (tenant_id) REFERENCES tenants(tenant_id),
  CONSTRAINT fk_aigen_actor FOREIGN KEY (actor_user_id) REFERENCES users(user_id)
) ENGINE=InnoDB;

ALTER TABLE functional_skills
  ADD CONSTRAINT fk_skill_aigen FOREIGN KEY (ai_generation_id) REFERENCES ai_generation_log(generation_id);

CREATE TABLE audit_log (
  log_id            BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  tenant_id         BIGINT UNSIGNED NULL,
  actor_user_id     BIGINT UNSIGNED NOT NULL,
  action            VARCHAR(100) NOT NULL,
  entity_type       VARCHAR(100) NOT NULL,
  entity_id         BIGINT UNSIGNED NOT NULL,
  before_json       JSON NULL,
  after_json        JSON NULL,
  created_at        DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_audit_actor FOREIGN KEY (actor_user_id) REFERENCES users(user_id),
  KEY idx_audit_entity (entity_type, entity_id)
) ENGINE=InnoDB;

-- ----------------------------------------------------------------------------
-- 7. ASSESSMENT CYCLE, FORMS & LINE ITEMS (unified scoring pattern)
-- ----------------------------------------------------------------------------

CREATE TABLE assessment_cycles (
  cycle_id          BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  tenant_id         BIGINT UNSIGNED NOT NULL,
  name              VARCHAR(100) NOT NULL,              -- e.g. 'FY2026-27 Annual Cycle'
  ask_version_id    BIGINT UNSIGNED NOT NULL,            -- locked framework this cycle assesses against
  period_start      DATE NOT NULL,
  period_end        DATE NOT NULL,
  status            ENUM('NOT_STARTED','IN_PROGRESS','CLOSED') NOT NULL DEFAULT 'NOT_STARTED',
  created_at        DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_cycle_tenant FOREIGN KEY (tenant_id) REFERENCES tenants(tenant_id),
  CONSTRAINT fk_cycle_askversion FOREIGN KEY (ask_version_id) REFERENCES ask_dictionary_versions(version_id)
) ENGINE=InnoDB;

-- Restricted-PII: tenant-controlled recipients for assessment submission alerts.
CREATE TABLE assessment_notification_recipients (
  notification_recipient_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  tenant_id         BIGINT UNSIGNED NOT NULL,
  email             VARCHAR(150) NOT NULL,
  is_active         BOOLEAN NOT NULL DEFAULT TRUE,
  created_at        DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at        DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  CONSTRAINT fk_assessment_notification_recipient_tenant
    FOREIGN KEY (tenant_id) REFERENCES tenants(tenant_id),
  UNIQUE KEY uq_assessment_notification_recipient (tenant_id, email),
  KEY ix_assessment_notification_recipient_active (tenant_id, is_active)
) ENGINE=InnoDB;

-- Restricted: encrypted SMTP credentials; the encryption key is held outside the database.
CREATE TABLE email_delivery_configurations (
  email_delivery_configuration_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  tenant_id         BIGINT UNSIGNED NOT NULL,
  smtp_host         VARCHAR(255) NOT NULL,
  smtp_port         SMALLINT UNSIGNED NOT NULL DEFAULT 587,
  smtp_username     VARCHAR(255) NULL,
  smtp_password_encrypted TEXT NOT NULL,
  smtp_from_email   VARCHAR(150) NOT NULL,
  smtp_use_tls      BOOLEAN NOT NULL DEFAULT TRUE,
  is_active         BOOLEAN NOT NULL DEFAULT TRUE,
  created_at        DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at        DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  CONSTRAINT fk_email_delivery_configuration_tenant
    FOREIGN KEY (tenant_id) REFERENCES tenants(tenant_id),
  UNIQUE KEY uq_email_delivery_configuration_tenant (tenant_id)
) ENGINE=InnoDB;

CREATE TABLE assessment_forms (
  form_id           BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  tenant_id         BIGINT UNSIGNED NOT NULL,
  cycle_id          BIGINT UNSIGNED NOT NULL,
  assessment_type   ENUM('BEHAVIOUR','SKILL') NOT NULL,
  employee_id       BIGINT UNSIGNED NOT NULL,
  role_id           BIGINT UNSIGNED NOT NULL,
  manager_employee_id BIGINT UNSIGNED NOT NULL,
  skip_manager_employee_id BIGINT UNSIGNED NULL,
  status            ENUM('NOT_STARTED','SELF_SUBMITTED','MANAGER_SUBMITTED','RECONCILIATION_IN_PROGRESS',
                          'ESCALATED_TO_SKIP_MANAGER','AGREED_SIGNED','SUBMITTED_TO_HR') NOT NULL DEFAULT 'NOT_STARTED',
  self_assessment_date DATE NULL,
  behaviour_self_submitted_at DATETIME NULL,
  functional_self_submitted_at DATETIME NULL,
  manager_assessment_date DATE NULL,
  behaviour_manager_submitted_at DATETIME NULL,
  functional_manager_submitted_at DATETIME NULL,
  employee_signed_at DATETIME NULL,
  manager_signed_at DATETIME NULL,
  skip_manager_signed_at DATETIME NULL,
  head_hr_signed_at DATETIME NULL,
  created_at        DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at        DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  CONSTRAINT fk_form_tenant FOREIGN KEY (tenant_id) REFERENCES tenants(tenant_id),
  CONSTRAINT fk_form_cycle FOREIGN KEY (cycle_id) REFERENCES assessment_cycles(cycle_id),
  CONSTRAINT fk_form_employee FOREIGN KEY (employee_id) REFERENCES employees(employee_id),
  CONSTRAINT fk_form_role FOREIGN KEY (role_id) REFERENCES roles(role_id),
  CONSTRAINT fk_form_manager FOREIGN KEY (manager_employee_id) REFERENCES employees(employee_id),
  CONSTRAINT fk_form_skipmanager FOREIGN KEY (skip_manager_employee_id) REFERENCES employees(employee_id),
  UNIQUE KEY uq_form_employee_cycle_type (cycle_id, employee_id, assessment_type)
) ENGINE=InnoDB;

-- Unified line-item table: one row per (form, item) covering BOTH functional
-- skills and success behaviours via item_type, exactly as PGC's paper ASK
-- form does (Knowledge & Skills table + Success Behaviours table share the
-- same 5-column structure: DL / SAL / MAL / Gap / Description).
CREATE TABLE assessment_line_items (
  line_item_id      BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  form_id           BIGINT UNSIGNED NOT NULL,
  item_type         ENUM('BEHAVIOUR','SKILL') NOT NULL,
  item_id           BIGINT UNSIGNED NOT NULL,            -- behaviour_id or skill_id, disambiguated by item_type
  desired_level     TINYINT NOT NULL,                    -- copied from desired_level_matrix at form-creation time
  self_assessment_level   TINYINT NULL,                  -- SAL
  manager_assessment_level TINYINT NULL,                 -- MAL
  gap               TINYINT GENERATED ALWAYS AS (manager_assessment_level - desired_level) STORED,
  -- Gap = MAL - DL, always. See TDD Section 4 for why this direction is hard-coded.
  description_for_improvement TEXT NULL,
  data_quality_flag ENUM('OK','NA','MISSING_MANAGER','ORPHAN_RECORD','ZERO_NOT_ENTERED') NOT NULL DEFAULT 'OK',
  created_at        DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at        DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  CONSTRAINT fk_lineitem_form FOREIGN KEY (form_id) REFERENCES assessment_forms(form_id),
  UNIQUE KEY uq_lineitem_form_item (form_id, item_type, item_id)
) ENGINE=InnoDB;

CREATE TABLE outstanding_assessment_flags (
  flag_id           BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  tenant_id         BIGINT UNSIGNED NOT NULL,
  cycle_id          BIGINT UNSIGNED NOT NULL,
  employee_id       BIGINT UNSIGNED NOT NULL,
  missing_item      ENUM('SELF','MANAGER','BOTH') NOT NULL,
  owner_user_id     BIGINT UNSIGNED NULL,
  blocks_description TEXT NOT NULL,                      -- e.g. 'gap cannot be computed', 'priority score understated'
  resolved_at       DATETIME NULL,
  created_at        DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_flag_tenant FOREIGN KEY (tenant_id) REFERENCES tenants(tenant_id),
  CONSTRAINT fk_flag_cycle FOREIGN KEY (cycle_id) REFERENCES assessment_cycles(cycle_id),
  CONSTRAINT fk_flag_employee FOREIGN KEY (employee_id) REFERENCES employees(employee_id)
) ENGINE=InnoDB;

-- ----------------------------------------------------------------------------
-- 8. PRIORITY SCORING, CRITICAL ROLES & SUCCESSION
-- ----------------------------------------------------------------------------

CREATE TABLE priority_score_records (
  record_id         BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  tenant_id         BIGINT UNSIGNED NOT NULL,
  cycle_id          BIGINT UNSIGNED NOT NULL,
  employee_id       BIGINT UNSIGNED NOT NULL,
  role_criticality  TINYINT UNSIGNED NOT NULL,           -- 0-35
  gap_severity      TINYINT UNSIGNED NOT NULL,           -- 0-30
  succession_urgency TINYINT UNSIGNED NOT NULL,          -- 0-20
  market_scarcity   TINYINT UNSIGNED NOT NULL,           -- 0-15
  total_score       TINYINT UNSIGNED GENERATED ALWAYS AS
                      (role_criticality + gap_severity + succession_urgency + market_scarcity) STORED,
  band              ENUM('P1','P2','NONE') NOT NULL DEFAULT 'NONE',
  -- Band threshold is application-configured (see TDD Section 4 open item), not hard-coded here.
  person_type       ENUM('CRITICAL_INCUMBENT','SUCCESSION_CANDIDATE','DEPTH') NOT NULL,
  build_or_buy      ENUM('BUILD','BUY') NULL,
  worst_gap         TINYINT NULL,
  negative_gap_count SMALLINT UNSIGNED NOT NULL DEFAULT 0,
  gap_ratio         DECIMAL(4,2) NULL,
  items_assessed_count SMALLINT UNSIGNED NOT NULL DEFAULT 0,
  recommended_intervention TEXT NULL,
  computed_at       DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_priority_tenant FOREIGN KEY (tenant_id) REFERENCES tenants(tenant_id),
  CONSTRAINT fk_priority_cycle FOREIGN KEY (cycle_id) REFERENCES assessment_cycles(cycle_id),
  CONSTRAINT fk_priority_employee FOREIGN KEY (employee_id) REFERENCES employees(employee_id),
  UNIQUE KEY uq_priority_cycle_employee (cycle_id, employee_id)
) ENGINE=InnoDB;

CREATE TABLE critical_roles (
  critical_role_id  BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  tenant_id         BIGINT UNSIGNED NOT NULL,
  role_id           BIGINT UNSIGNED NOT NULL,
  criteria_business_impact BOOLEAN NOT NULL DEFAULT FALSE,
  criteria_technical_scarcity BOOLEAN NOT NULL DEFAULT FALSE,
  criteria_institutional_knowledge BOOLEAN NOT NULL DEFAULT FALSE,
  criteria_vacancy_risk BOOLEAN NOT NULL DEFAULT FALSE,
  criteria_thin_succession_depth BOOLEAN NOT NULL DEFAULT FALSE,
  criteria_met_count TINYINT GENERATED ALWAYS AS (
      criteria_business_impact + criteria_technical_scarcity + criteria_institutional_knowledge +
      criteria_vacancy_risk + criteria_thin_succession_depth
  ) STORED,                                              -- >= 2 => candidate critical role, per PRD Module N
  tier              ENUM('TIER1','TIER2','TIER3','TIER4') NULL,
  risk_situation    ENUM('SITUATION_1_CRITICAL','SITUATION_2_HIGH','SITUATION_3_MEDIUM','SITUATION_4_WATCH') NULL,
  status            ENUM('CANDIDATE','VALIDATED','REJECTED') NOT NULL DEFAULT 'CANDIDATE',
  validated_by_user_id BIGINT UNSIGNED NULL,
  validated_at      DATETIME NULL,
  CONSTRAINT fk_critrole_tenant FOREIGN KEY (tenant_id) REFERENCES tenants(tenant_id),
  CONSTRAINT fk_critrole_role FOREIGN KEY (role_id) REFERENCES roles(role_id),
  UNIQUE KEY uq_critrole_role (role_id)
) ENGINE=InnoDB;

CREATE TABLE assumptions_config (
  config_id         BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  tenant_id         BIGINT UNSIGNED NOT NULL,
  plan_start_date   DATE NOT NULL,
  months_per_move   TINYINT UNSIGNED NOT NULL DEFAULT 24,
  min_rotation_months TINYINT UNSIGNED NOT NULL DEFAULT 18,
  max_rotation_months TINYINT UNSIGNED NOT NULL DEFAULT 36,
  gaps_closed_per_move TINYINT UNSIGNED NOT NULL DEFAULT 2,
  behaviours_per_move TINYINT UNSIGNED NOT NULL DEFAULT 1,
  updated_at        DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  CONSTRAINT fk_assumptions_tenant FOREIGN KEY (tenant_id) REFERENCES tenants(tenant_id),
  UNIQUE KEY uq_assumptions_tenant (tenant_id)
) ENGINE=InnoDB;

CREATE TABLE succession_candidates (
  candidate_id      BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  tenant_id         BIGINT UNSIGNED NOT NULL,
  critical_role_id  BIGINT UNSIGNED NOT NULL,
  candidate_employee_id BIGINT UNSIGNED NOT NULL,
  readiness_level   TINYINT UNSIGNED NOT NULL,           -- 1=Emergency, 2=One Move, 3=Two Moves, 4=Three Moves
  readiness_label   VARCHAR(50) NOT NULL,                -- denormalised for reporting: 'Emergency Replacement', etc.
  estimated_ready_date DATE NULL,                        -- computed from assumptions_config + plan_start_date
  notes             TEXT NULL,
  created_at        DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at        DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  CONSTRAINT fk_succession_tenant FOREIGN KEY (tenant_id) REFERENCES tenants(tenant_id),
  CONSTRAINT fk_succession_critrole FOREIGN KEY (critical_role_id) REFERENCES critical_roles(critical_role_id),
  CONSTRAINT fk_succession_candidate FOREIGN KEY (candidate_employee_id) REFERENCES employees(employee_id)
) ENGINE=InnoDB;

SET FOREIGN_KEY_CHECKS = 1;

-- ----------------------------------------------------------------------------
-- 9. EMPLOYEE UPLOAD STAGING (Module B; Restricted-PII)
-- ----------------------------------------------------------------------------

CREATE TABLE employee_upload_batches (
  batch_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  tenant_id BIGINT UNSIGNED NOT NULL,
  uploaded_by_user_id BIGINT UNSIGNED NOT NULL,
  status ENUM('DRAFT','PUBLISHED','REJECTED') NOT NULL DEFAULT 'DRAFT',
  rejection_reason TEXT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  published_at DATETIME NULL,
  CONSTRAINT fk_upload_batch_tenant FOREIGN KEY (tenant_id) REFERENCES tenants(tenant_id),
  CONSTRAINT fk_upload_batch_user FOREIGN KEY (uploaded_by_user_id) REFERENCES users(user_id)
) ENGINE=InnoDB;

CREATE TABLE employee_upload_rows (
  upload_row_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  batch_id BIGINT UNSIGNED NOT NULL,
  `row_number` INT UNSIGNED NOT NULL,
  employee_code VARCHAR(30) NULL,
  raw_json JSON NOT NULL,
  validation_error TEXT NULL,
  accepted BOOLEAN NOT NULL DEFAULT FALSE,
  staged_role_title VARCHAR(150) NULL,
  CONSTRAINT fk_upload_row_batch FOREIGN KEY (batch_id) REFERENCES employee_upload_batches(batch_id),
  UNIQUE KEY uq_upload_row_number (batch_id, `row_number`)
) ENGINE=InnoDB;

-- ----------------------------------------------------------------------------
-- 9. SEED DATA — grade bands, five Success Behaviours, proficiency scales
--    (tenant_id = 1 assumed to be the KDDL tenant seeded during onboarding)
-- ----------------------------------------------------------------------------

INSERT INTO grade_bands (tenant_id, band_code, band_group, designation_label, sort_order) VALUES
  (1,'S1','WORKMEN','Workmen S1',1),
  (1,'S2','WORKMEN','Workmen S2',2),
  (1,'S3','SUB_STAFF','Sub-staff S3',3),
  (1,'E1','EXECUTIVE','Executive E1',4),
  (1,'E2','EXECUTIVE','Executive E2',5),
  (1,'E3','EXECUTIVE','Executive E3',6),
  (1,'E4','EXECUTIVE','Executive E4',7),
  (1,'M1','MANAGERIAL','Managerial M1',8),
  (1,'M2','MANAGERIAL','Managerial M2',9),
  (1,'M3','MANAGERIAL','Managerial M3',10),
  (1,'M4','MANAGERIAL','Managerial M4',11),
  (1,'LM1','LEADERSHIP','Leadership LM1',12),
  (1,'LM2','LEADERSHIP','Leadership LM2',13),
  (1,'A1','APEX','Apex A1',14),
  (1,'A2','APEX','Apex A2',15),
  (1,'A3','APEX','Apex A3',16);

INSERT INTO proficiency_scale_levels (tenant_id, scale_type, level, title, description) VALUES
  (1,'BEHAVIOUR',1,'Learning','Follows guidance, develops basics; inconsistent or supervised; individual/task-level.'),
  (1,'BEHAVIOUR',2,'Doing with Support','Applies skills in known situations; consistent in routine tasks; team/workgroup.'),
  (1,'BEHAVIOUR',3,'Doing Independently','Demonstrates ownership, initiative; consistent across varied contexts; function/cross-functional.'),
  (1,'BEHAVIOUR',4,'Guiding Others','Coaches others, role-models behaviour; embeds into team/org norms; team culture/business-wide.'),
  (1,'FUNCTIONAL',1,'Foundation','Task/activity; low-to-moderate complexity; individual/limited team.'),
  (1,'FUNCTIONAL',2,'Applied','Process/work stream; moderate-to-high complexity; team/work unit.'),
  (1,'FUNCTIONAL',3,'Proficient','Function/domain; high-to-very-high complexity; function/department/BU.'),
  (1,'FUNCTIONAL',4,'Expert / Strategic','Domain/organisation; very high complexity; organisation/cross-functional.');

INSERT INTO success_behaviours (tenant_id, code, name, definition) VALUES
  (1,'SB01','Ownership and Execution Discipline','Demonstrates commitment to goals, delivers outcomes reliably, and follows through with accuracy and consistency.'),
  (1,'SB02','Problem Solving and Critical Thinking','Approaches challenges with structured thinking, identifies root causes, and applies solutions that lead to lasting improvements.'),
  (1,'SB03','Collaboration and Influencing','Builds strong relationships, communicates clearly, and works across functions to achieve shared goals and positive outcomes.'),
  (1,'SB04','Detail Orientation and Quality Focus','Consistently delivers accurate, complete, and high-quality output by focusing on details, standards, and continuous improvement.'),
  (1,'SB05','Learning Agility and Coaching Mindset','Demonstrates curiosity, adapts quickly to change, and develops self and others to stay ahead of evolving business needs.');

-- Functional skills, roles, employees, and desired-level matrix rows are
-- tenant/department specific and should be loaded via Module B/G workflows,
-- not seeded here.
