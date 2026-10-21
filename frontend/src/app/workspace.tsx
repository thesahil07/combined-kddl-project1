import { FormEvent, useEffect, useState } from "react";

import { activeTenantBrand } from "./tenantBrand";
import {
  RoleDefinitionTemplate,
  RoleDefinitionValues,
} from "./roleDefinitionTemplate";
import { ExecutiveReviewWorkspace } from "./executiveReview";

const apiUrl = "http://127.0.0.1:8000/api/v1";

export type CurrentUser = {
  email: string;
  role:
    | "PGC_ADMIN"
    | "HR_SPOC"
    | "HOD_MANAGER"
    | "EMPLOYEE"
    | "SKIP_MANAGER"
    | "SPONSOR_VIEWER";
  tenant_id: number | null;
  employee_id: number | null;
  division_scope_id: number | null;
  admin_console_access: boolean;
  executive_review_access: boolean;
  is_manager: boolean;
  employee_name: string | null;
  employee_code: string | null;
};
type TeamMember = {
  employee_id: number;
  employee_code: string;
  full_name: string;
  designation: string;
  role_id: number | null;
  role_title: string | null;
  function_name: string;
  department_name: string | null;
  grade_band_code: string;
  description_status:
    | "NOT_STARTED"
    | "DRAFT"
    | "SUBMITTED"
    | "VALIDATED"
    | null;
  self_assessment_status: "PENDING" | "IN_PROGRESS" | "COMPLETED";
  manager_assessment_status: "PENDING" | "IN_PROGRESS" | "COMPLETED";
  behaviour_employee_status: AssessmentStatus;
  behaviour_manager_status: AssessmentStatus;
  functional_employee_status: AssessmentStatus;
  functional_manager_status: AssessmentStatus;
  gap_items: number;
};
type AssessmentStatus =
  | "PENDING_WITH_EMPLOYEE"
  | "PENDING_WITH_MANAGER"
  | "COMPLETED"
  | "NOT_CONFIGURED";
type AssignedRole = {
  employee_id: number;
  full_name: string;
  designation: string;
  role_id: number;
  role_title: string;
  function_name: string;
  department_name: string | null;
  grade_band_code: string | null;
  description_status: "NOT_STARTED" | "DRAFT" | "SUBMITTED" | "VALIDATED";
};
type RoleDefinitionTarget = TeamMember | AssignedRole;
type TeamRoleDefinition = {
  employee_id: number;
  employee_code: string;
  full_name: string;
  role_title: string;
  role_definition: string | null;
  key_responsibilities: string | null;
  kpis: string | null;
  knowledge_required: string | null;
  skills_required: string | null;
  attitudes_behaviours: string | null;
};
type SkipDashboard = {
  manager: { full_name: string; employee_code: string };
  active_cycle: { name: string; period_start: string; period_end: string } | null;
  team: TeamMember[];
  assigned_roles: AssignedRole[];
  team_size: number;
  pending_self_assessments: number;
  pending_manager_assessments: number;
  pending_employee_sections: number;
  pending_manager_sections: number;
  employees_with_gaps: number;
  behaviour_gap_items: number;
  functional_gap_items: number;
  gap_items: number;
  role_definition_status: {
    not_started: number;
    draft: number;
    submitted: number;
  };
};
type GapValue = {
  desired_level: number | null;
  self_assessment_level: number | null;
  manager_assessment_level: number | null;
  gap: number | null;
};
type GapMatrixRow = {
  employee_id: number;
  employee_code: string;
  full_name: string;
  role_title: string | null;
  grade_band_code: string | null;
  designation: string;
  values: Record<string, GapValue>;
};
type GapMatrix = {
  items: { item_id: number; name: string }[];
  rows: GapMatrixRow[];
};
type GapMatrices = {
  success_behaviours: GapMatrix;
  functional_skills: GapMatrix;
};
type EmployeeDashboard = {
  employee: { full_name: string; employee_code: string };
  active_cycle: {
    cycle_id: number;
    name: string;
    period_start: string;
    period_end: string;
  } | null;
  form_status?: string;
  success_behaviours_status: "PENDING" | "COMPLETE";
  functional_skills_status: "PENDING" | "COMPLETE";
};
type EmployeeRole = {
  role_id: number;
  title: string;
  description_status: string;
  role_definition: string | null;
  key_responsibilities: string | null;
  kpis: string | null;
  knowledge_required: string | null;
  skills_required: string | null;
  attitudes_behaviours: string | null;
};
type EmployeeAssessment = {
  cycle: {
    cycle_id: number;
    name: string;
    period_start: string;
    period_end: string;
  };
  form_status: string;
  is_submitted: boolean;
  items: {
    item_id: number;
    code: string;
    name: string;
    definition: string;
    desired_level: number;
    self_assessment_level: number | null;
  }[];
};
type LevelDefinition = { level: number; title: string; description: string };

function LevelDefinitionButton({ itemType, itemId }: { itemType: "success-behaviours" | "functional-skills"; itemId: number }) {
  const [levels, setLevels] = useState<LevelDefinition[] | null>(null);
  const [open, setOpen] = useState(false);
  async function show() {
    const token = sessionStorage.getItem("kddl_access_token") ?? "";
    const response = await fetch(`${apiUrl}/employee/level-definitions/${itemType}/${itemId}`, { headers: { Authorization: `Bearer ${token}` } });
    setLevels(response.ok ? ((await response.json()).levels as LevelDefinition[]) : []);
    setOpen(true);
  }
  return <>{<button type="button" className="role-definition-icon" title="View level definitions" onClick={() => void show()}>ⓘ</button>}{open && <div className="dialog-backdrop"><section className="role-dialog" role="dialog" aria-modal="true"><button className="close" onClick={() => setOpen(false)}>Close</button><h2>Level definitions</h2>{levels?.map(level => <section key={level.level}><h3>L{level.level} · {level.title}</h3><p className="preserve-lines">{level.description}</p></section>)}</section></div>}</>;
}
type PreviousAssessment = {
  cycle_id: number;
  name: string;
  period_start: string;
  period_end: string;
  form_status: string;
  success_behaviours: PreviousAssessmentItem[];
  functional_skills: PreviousAssessmentItem[];
};
type PreviousAssessmentItem = {
  item_id: number;
  item_name: string;
  desired_level: number;
  self_assessment_level: number | null;
  manager_assessment_level: number | null;
  gap: number | null;
};
type ManagerAssessmentItem = {
  form_id: number;
  item_id: number;
  code: string;
  name: string;
  definition: string;
  desired_level: number;
  self_assessment_level: number | null;
  manager_assessment_level: number | null;
};
type ManagerAssessment = {
  cycle: { cycle_id: number; name: string };
  form_status: string;
  behaviour_is_submitted: boolean;
  functional_is_submitted: boolean;
  success_behaviours: ManagerAssessmentItem[];
  functional_skills: ManagerAssessmentItem[];
};
type AdminReport = {
  divisions: { division_id: number; name: string }[];
  cycles: { cycle_id: number; name: string; period_start: string; period_end: string; status: string }[];
  selected_cycle_id: number | null;
  page: number;
  page_size: number;
  total_employees: number;
  employees: Array<{
    employee_id: number; employee_code: string; full_name: string; division_name: string;
    manager_name: string | null; role_title: string; behaviour_self_status: AssessmentStatus;
    behaviour_manager_status: AssessmentStatus; functional_self_status: AssessmentStatus;
    functional_manager_status: AssessmentStatus; behaviour_gaps: number; functional_gaps: number;
  }>;
  summary: Record<string, number>;
};
type SubmittedConsoleAssessment = {
  employee: { full_name: string; employee_code: string; division_name: string };
  success_behaviours: PreviousAssessmentItem[];
  functional_skills: PreviousAssessmentItem[];
};

function formatDisplayDate(value: string): string {
  const [year, month, day] = value.slice(0, 10).split("-").map(Number);
  const months = [
    "JAN", "FEB", "MAR", "APR", "MAY", "JUN",
    "JUL", "AUG", "SEP", "OCT", "NOV", "DEC",
  ];
  if (!year || !month || !day || month > 12 || day > 31) return value;
  return `${String(day).padStart(2, "0")} ${months[month - 1]} ${year}`;
}

function AssessmentLegend({ includeStatuses = false }: { includeStatuses?: boolean }) {
  return (
    <p className="assessment-legend">
      <b>Key:</b> SB = Success Behaviour · FS/SF = Functional Skills · DL = Desired Level · SAL = Self Assessment Level · MAL = Manager Assessment Level · GAP = difference from desired level (shaded when below the desired level)
      {includeStatuses && " · Employee and Manager columns show who needs to complete that section."}
    </p>
  );
}

const roleViews: Record<
  CurrentUser["role"],
  { label: string; title: string; description: string; actions: string[] }
> = {
  PGC_ADMIN: {
    label: "Platform administration",
    title: "Platform control centre",
    description:
      "Manage the operating foundation, client access, and PGC-only workflows.",
    actions: [
      "Tenant oversight",
      "Role description governance",
      "AI workflow controls",
    ],
  },
  HR_SPOC: {
    label: "People operations",
    title: "Your talent workspace",
    description:
      "Prepare organisation data, shape role clarity, and coordinate the assessment cycle.",
    actions: ["Employee data", "Role descriptions", "Assessment readiness"],
  },
  HOD_MANAGER: {
    label: "Function leadership",
    title: "Your team workspace",
    description:
      "Review role descriptions and guide capability conversations for your team.",
    actions: ["My function", "Role descriptions", "Team capability"],
  },
  EMPLOYEE: {
    label: "My development",
    title: "Your growth workspace",
    description:
      "See your role, assessments, and development priorities in one focused space.",
    actions: ["My role", "My assessment", "Development plan"],
  },
  SKIP_MANAGER: {
    label: "Leadership review",
    title: "Your review workspace",
    description:
      "Support fair, consistent talent conversations across the reporting line.",
    actions: ["Role definitions", "Team assessments", "Gaps to review"],
  },
  SPONSOR_VIEWER: {
    label: "Executive insight",
    title: "Talent insight workspace",
    description:
      "Access aggregate, persona-based talent insights without employee-level records.",
    actions: ["Talent overview", "Succession signals", "Workforce themes"],
  },
};

function ChangePasswordAction({ onSignOut, navigation = false, navigationNumber = "05" }: { onSignOut: () => void; navigation?: boolean; navigationNumber?: string }) {
  const [isOpen, setIsOpen] = useState(false);
  const [message, setMessage] = useState("");
  const token = sessionStorage.getItem("kddl_access_token") ?? "";

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const newPassword = String(form.get("new_password") ?? "");
    if (newPassword !== String(form.get("confirm_password") ?? "")) {
      setMessage("New password and confirmation must match.");
      return;
    }
    setMessage("Changing password...");
    const response = await fetch(`${apiUrl}/auth/change-password`, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${token}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        current_password: form.get("current_password"),
        new_password: newPassword,
      }),
    });
    if (!response.ok) {
      const body = (await response.json().catch(() => null)) as {
        detail?: string | Array<{ msg?: string }>;
      } | null;
      const detail = body?.detail;
      const validationMessage = Array.isArray(detail)
        ? detail.map((issue) => issue.msg).filter(Boolean).join(" ")
        : detail;
      setMessage(validationMessage || "Unable to change password.");
      return;
    }
    window.alert("Password changed. Please sign in again.");
    onSignOut();
  }

  return (
    <>
      <button className={`password-action${navigation ? " navigation-option" : ""}`} onClick={() => setIsOpen(true)}>
        {navigation && <b>{navigationNumber}</b>}Change password
      </button>
      {isOpen && (
        <div className="dialog-backdrop">
          <section className="dialog password-dialog" role="dialog" aria-modal="true" aria-labelledby="change-password-title">
            <p className="eyebrow">SECURE ACCESS</p>
            <h2 id="change-password-title">Change password</h2>
            <p>Use at least 12 characters, including uppercase, lowercase, and a number.</p>
            <form onSubmit={submit}>
              <label>Current password<input name="current_password" type="password" autoComplete="current-password" required /></label>
              <label>New password<input name="new_password" type="password" autoComplete="new-password" required /></label>
              <label>Confirm new password<input name="confirm_password" type="password" autoComplete="new-password" required /></label>
              <div className="password-dialog-actions">
                <button type="submit">Change password</button>
                <button type="button" className="password-close" onClick={() => setIsOpen(false)}>Close</button>
              </div>
            </form>
            {message && <div className="login-message" role="status">{message}</div>}
          </section>
        </div>
      )}
    </>
  );
}

function SkipManagerWorkspace({
  user,
  onSignOut,
  onOpenAdminConsole,
  onOpenExecutiveReview,
  onOpenEmployeeWorkspace,
}: {
  user: CurrentUser;
  onSignOut: () => void;
  onOpenAdminConsole: () => void;
  onOpenExecutiveReview: () => void;
  onOpenEmployeeWorkspace: () => void;
}) {
  const [dashboard, setDashboard] = useState<SkipDashboard | null>(null);
  const [gapMatrices, setGapMatrices] = useState<GapMatrices | null>(null);
  // Role-definition review is temporarily unavailable for every manager.
  const roleDefinitionStatusEnabled = false;
  const [active, setActive] = useState("assessments");
  const [selected, setSelected] = useState<RoleDefinitionTarget | null>(null);
  const [definitionValues, setDefinitionValues] =
    useState<RoleDefinitionValues>({});
  const [selectedEmployee, setSelectedEmployee] = useState<TeamMember | null>(
    null,
  );
  const [managerAssessment, setManagerAssessment] =
    useState<ManagerAssessment | null>(null);
  const [managerType, setManagerType] = useState<
    "success-behaviours" | "functional-skills"
  >("success-behaviours");
  const [previousAssessments, setPreviousAssessments] = useState<
    PreviousAssessment[] | null
  >(null);
  const [submittedAssessment, setSubmittedAssessment] =
    useState<SubmittedConsoleAssessment | null>(null);
  const [teamRoleDefinition, setTeamRoleDefinition] =
    useState<TeamRoleDefinition | null>(null);
  const [saveMessage, setSaveMessage] = useState("");
  const token = sessionStorage.getItem("kddl_access_token") ?? "";
  const managerIdentity = dashboard?.manager ?? (
    user.employee_name && user.employee_code
      ? { full_name: user.employee_name, employee_code: user.employee_code }
      : null
  );

  const load = async () => {
    const headers = { Authorization: `Bearer ${token}` };
    const [dashboardResponse, gapsResponse] = await Promise.all([
      fetch(`${apiUrl}/skip-manager/dashboard`, { headers }),
      fetch(`${apiUrl}/skip-manager/gaps`, { headers }),
    ]);
    if (!dashboardResponse.ok || !gapsResponse.ok)
      throw new Error("Unable to load your manager workspace.");
    setDashboard((await dashboardResponse.json()) as SkipDashboard);
    setGapMatrices((await gapsResponse.json()) as GapMatrices);
  };
  useEffect(() => {
    load().catch((error) => setSaveMessage(error.message));
  }, []);

  async function openDefinition(member: RoleDefinitionTarget | null) {
    if (!member?.role_id) return;
    const response = await fetch(
      `${apiUrl}/skip-manager/role-definitions/${member.role_id}`,
      { headers: { Authorization: `Bearer ${token}` } },
    );
    setDefinitionValues(
      response.ok ? ((await response.json()) as RoleDefinitionValues) : {},
    );
    setSelected(member);
  }

  async function saveDefinition(
    event: FormEvent<HTMLFormElement>,
    action: "draft" | "submit",
  ) {
    event.preventDefault();
    if (!selected?.role_id) return;
    const values = new FormData(event.currentTarget);
    const response = await fetch(
      `${apiUrl}/skip-manager/role-definitions/${selected.role_id}${action === "submit" ? "/submit" : ""}`,
      {
        method: action === "submit" ? "POST" : "PUT",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          people_count: Number(values.get("people_count")),
          role_definition: values.get("role_definition"),
          key_responsibilities: values.get("key_responsibilities"),
          kpis: values.get("kpis"),
          education_certifications: values.get("education_certifications"),
          minimum_relevant_experience: values.get(
            "minimum_relevant_experience",
          ),
          knowledge_required: values.get("knowledge_required"),
          skills_required: values.get("skills_required"),
          attitudes_behaviours: values.get("attitudes_behaviours"),
          equipment_process_refs: values.get("equipment_process_refs") || null,
        }),
      },
    );
    const responseBody = response.ok
      ? null
      : ((await response.json().catch(() => null)) as {
          detail?: string;
        } | null);
    setSaveMessage(
      response.ok
        ? action === "submit"
          ? "Role definition submitted."
          : "Role definition saved as a draft."
        : (responseBody?.detail ??
            (action === "submit"
              ? "Complete every required template field before submitting."
              : "Unable to save this role definition.")),
    );
    if (response.ok) {
      setDefinitionValues({});
      setSelected(null);
      await load();
    }
  }

  async function openManagerAssessment(
    member: TeamMember,
    type: "success-behaviours" | "functional-skills",
  ) {
    const response = await fetch(
      `${apiUrl}/skip-manager/assessments/${member.employee_id}`,
      { headers: { Authorization: `Bearer ${token}` } },
    );
    if (!response.ok) {
      setSaveMessage("Unable to load the employee assessment.");
      return;
    }
    setSelectedEmployee(member);
    setManagerType(type);
    setManagerAssessment((await response.json()) as ManagerAssessment);
    setPreviousAssessments(null);
    setSubmittedAssessment(null);
  }

  async function saveManagerAssessment(form: HTMLFormElement, submit: boolean) {
    if (!selectedEmployee || !managerAssessment) return;
    const items = (
      managerType === "success-behaviours"
        ? managerAssessment.success_behaviours
        : managerAssessment.functional_skills
    ).map((item) => ({
      item_id: item.item_id,
      self_assessment_level: Number(
        new FormData(form).get(`manager-${item.item_id}`),
      ),
    }));
    if (
      items.some(
        (item) =>
          item.self_assessment_level < 1 || item.self_assessment_level > 4,
      )
    ) {
      setSaveMessage("Select L1 to L4 for every item before saving.");
      return;
    }
    const response = await fetch(
      `${apiUrl}/skip-manager/assessments/${selectedEmployee.employee_id}/${managerType}${submit ? "/submit" : ""}`,
      {
        method: submit ? "POST" : "PUT",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ items }),
      },
    );
    if (!response.ok) {
      setSaveMessage(
        (
          await response
            .json()
            .catch(() => ({ detail: "Unable to save assessment." }))
        ).detail,
      );
      return;
    }
    setManagerAssessment((await response.json()) as ManagerAssessment);
    setSaveMessage(
      submit
        ? "Manager assessment submitted."
        : "Manager assessment saved as a draft.",
    );
    await load();
  }

  async function openPreviousAssessments(member: TeamMember) {
    const response = await fetch(
      `${apiUrl}/skip-manager/assessments/${member.employee_id}/previous`,
      { headers: { Authorization: `Bearer ${token}` } },
    );
    if (!response.ok) {
      setSaveMessage("Unable to load previous assessments.");
      return;
    }
    setSelectedEmployee(member);
    setPreviousAssessments((await response.json()) as PreviousAssessment[]);
    setManagerAssessment(null);
    setSubmittedAssessment(null);
  }

  async function openSubmittedAssessment(member: TeamMember) {
    const response = await fetch(
      `${apiUrl}/skip-manager/assessments/${member.employee_id}/submitted`,
      { headers: { Authorization: `Bearer ${token}` } },
    );
    const data = response.ok
      ? ((await response.json()) as SubmittedConsoleAssessment | null)
      : null;
    if (!data) {
      setSaveMessage("No submitted assessment is available for this employee.");
      return;
    }
    setSelectedEmployee(member);
    setManagerAssessment(null);
    setPreviousAssessments(null);
    setSubmittedAssessment(data);
  }

  async function openTeamRoleDefinition(member: TeamMember) {
    const response = await fetch(
      `${apiUrl}/skip-manager/team-members/${member.employee_id}/role-definition`,
      { headers: { Authorization: `Bearer ${token}` } },
    );
    const definition = response.ok
      ? ((await response.json()) as TeamRoleDefinition | null)
      : null;
    if (!definition) {
      setSaveMessage("This employee does not have a role definition available.");
      return;
    }
    setTeamRoleDefinition(definition);
  }

  function changeTab(tab: "role-definitions" | "assessments" | "gaps") {
    if (tab === "role-definitions" && !roleDefinitionStatusEnabled) return;
    setActive(tab);
    setSaveMessage("");
  }

  return (
    <main className="manager-shell">
      <header className="manager-header">
        <div className="manager-brand">
          <img src={activeTenantBrand.logoUrl} alt="KDDL" />
          <span>Talent Transformation</span>
        </div>
        <div>
          <span className="manager-user">
            {managerIdentity
              ? `${managerIdentity.full_name} · ${managerIdentity.employee_code}`
              : "Employee profile unavailable"}
          </span>
          <button onClick={onOpenEmployeeWorkspace}>My employee workspace</button>
          {user.admin_console_access && <button onClick={onOpenAdminConsole}>Admin Console</button>}
          {user.executive_review_access && <button onClick={onOpenExecutiveReview}>Executive Review</button>}
          <ChangePasswordAction onSignOut={onSignOut} />
          <button onClick={onSignOut}>Sign out</button>
        </div>
      </header>
      <section className="manager-hero">
        <p className="eyebrow">SKIP MANAGER / LEADERSHIP REVIEW</p>
        <h1>
          Team capability,
          <br />
          <em>made visible.</em>
        </h1>
        <p>
          Review role-definition readiness and assessment progress for your
          direct team.
        </p>
      </section>
      <nav className="manager-tabs" aria-label="Skip Manager options">
        <button
          className={active === "assessments" ? "active" : ""}
          onClick={() => changeTab("assessments")}
        >
          Team assessments
        </button>
        <button
          className={active === "gaps" ? "active" : ""}
          onClick={() => changeTab("gaps")}
        >
          See gaps
        </button>
        <button
          className={active === "role-definitions" ? "active" : ""}
          onClick={() => changeTab("role-definitions")}
          disabled={!roleDefinitionStatusEnabled}
          title="Temporarily unavailable"
        >
          Role definition status
        </button>
      </nav>
      <section className="manager-content">
        {!dashboard && (
          <p className="workspace-loading">Loading your team workspace…</p>
        )}
        {dashboard && active === "role-definitions" && (
          <>
            <div className="metric-grid">
              <article>
                <b>{dashboard.role_definition_status.not_started}</b>
                <span>Not Started</span>
              </article>
              <article>
                <b>{dashboard.role_definition_status.draft}</b>
                <span>Draft</span>
              </article>
              <article>
                <b>{dashboard.role_definition_status.submitted}</b>
                <span>Submitted</span>
              </article>
            </div>
            <div className="panel-header">
              <div>
                <p className="eyebrow">MAPPED ROLE DEFINITIONS</p>
                <h2>Roles assigned to you</h2>
              </div>
            </div>
            <AssignedRolesTable
              roles={dashboard.assigned_roles}
              onOpen={openDefinition}
            />
            {saveMessage && <p className="save-message">{saveMessage}</p>}
          </>
        )}
        {dashboard && active === "assessments" && (
          <>
            <div className="metric-grid">
              <article>
                <b>{dashboard.team_size}</b>
                <span>Team members</span>
              </article>
              <article>
                <b>{dashboard.pending_employee_sections}</b>
                <span>Pending employee sections</span>
              </article>
              <article>
                <b>{dashboard.pending_manager_sections}</b>
                <span>Pending manager sections</span>
              </article>
            </div>
            <div className="panel-header">
              <div>
                <p className="eyebrow">ASSESSMENT PROGRESS</p>
                <h2>Team assessment status</h2>
                <p className="cycle-period">
                  {dashboard.active_cycle
                    ? `${dashboard.active_cycle.name} · ${formatDisplayDate(dashboard.active_cycle.period_start)} to ${formatDisplayDate(dashboard.active_cycle.period_end)}`
                    : "No active assessment cycle"}
                </p>
              </div>
            </div>
            <AssessmentTable
              members={dashboard.team}
              onAssess={openManagerAssessment}
              onPrevious={openPreviousAssessments}
              onViewSubmitted={openSubmittedAssessment}
              onViewRoleDefinition={openTeamRoleDefinition}
            />
            <AssessmentLegend includeStatuses />
          </>
        )}
        {dashboard && active === "gaps" && (
          <>
            <div className="metric-grid">
              <article>
                <b>{dashboard.employees_with_gaps}</b>
                <span>Employees with gaps</span>
              </article>
              <article>
                <b>{dashboard.behaviour_gap_items}</b>
                <span>Behaviour gap items</span>
              </article>
              <article>
                <b>{dashboard.functional_gap_items}</b>
                <span>Functional skill gap items</span>
              </article>
            </div>
            <div className="panel-header">
              <div>
                <p className="eyebrow">CAPABILITY GAPS</p>
                <h2>Success Behaviours</h2>
              </div>
            </div>
            <GapMatrixTable
              matrix={gapMatrices?.success_behaviours}
              kind="Behaviour"
            />
            <div className="panel-header gap-section-header">
              <div>
                <p className="eyebrow">CAPABILITY GAPS</p>
                <h2>Functional Skills</h2>
              </div>
            </div>
            <GapMatrixTable
              matrix={gapMatrices?.functional_skills}
              kind="Functional skill"
            />
            <AssessmentLegend />
          </>
        )}
      </section>
      {selected && (
        <RoleDefinitionTemplate
          key={`${selected.role_id}-${JSON.stringify(definitionValues)}`}
          role={{
            ...selected,
            grade_band_code: selected.grade_band_code ?? "To be confirmed",
          }}
          values={definitionValues}
          isReadOnly={
            selected.description_status === "SUBMITTED" ||
            selected.description_status === "VALIDATED"
          }
          onSubmit={saveDefinition}
          onClose={() => setSelected(null)}
        />
      )}
      {selectedEmployee && managerAssessment && (
        <div className="dialog-backdrop">
          <section className="role-dialog manager-assessment-dialog">
            <button className="close" onClick={() => setSelectedEmployee(null)}>
              Close
            </button>
            <p className="eyebrow">
              MANAGER ASSESSMENT · {selectedEmployee.full_name}
            </p>
            <h2>
              {managerType === "success-behaviours"
                ? "Success Behaviours"
                : "Functional Skills"}
            </h2>
            <p>
              {managerAssessment.cycle.name}. Review the employee’s self-rating
              and submit your manager rating.
            </p>
            <ManagerAssessmentForm
              assessment={managerAssessment}
              type={managerType}
              onSave={saveManagerAssessment}
            />
          </section>
        </div>
      )}
      {selectedEmployee && previousAssessments && (
        <div className="dialog-backdrop">
          <section className="role-dialog manager-assessment-dialog">
            <button className="close" onClick={() => setSelectedEmployee(null)}>
              Close
            </button>
            <p className="eyebrow">
              ASSESSMENT HISTORY · {selectedEmployee.full_name}
            </p>
            <h2>Previous cycles</h2>
            <PreviousAssessments cycles={previousAssessments} />
          </section>
        </div>
      )}
      {submittedAssessment && (
        <div className="dialog-backdrop">
          <section className="role-dialog submitted-assessment" role="dialog" aria-modal="true">
            <button className="close" aria-label="Close submitted assessment" onClick={() => setSubmittedAssessment(null)}>Close</button>
            <p className="eyebrow">SUBMITTED ASSESSMENT · READ ONLY</p>
            <h2>{submittedAssessment.employee.full_name}</h2>
            <p>{submittedAssessment.employee.employee_code} · {submittedAssessment.employee.division_name}</p>
            {([['Success Behaviours', submittedAssessment.success_behaviours], ['Functional Skills', submittedAssessment.functional_skills]] as const).map(([title, items]) => (
              <section key={title}>
                <h3>{title}</h3>
                {items.length ? <table><thead><tr><th>Skill Name</th><th>DL</th><th>SAL</th><th>MAL</th><th>Gap</th></tr></thead><tbody>{items.map((item) => <tr key={item.item_id}><td>{item.item_name}</td><td>{item.desired_level}</td><td>{item.self_assessment_level ?? '—'}</td><td>{item.manager_assessment_level ?? '—'}</td><td className={item.gap !== null && item.gap < 0 ? 'negative-gap' : ''}>{item.gap ?? '—'}</td></tr>)}</tbody></table> : <p>No submitted items.</p>}
              </section>
            ))}
            <AssessmentLegend />
          </section>
        </div>
      )}
      {teamRoleDefinition && (
        <div className="dialog-backdrop">
          <section className="role-dialog team-role-definition" role="dialog" aria-modal="true" aria-labelledby="team-role-definition-title">
            <button className="close" aria-label="Close role definition" onClick={() => setTeamRoleDefinition(null)}>Close</button>
            <p className="eyebrow">EMPLOYEE ROLE DEFINITION</p>
            <h2 id="team-role-definition-title">{teamRoleDefinition.role_title}</h2>
            <p>{teamRoleDefinition.full_name} · {teamRoleDefinition.employee_code}</p>
            <h3>Role definition</h3>
            <p className="preserve-lines">{teamRoleDefinition.role_definition || "Not available"}</p>
            <h3>Key responsibilities</h3>
            <p className="preserve-lines">{teamRoleDefinition.key_responsibilities || "Not available"}</p>
            <h3>KPIs</h3>
            <p className="preserve-lines">{teamRoleDefinition.kpis || "Not available"}</p>
            <h3>Knowledge required</h3>
            <p className="preserve-lines">{teamRoleDefinition.knowledge_required || "Not available"}</p>
            <h3>Skills required</h3>
            <p className="preserve-lines">{teamRoleDefinition.skills_required || "Not available"}</p>
            <h3>Attitudes &amp; behaviours</h3>
            <p className="preserve-lines">{teamRoleDefinition.attitudes_behaviours || "Not available"}</p>
          </section>
        </div>
      )}
    </main>
  );
}

function TeamTable({
  members,
  show,
  empty = "No direct team members were found.",
  onOpen,
}: {
  members: TeamMember[];
  show: "role" | "assessment" | "gaps";
  empty?: string;
  onOpen?: (member: TeamMember) => void;
}) {
  if (!members.length) return <div className="empty-state">{empty}</div>;
  return (
    <div className="team-table">
      {members.map((member) => (
        <article key={member.employee_id}>
          <div>
            <b>{member.full_name}</b>
            <span>
              {member.designation} · {member.role_title ?? "Role not assigned"}
            </span>
          </div>
          {show === "role" && (
            <div className="role-row-action">
              <span
                className={`status ${member.description_status?.toLowerCase()}`}
              >
                {member.description_status?.replaceAll("_", " ") ??
                  "Not started"}
              </span>
              <button className="text-action" onClick={() => onOpen?.(member)}>
                {member.description_status === "DRAFT"
                  ? "Continue draft"
                  : member.description_status === "SUBMITTED"
                    ? "View submitted"
                    : "Open"}
              </button>
            </div>
          )}
          {show === "gaps" && (
            <span className="gap-count">
              {member.gap_items} gap item{member.gap_items === 1 ? "" : "s"}
            </span>
          )}
        </article>
      ))}
    </div>
  );
}

function AssessmentTable({
  members,
  onAssess,
  onPrevious,
  onViewSubmitted,
  onViewRoleDefinition,
}: {
  members: TeamMember[];
  onAssess: (
    member: TeamMember,
    type: "success-behaviours" | "functional-skills",
  ) => void;
  onPrevious: (member: TeamMember) => void;
  onViewSubmitted: (member: TeamMember) => void;
  onViewRoleDefinition: (member: TeamMember) => void;
}) {
  if (!members.length)
    return (
      <div className="empty-state">No direct team members were found.</div>
    );
  return (
    <div className="assessment-table team-assessment-table">
      <div className="assessment-head">
        <span>Employee</span>
        <span>SB · Employee</span>
        <span>SB · Manager</span>
        <span>FS · Employee</span>
        <span>FS · Manager</span>
        <span>Assessment reports</span>
      </div>
      {members.map((member) => (
        <article key={member.employee_id}>
          <div>
            <b>{member.full_name}</b>
            <div className="team-role-line">
              <span>{member.designation} · {member.role_title ?? "Role not assigned"}</span>
              {member.role_title && <button className="role-definition-icon" type="button" title="View role definition" aria-label={`View role definition for ${member.full_name}`} onClick={() => onViewRoleDefinition(member)}><svg viewBox="0 0 16 16" aria-hidden="true"><path d="M4 1.5h5l3 3v10H4zM9 1.5v3h3M6 8h4M6 10.5h4" /></svg></button>}
            </div>
          </div>
          <AssessmentProgress
            status={member.behaviour_employee_status}
            onAssess={() => undefined}
          />
          <AssessmentProgress
            status={member.behaviour_manager_status}
            canAssess={member.behaviour_employee_status === "COMPLETED"}
            onAssess={() => onAssess(member, "success-behaviours")}
          />
          <AssessmentProgress
            status={member.functional_employee_status}
            onAssess={() => undefined}
          />
          <AssessmentProgress
            status={member.functional_manager_status}
            canAssess={member.functional_employee_status === "COMPLETED"}
            onAssess={() => onAssess(member, "functional-skills")}
          />
          <div className="assessment-report-actions">
            {(member.behaviour_employee_status === "COMPLETED" || member.functional_employee_status === "COMPLETED") && <button className="text-action" onClick={() => onViewSubmitted(member)}>View submitted</button>}
            <button className="text-action" onClick={() => onPrevious(member)}>Previous cycles</button>
          </div>
        </article>
      ))}
    </div>
  );
}

function AssessmentProgress({
  status,
  canAssess = true,
  onAssess,
}: {
  status: AssessmentStatus;
  canAssess?: boolean;
  onAssess: () => void;
}) {
  return (
    <div className="assessment-progress">
      <span className={`status ${status.toLowerCase()}`}>
        {status.replaceAll("_", " ")}
      </span>
      {status === "PENDING_WITH_MANAGER" && canAssess && (
        <button className="text-action" onClick={onAssess}>
          Assess & submit
        </button>
      )}
    </div>
  );
}

function ManagerAssessmentForm({
  assessment,
  type,
  onSave,
}: {
  assessment: ManagerAssessment;
  type: "success-behaviours" | "functional-skills";
  onSave: (form: HTMLFormElement, submit: boolean) => void;
}) {
  const items =
    type === "success-behaviours"
      ? assessment.success_behaviours
      : assessment.functional_skills;
  const isSubmitted =
    type === "success-behaviours"
      ? assessment.behaviour_is_submitted
      : assessment.functional_is_submitted;
  if (!items.length)
    return (
      <div className="empty-state">
        No assessment items have been configured for this section.
      </div>
    );
  return (
    <form
      className="employee-assessment-form"
      onSubmit={(event) => {
        event.preventDefault();
        if (!isSubmitted) void onSave(event.currentTarget, true);
      }}
    >
      {isSubmitted && (
        <p className="save-message">Submitted assessment — view only.</p>
      )}
      {items.map((item) => (
        <article key={item.item_id}>
          <div>
            <b>
              {item.code} · {item.name}
              <LevelDefinitionButton itemType={type} itemId={item.item_id} />
            </b>
            <p>{item.definition}</p>
            <span>
              Desired level: L{item.desired_level} · Employee self-rating{" "}
              {item.self_assessment_level === null
                ? "Pending"
                : `L${item.self_assessment_level}`}
            </span>
          </div>
          <label>
            Manager level
            <select
              name={`manager-${item.item_id}`}
              defaultValue={item.manager_assessment_level ?? ""}
              required
              disabled={isSubmitted}
            >
              <option value="" disabled>
                Select level
              </option>
              {[1, 2, 3, 4].map((level) => (
                <option value={level} key={level}>
                  L{level}
                </option>
              ))}
            </select>
          </label>
        </article>
      ))}
      {!isSubmitted && (
        <div className="template-actions">
          <button
            className="secondary"
            type="button"
            onClick={(event) => {
              const form = event.currentTarget.form;
              if (form) void onSave(form, false);
            }}
          >
            Save draft
          </button>
          <button className="primary" type="submit">
            Submit manager assessment
          </button>
        </div>
      )}
    </form>
  );
}

function GapMatrixTable({
  matrix,
  kind,
}: {
  matrix: GapMatrix | undefined;
  kind: string;
}) {
  if (!matrix?.rows.length || !matrix.items.length)
    return (
      <div className="empty-state">
        No {kind.toLowerCase()} assessment results are available for this team
        yet.
      </div>
    );
  const display = (value: number | null | undefined) => value ?? "—";
  const isFunctionalSkillMatrix = kind === "Functional skill";
  const items = isFunctionalSkillMatrix
    ? matrix.items
    : matrix.items;
  const functionalSlots = [1, 2, 3, 4, 5, 6, 7];
  return (
    <div className="gap-matrix-wrap">
      <table className="gap-matrix">
        <thead>
          <tr>
            <th colSpan={6}>Employee Information</th>
            {isFunctionalSkillMatrix
              ? functionalSlots.map((slot) => (
                  <th colSpan={5} key={`skill-${slot}`}>
                    Skill {slot}
                  </th>
                ))
              : items.map((item, index) => (
                  <th colSpan={4} key={item.item_id}>
                    {kind} {index + 1}: {item.name}
                  </th>
                ))}
          </tr>
          <tr>
            <th>#</th>
            <th>Emp Code</th>
            <th>Name</th>
            <th>Role</th>
            <th>Grade</th>
            <th>Designation</th>
            {isFunctionalSkillMatrix
              ? functionalSlots.flatMap((slot) => [
                  <th key={`skill-${slot}-name`}>Skill name</th>,
                  <th key={`skill-${slot}-desired`}>Desired Level</th>,
                  <th key={`skill-${slot}-self`}>Self Assessment</th>,
                  <th key={`skill-${slot}-manager`}>Mgr Assessment</th>,
                  <th key={`skill-${slot}-gap`}>Gap</th>,
                ])
              : items.flatMap((item) => [
                  <th key={`${item.item_id}-desired`}>Desired Level</th>,
                  <th key={`${item.item_id}-self`}>Self Assessment</th>,
                  <th key={`${item.item_id}-manager`}>Mgr Assessment</th>,
                  <th key={`${item.item_id}-gap`}>Gap</th>,
                ])}
          </tr>
        </thead>
        <tbody>
          {matrix.rows.map((row, rowIndex) => (
            <tr key={row.employee_id}>
              <td>{rowIndex + 1}</td>
              <td>{row.employee_code}</td>
              <td>{row.full_name}</td>
              <td>{row.role_title ?? "—"}</td>
              <td>{row.grade_band_code ?? "—"}</td>
              <td>{row.designation}</td>
              {(isFunctionalSkillMatrix
                ? functionalSlots.map((slot) =>
                    matrix.items.filter(
                      (item) => row.values[String(item.item_id)] !== undefined,
                    )[slot - 1],
                  )
                : items
              ).flatMap((item, index) => {
                if (!item) {
                  return [
                    <td key={`empty-${index}-name`}>—</td>,
                    <td key={`empty-${index}-desired`}>—</td>,
                    <td key={`empty-${index}-self`}>—</td>,
                    <td key={`empty-${index}-manager`}>—</td>,
                    <td key={`empty-${index}-gap`}>—</td>,
                  ];
                }
                const value = row.values[String(item.item_id)];
                return [
                  ...(isFunctionalSkillMatrix
                    ? [
                        <td key={`${item.item_id}-name`}>
                          {value ? item.name : "—"}
                        </td>,
                      ]
                    : []),
                  <td key={`${item.item_id}-desired`}>
                    {display(value?.desired_level)}
                  </td>,
                  <td key={`${item.item_id}-self`}>
                    {display(value?.self_assessment_level)}
                  </td>,
                  <td key={`${item.item_id}-manager`}>
                    {display(value?.manager_assessment_level)}
                  </td>,
                  <td
                    className={
                      value?.gap !== undefined &&
                      value.gap !== null &&
                      value.gap < 0
                        ? "negative-gap"
                        : ""
                    }
                    key={`${item.item_id}-gap`}
                  >
                    {display(value?.gap)}
                  </td>,
                ];
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function AssignedRolesTable({
  roles,
  onOpen,
}: {
  roles: AssignedRole[];
  onOpen: (role: AssignedRole) => void;
}) {
  if (!roles.length)
    return (
      <div className="empty-state">
        No role definitions have been mapped to you yet.
      </div>
    );
  return (
    <div className="team-table">
      {roles.map((role) => (
        <article key={role.role_id}>
          <div>
            <b>{role.role_title}</b>
            <span>
              {role.function_name} ·{" "}
              {role.department_name ?? "Department to be confirmed"} ·{" "}
              {role.grade_band_code ?? "Grade to be confirmed"}
            </span>
          </div>
          <div className="role-row-action">
            <span className={`status ${role.description_status.toLowerCase()}`}>
              {role.description_status.replaceAll("_", " ")}
            </span>
            <button className="text-action" onClick={() => onOpen(role)}>
              {role.description_status === "DRAFT"
                ? "Continue draft"
                : role.description_status === "SUBMITTED"
                  ? "View submitted"
                  : "Open"}
            </button>
          </div>
        </article>
      ))}
    </div>
  );
}

function EmployeeWorkspace({
  user,
  onSignOut,
  onOpenAdminConsole,
  onOpenManagerWorkspace,
}: {
  user: CurrentUser;
  onSignOut: () => void;
  onOpenAdminConsole: () => void;
  onOpenManagerWorkspace: () => void;
}) {
  const [dashboard, setDashboard] = useState<EmployeeDashboard | null>(null);
  const [role, setRole] = useState<EmployeeRole | null>(null);
  const [assessment, setAssessment] = useState<EmployeeAssessment | null>(null);
  const [previous, setPrevious] = useState<PreviousAssessment[]>([]);
  const [active, setActive] = useState("role");
  const [message, setMessage] = useState("");
  const token = sessionStorage.getItem("kddl_access_token") ?? "";
  const headers = { Authorization: `Bearer ${token}` };

  async function load() {
    const [dashboardResponse, roleResponse] = await Promise.all([
      fetch(`${apiUrl}/employee/dashboard`, { headers }),
      fetch(`${apiUrl}/employee/role`, { headers }),
    ]);
    if (!dashboardResponse.ok || !roleResponse.ok)
      throw new Error("Unable to load your employee workspace.");
    setDashboard((await dashboardResponse.json()) as EmployeeDashboard);
    setRole((await roleResponse.json()) as EmployeeRole | null);
  }
  useEffect(() => {
    load().catch((error) => setMessage(error.message));
  }, []);

  async function openRole() {
    setActive("role");
    setAssessment(null);
    setMessage("");
    const response = await fetch(`${apiUrl}/employee/role`, { headers });
    if (!response.ok) {
      setMessage("Unable to load your role description.");
      return;
    }
    setRole((await response.json()) as EmployeeRole | null);
  }

  async function openAssessment(
    type: "success-behaviours" | "functional-skills",
  ) {
    setMessage("");
    setAssessment(null);
    setActive(type);
    let response = await fetch(`${apiUrl}/employee/assessments/${type}`, {
      headers,
    });
    let data = response.ok
      ? ((await response.json()) as EmployeeAssessment | null)
      : null;
    if (!data) {
      response = await fetch(`${apiUrl}/employee/assessments/${type}/start`, {
        method: "POST",
        headers,
      });
      if (!response.ok) {
        setMessage(
          (
            await response
              .json()
              .catch(() => ({ detail: "Unable to start the assessment." }))
          ).detail,
        );
        return;
      }
      data = (await response.json()) as EmployeeAssessment;
    }
    setAssessment(data);
  }

  async function openPrevious() {
    setActive("previous");
    setAssessment(null);
    setMessage("");
    const response = await fetch(`${apiUrl}/employee/assessments/previous`, {
      headers,
    });
    if (!response.ok) {
      setMessage("Unable to load previous assessments.");
      return;
    }
    setPrevious((await response.json()) as PreviousAssessment[]);
  }

  async function saveAssessment(form: HTMLFormElement, submit: boolean) {
    const type = active as "success-behaviours" | "functional-skills";
    const values = new FormData(form);
    const items =
      assessment?.items.map((item) => ({
        item_id: item.item_id,
        self_assessment_level: Number(values.get(`level-${item.item_id}`)),
      })) ?? [];
    if (
      items.some(
        (item) =>
          item.self_assessment_level < 1 || item.self_assessment_level > 4,
      )
    ) {
      setMessage("Select a level from L1 to L4 for every item.");
      return;
    }
    const response = await fetch(
      `${apiUrl}/employee/assessments/${type}${submit ? "/submit" : ""}`,
      {
        method: submit ? "POST" : "PUT",
        headers: { ...headers, "Content-Type": "application/json" },
        body: JSON.stringify({ items }),
      },
    );
    if (!response.ok) {
      setMessage(
        (
          await response
            .json()
            .catch(() => ({ detail: "Unable to save assessment." }))
        ).detail,
      );
      return;
    }
    setAssessment((await response.json()) as EmployeeAssessment);
    setMessage(
      submit ? "Assessment submitted." : "Assessment saved as a draft.",
    );
    await load();
  }

  return (
    <main className="workspace-shell employee-shell">
      <aside className="workspace-nav">
        <div className="workspace-brand">
          <img
            src={activeTenantBrand.logoUrl}
            alt={activeTenantBrand.tenantName}
          />
          <span>Talent Transformation</span>
        </div>
        <p className="workspace-role">My development</p>
        <nav aria-label="Employee navigation">
          <button
            className={active === "role" ? "active" : ""}
            onClick={() => openRole().catch((error) => setMessage(error.message))}
          >
            <b>01</b>My Role
          </button>
          <button
            className={active === "success-behaviours" ? "active" : ""}
            onClick={() => openAssessment("success-behaviours")}
          >
            <b>02</b>Success Behaviour
          </button>
          <button
            className={active === "functional-skills" ? "active" : ""}
            onClick={() => openAssessment("functional-skills")}
          >
            <b>03</b>Functional Skills
          </button>
          <button
            className={active === "previous" ? "active" : ""}
            onClick={openPrevious}
          >
            <b>04</b>Previous Assessments
          </button>
          {user.is_manager && <button onClick={onOpenManagerWorkspace}><b>05</b>Manager Workspace</button>}
          <ChangePasswordAction onSignOut={onSignOut} navigation navigationNumber={user.is_manager ? "06" : "05"} />
        </nav>
        {user.admin_console_access && <button className="password-action" onClick={onOpenAdminConsole}>Admin Console</button>}
        <button className="sign-out" onClick={onSignOut}>
          Sign out
        </button>
      </aside>
      <section className="workspace-content">
        <header>
          <p className="eyebrow">{active === "role" ? "MY ROLE" : "EMPLOYEE"}</p>
          <div className="employee-identity">
            <b>{dashboard?.employee.full_name ?? user.email}</b>
            <span>
              {dashboard
                ? `Employee code: ${dashboard.employee.employee_code}`
                : user.email}
            </span>
          </div>
        </header>
        {!dashboard && (
          <p className="workspace-loading">Loading your workspace…</p>
        )}
        {dashboard && (
          <>
            {active !== "role" && active !== "previous" && (
              <div className="workspace-intro employee-intro">
                <p className="eyebrow">MY ASSESSMENT CYCLE</p>
                <div className="cycle-summary">
                  <h1>{dashboard.active_cycle?.name ?? "No active assessment cycle"}</h1>
                  <span>
                  {dashboard.active_cycle
                    ? `${formatDisplayDate(dashboard.active_cycle.period_start)} to ${formatDisplayDate(dashboard.active_cycle.period_end)}`
                    : "Your HR team has not opened an assessment cycle yet."}
                  </span>
                </div>
              </div>
            )}
            {active === "role" && (
              <section className="employee-panel">
                <h2>{role?.title ?? "Role not assigned"}</h2>
                {role?.role_definition ? (
                  <>
                    <h3>Role definition</h3>
                    <p>{role.role_definition}</p>
                    <h3>Key responsibilities</h3>
                    <p className="preserve-lines">
                      {role.key_responsibilities}
                    </p>
                    <h3>KPIs</h3>
                    <p className="preserve-lines">{role.kpis || "Not available"}</p>
                    <h3>Knowledge required</h3>
                    <p className="preserve-lines">{role.knowledge_required || "Not available"}</p>
                    <h3>Skills required</h3>
                    <p className="preserve-lines">{role.skills_required || "Not available"}</p>
                    <h3>Attitudes &amp; behaviours</h3>
                    <p className="preserve-lines">{role.attitudes_behaviours || "Not available"}</p>
                  </>
                ) : (
                  <div className="empty-state">
                    Your role description is not available yet.
                  </div>
                )}
              </section>
            )}
            {(active === "success-behaviours" ||
              active === "functional-skills") && (
              <section className="employee-panel">
                {assessment ? (
                  <EmployeeAssessmentForm
                    assessment={assessment}
                    kind={
                      active === "success-behaviours"
                        ? "Success Behaviour"
                        : "Functional Skills"
                    }
                    message={message}
                    onSave={saveAssessment}
                  />
                ) : (
                  <div className="empty-state">
                    {message || "Opening your assessment…"}
                  </div>
                )}
              </section>
            )}
            {active === "previous" && (
              <section className="employee-panel">
                <p className="eyebrow">ASSESSMENT HISTORY</p>
                <h2>Previous assessments</h2>
                <PreviousAssessments cycles={previous} />
              </section>
            )}
            <div className="employee-status-grid">
              <button onClick={() => openAssessment("success-behaviours")}>
                <span>Success Behaviour</span>
                <b
                  className={`status ${dashboard.success_behaviours_status.toLowerCase()}`}
                >
                  {dashboard.success_behaviours_status}
                </b>
              </button>
              <button onClick={() => openAssessment("functional-skills")}>
                <span>Functional Skills</span>
                <b
                  className={`status ${dashboard.functional_skills_status.toLowerCase()}`}
                >
                  {dashboard.functional_skills_status}
                </b>
              </button>
            </div>
            {message &&
              active !== "success-behaviours" &&
              active !== "functional-skills" && (
                <p className="save-message">{message}</p>
              )}
          </>
        )}
      </section>
    </main>
  );
}

function EmployeeAssessmentForm({
  assessment,
  kind,
  message,
  onSave,
}: {
  assessment: EmployeeAssessment;
  kind: string;
  message: string;
  onSave: (form: HTMLFormElement, submit: boolean) => void;
}) {
  return (
    <>
      <p className="eyebrow">SELF ASSESSMENT</p>
      <h2>{kind}</h2>
      <p className="assessment-cycle-label">
        Select your current proficiency level from L1 to L4.
      </p>
      <form
        className="employee-assessment-form"
        onSubmit={(event) => {
          event.preventDefault();
          if (!assessment.is_submitted) void onSave(event.currentTarget, true);
        }}
      >
        {assessment.is_submitted && (
          <p className="save-message">Submitted assessment — view only.</p>
        )}
        {assessment.items.map((item) => (
          <article key={item.item_id}>
            <div>
              <b>
                {item.code} · {item.name}
                <LevelDefinitionButton itemType={kind === "Success Behaviour" ? "success-behaviours" : "functional-skills"} itemId={item.item_id} />
              </b>
              <p>{item.definition}</p>
              <span>Desired level: L{item.desired_level}</span>
            </div>
            <label>
              My level
              <select
                name={`level-${item.item_id}`}
                defaultValue={item.self_assessment_level ?? ""}
                required
                disabled={assessment.is_submitted}
              >
                <option value="" disabled>
                  Select level
                </option>
                {[1, 2, 3, 4].map((level) => (
                  <option value={level} key={level}>
                    L{level}
                  </option>
                ))}
              </select>
            </label>
          </article>
        ))}
        {!assessment.is_submitted && (
          <div className="template-actions">
            <button
              className="secondary"
              type="button"
              onClick={(event) => {
                const form = event.currentTarget.form;
                if (form) void onSave(form, false);
              }}
            >
              Save draft
            </button>
            <button className="primary" type="submit">
              Submit assessment
            </button>
          </div>
        )}
      </form>
      {message && <p className="save-message">{message}</p>}
    </>
  );
}

function PreviousAssessments({
  cycles,
  showDesired = true,
}: {
  cycles: PreviousAssessment[];
  showDesired?: boolean;
}) {
  if (!cycles.length)
    return (
      <div className="empty-state">
        No closed assessment cycles are available yet.
      </div>
    );
  const level = (value: number | null) => (value === null ? "—" : `L${value}`);
  return (
    <div className="previous-cycles">
      {cycles.map((cycle) => (
        <article key={cycle.cycle_id}>
          <div className="cycle-summary">
            <h3>{cycle.name}</h3>
            <span>{formatDisplayDate(cycle.period_start)} to {formatDisplayDate(cycle.period_end)}</span>
          </div>
          {(["success_behaviours", "functional_skills"] as const).map(
            (type) => (
              <div key={type}>
                <h4>
                  {type === "success_behaviours"
                    ? "Success Behaviours"
                    : "Functional Skills"}
                </h4>
                {cycle[type].length ? (
                  <table>
                    <thead>
                      <tr>
                        <th>Skill Name</th>
                        {showDesired && <th>DL</th>}
                        <th>Self</th>
                        <th>Manager</th>
                        <th>Gap</th>
                      </tr>
                    </thead>
                    <tbody>
                      {cycle[type].map((item) => (
                        <tr key={item.item_id}>
                          <td>{item.item_name}</td>
                          {showDesired && <td>{level(item.desired_level)}</td>}
                          <td>{level(item.self_assessment_level)}</td>
                          <td>{level(item.manager_assessment_level)}</td>
                          <td className={item.gap !== null && item.gap < 0 ? "negative-gap" : ""}>{item.gap ?? "—"}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                ) : (
                  <p>No items recorded.</p>
                )}
              </div>
            ),
          )}
        </article>
      ))}
      <AssessmentLegend />
    </div>
  );
}

function AdminConsoleWorkspace({ user, onSignOut, onClose }: { user: CurrentUser; onSignOut: () => void; onClose?: () => void }) {
  const [report, setReport] = useState<AdminReport | null>(null);
  const [divisionId, setDivisionId] = useState("");
  const [cycleId, setCycleId] = useState("");
  const [employeeName, setEmployeeName] = useState("");
  const [page, setPage] = useState(1);
  const [message, setMessage] = useState("");
  const [submittedAssessment, setSubmittedAssessment] = useState<SubmittedConsoleAssessment | null>(null);
  const token = sessionStorage.getItem("kddl_access_token") ?? "";
  async function load(division = divisionId, cycle = cycleId, requestedPage = page, name = employeeName) {
    const query = new URLSearchParams();
    if (division) query.set("division_id", division);
    if (cycle) query.set("cycle_id", cycle);
    if (name.trim()) query.set("employee_name", name.trim());
    query.set("page", String(requestedPage));
    query.set("page_size", "10");
    const response = await fetch(`${apiUrl}/admin-console/assessment-report?${query}`, { headers: { Authorization: `Bearer ${token}` } });
    if (!response.ok) throw new Error("Unable to load the assessment report.");
    const data = (await response.json()) as AdminReport;
    setReport(data);
    setPage(data.page);
    if (!cycle && data.selected_cycle_id) setCycleId(String(data.selected_cycle_id));
  }
  useEffect(() => { load().catch((error) => setMessage(error.message)); }, []);
  const status = (value: AssessmentStatus) => <span className={`status ${value.toLowerCase()}`}>{value.replaceAll("_", " ")}</span>;
  async function viewSubmitted(employeeId: number) {
    if (!report?.selected_cycle_id) return;
    const response = await fetch(`${apiUrl}/admin-console/assessments/${employeeId}?cycle_id=${report.selected_cycle_id}`, { headers: { Authorization: `Bearer ${token}` } });
    const data = response.ok ? await response.json() as SubmittedConsoleAssessment | null : null;
    if (!data) { setMessage("No submitted assessment is available for this employee in the selected cycle."); return; }
    setSubmittedAssessment(data);
  }
  return <main className="manager-shell admin-console">
    <header className="manager-header"><div className="manager-brand"><img src={activeTenantBrand.logoUrl} alt="KDDL" /><span>Admin Console</span></div><div><span className="manager-user">{user.email}</span>{onClose && <button onClick={onClose}>Back to workspace</button>}<ChangePasswordAction onSignOut={onSignOut} /><button onClick={onSignOut}>Sign out</button></div></header>
    <section className="manager-hero"><p className="eyebrow">HR ASSESSMENT OVERSIGHT</p><h1>Assessment status,<br /><em>across every entity.</em></h1><p>Review employee and manager completion separately for Success Behaviour and Functional Skills, then focus on the reported gaps.</p></section>
    <section className="manager-content">
      <div className="admin-filters"><label>Entity<select value={divisionId} onChange={(event) => { setDivisionId(event.target.value); load(event.target.value, cycleId, 1).catch((error) => setMessage(error.message)); }}><option value="">All entities</option>{report?.divisions.map((division) => <option key={division.division_id} value={division.division_id}>{division.name}</option>)}</select></label><label>Assessment cycle<select value={cycleId} onChange={(event) => { setCycleId(event.target.value); load(divisionId, event.target.value, 1).catch((error) => setMessage(error.message)); }}>{report?.cycles.map((cycle) => <option key={cycle.cycle_id} value={cycle.cycle_id}>{cycle.name}</option>)}</select></label><form className="employee-search" onSubmit={(event) => { event.preventDefault(); load(divisionId, cycleId, 1, employeeName).catch((error) => setMessage(error.message)); }}><label>Employee name<input value={employeeName} onChange={(event) => setEmployeeName(event.target.value)} placeholder="Search by employee name" /></label><button className="primary" type="submit">Search</button>{employeeName && <button className="text-action" type="button" onClick={() => { setEmployeeName(""); load(divisionId, cycleId, 1, "").catch((error) => setMessage(error.message)); }}>Clear</button>}</form></div>
      {report && <div className="metric-grid admin-metrics"><article><b>{report.summary.employees}</b><span>Employees in scope</span></article><article><b>{report.summary.behaviour_self_pending + report.summary.functional_self_pending}</b><span>Self-assessment sections pending</span></article><article><b>{report.summary.behaviour_manager_pending + report.summary.functional_manager_pending}</b><span>Manager sections pending</span></article><article><b>{report.summary.behaviour_gaps + report.summary.functional_gaps}</b><span>Reported gap items</span></article></div>}
      <div className="panel-header"><div><p className="eyebrow">CYCLE STATUS</p><h2>Manager assessment status</h2></div></div>
      {message && <p className="form-error">{message}</p>}
      {!report ? <p className="workspace-loading">Loading assessment report…</p> : <><div className="admin-table-wrap"><table className="admin-table"><thead><tr><th>Entity / employee</th><th>Manager</th><th>Behaviour self</th><th>Behaviour manager</th><th>Functional self</th><th>Functional manager</th><th>Behaviour gaps</th><th>Functional gaps</th><th>Submitted assessment</th></tr></thead><tbody>{report.employees.map((employee) => <tr key={employee.employee_id}><td><b>{employee.full_name}</b><span>{employee.employee_code} · {employee.division_name}</span></td><td>{employee.manager_name ?? "Not assigned"}</td><td>{status(employee.behaviour_self_status)}</td><td>{status(employee.behaviour_manager_status)}</td><td>{status(employee.functional_self_status)}</td><td>{status(employee.functional_manager_status)}</td><td className={employee.behaviour_gaps > 0 ? "negative-gap" : ""}>{employee.behaviour_gaps}</td><td className={employee.functional_gaps > 0 ? "negative-gap" : ""}>{employee.functional_gaps}</td><td>{employee.behaviour_self_status === "COMPLETED" || employee.functional_self_status === "COMPLETED" ? <button className="text-action" onClick={() => viewSubmitted(employee.employee_id)}>View</button> : "—"}</td></tr>)}</tbody></table></div><AssessmentLegend includeStatuses /><div className="pagination"><span>Showing {report.employees.length ? (report.page - 1) * report.page_size + 1 : 0}–{Math.min(report.page * report.page_size, report.total_employees)} of {report.total_employees} employees</span><button disabled={report.page === 1} onClick={() => load(divisionId, cycleId, report.page - 1)}>Previous</button><button disabled={report.page * report.page_size >= report.total_employees} onClick={() => load(divisionId, cycleId, report.page + 1)}>Next</button></div></>}
      {submittedAssessment && <div className="dialog-backdrop"><section className="role-dialog submitted-assessment" role="dialog" aria-modal="true"><button className="close" aria-label="Close submitted assessment" onClick={() => setSubmittedAssessment(null)}>Close</button><p className="eyebrow">SUBMITTED ASSESSMENT · READ ONLY</p><h2>{submittedAssessment.employee.full_name}</h2><p>{submittedAssessment.employee.employee_code} · {submittedAssessment.employee.division_name}</p>{([["Success Behaviours", submittedAssessment.success_behaviours], ["Functional Skills", submittedAssessment.functional_skills]] as const).map(([title, items]) => <section key={title}><h3>{title}</h3>{items.length ? <table><thead><tr><th>Skill Name</th><th>DL</th><th>SAL</th><th>MAL</th><th>Gap</th></tr></thead><tbody>{items.map((item) => <tr key={item.item_id}><td>{item.item_name}</td><td>{item.desired_level}</td><td>{item.self_assessment_level ?? "—"}</td><td>{item.manager_assessment_level ?? "—"}</td><td className={item.gap !== null && item.gap < 0 ? "negative-gap" : ""}>{item.gap ?? "—"}</td></tr>)}</tbody></table> : <p>No submitted items.</p>}</section>)}<AssessmentLegend /></section></div>}
    </section>
  </main>;
}

export function Workspace({
  user,
  onSignOut,
}: {
  user: CurrentUser;
  onSignOut: () => void;
}) {
  const [showAdminConsole, setShowAdminConsole] = useState(false);
  const [showExecutiveReview, setShowExecutiveReview] = useState(false);
  const [showEmployeeWorkspace, setShowEmployeeWorkspace] = useState(false);
  if (showAdminConsole && user.admin_console_access)
    return <AdminConsoleWorkspace user={user} onSignOut={onSignOut} onClose={() => setShowAdminConsole(false)} />;
  if (showExecutiveReview && user.executive_review_access)
    return <ExecutiveReviewWorkspace user={user} onSignOut={onSignOut} onClose={() => setShowExecutiveReview(false)} />;
  if (user.is_manager && !showEmployeeWorkspace)
    return <SkipManagerWorkspace user={user} onSignOut={onSignOut} onOpenAdminConsole={() => setShowAdminConsole(true)} onOpenExecutiveReview={() => setShowExecutiveReview(true)} onOpenEmployeeWorkspace={() => setShowEmployeeWorkspace(true)} />;
  if (showEmployeeWorkspace && user.employee_id !== null)
    return <EmployeeWorkspace user={user} onSignOut={onSignOut} onOpenAdminConsole={() => setShowAdminConsole(true)} onOpenManagerWorkspace={() => setShowEmployeeWorkspace(false)} />;
  if (user.role === "EMPLOYEE")
    return <EmployeeWorkspace user={user} onSignOut={onSignOut} onOpenAdminConsole={() => setShowAdminConsole(true)} onOpenManagerWorkspace={() => setShowEmployeeWorkspace(false)} />;
  if (user.role === "HR_SPOC")
    return <AdminConsoleWorkspace user={user} onSignOut={onSignOut} />;
  const view = roleViews[user.role];
  return (
    <main className="workspace-shell">
      <aside className="workspace-nav">
        <div className="workspace-brand">
          <img
            src={activeTenantBrand.logoUrl}
            alt={activeTenantBrand.tenantName}
          />
          <span>Talent Transformation</span>
        </div>
        <p className="workspace-role">{view.label}</p>
        <nav aria-label="Workspace navigation">
          {view.actions.map((action, index) => (
            <button className={index === 0 ? "active" : ""} key={action}>
              {action}
            </button>
          ))}
        </nav>
        {user.admin_console_access && <button className="password-action" onClick={() => setShowAdminConsole(true)}>Admin Console</button>}
        <ChangePasswordAction onSignOut={onSignOut} />
        <button className="sign-out" onClick={onSignOut}>
          Sign out
        </button>
      </aside>
      <section className="workspace-content">
        <header>
          <p className="eyebrow">{user.role.replaceAll("_", " ")}</p>
          <span>{user.email}</span>
        </header>
        <div className="workspace-intro">
          <p className="eyebrow">KDDL DIALS / SECURE WORKSPACE</p>
          <h1>{view.title}</h1>
          <p>{view.description}</p>
        </div>
        <div className="workspace-cards">
          {view.actions.map((action, index) => (
            <article key={action}>
              <b>0{index + 1}</b>
              <h2>{action}</h2>
              <p>
                This area is ready for the corresponding approved platform
                module.
              </p>
              <span>Coming next</span>
            </article>
          ))}
        </div>
      </section>
    </main>
  );
}
