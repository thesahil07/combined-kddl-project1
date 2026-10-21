import { useMemo, useState, useEffect, Fragment } from "react";
import "./executiveReview.css";
import type { CurrentUser } from "./workspace";
import rawData from "./data/kddlDbData.json";
import executiveData from "./data/kddlExecutiveData.json";

// Type definitions based on exact dataset
type Employee = {
  emp_code: string;
  name: string;
  division: string;
  division_id?: number;
  function: string;
  department: string;
  role?: string | null;
  grade?: string | null;
  grade_band: string;
  designation?: string | null;
  manager_name?: string | null;
  person_type: string;
  assessment_status: string;
  in_scope_for_gaps: string;
  employment_status: string;
  is_assessed?: boolean;
};

type GapItem = {
  gap_id: string;
  emp_code: string;
  type: string;
  skill_or_behaviour: string;
  definition?: string;
  desired_level: number;
  self_level?: number | null;
  assessed_level: number | null;
  gap: number | null;
  is_gap: string;
  training_need: string;
  training_status: string;
  improvement_description?: string | null;
};

type CriticalRole = {
  role_id: string;
  role_title: string;
  division: string;
  incumbent?: string | null;
  incumbent_emp_code?: string | null;
  grade?: string | null;
  criticality_basis?: string | null;
  approved_by?: string | null;
  status: string;
  incumbent_status: string;
};

type SuccessionSlate = {
  slate_id: string;
  role_title: string;
  division: string;
  incumbent?: string | null;
  incumbent_emp_code?: string | null;
  designation?: string | null;
  grade?: string | null;
  is_critical: string;
  emergency_successor?: string | null;
  ready_now?: string | null;
  one_move?: string | null;
  two_move?: string | null;
  successor_status?: string | null;
  remarks?: string | null;
  incumbent_status?: string | null;
};

type ActionItem = {
  id: string;
  title: string;
  owner: string;
  dueDate: string;
  context: string;
  notes?: string;
  status: "Open" | "In Progress" | "Completed";
};

type ModuleId = "01" | "02" | "03" | "04" | "05" | "people" | "person";

export function ExecutiveReviewWorkspace({
  user,
  onSignOut,
  onClose,
}: {
  user: CurrentUser;
  onSignOut: () => void;
  onClose: () => void;
}) {
  // Navigation & View State
  const [activeTab, setActiveTab] = useState<ModuleId>("01");
  const [selectedPersonCode, setSelectedPersonCode] = useState<string | null>(null);

  // Filters
  const [company, setCompany] = useState<"TARATEC" | "EIGEN">("TARATEC");
  const [plant, setPlant] = useState<"COMBINED" | "DIAL1" | "DIAL2">("DIAL2");
  const [selectedFunction, setSelectedFunction] = useState("All Functions");
  const [selectedLevel, setSelectedLevel] = useState("All Levels");

  // Sub-filters & Searches
  const [skillSearch, setSkillSearch] = useState("");
  const [peopleSearch, setPeopleSearch] = useState("");
  const [peopleFilterStatus, setPeopleFilterStatus] = useState<"assessed" | "with_gaps" | "no_gaps" | "all">("assessed");
  const [expandedPeopleCodes, setExpandedPeopleCodes] = useState<string[]>([]);
  const [personDetailsFilter, setPersonDetailsFilter] = useState<"all" | "gaps" | "met">("all");
  const [personTypeFilter, setPersonTypeFilter] = useState<"all" | "SKILL" | "BEHAVIOUR">("all");
  const [personSkillSearch, setPersonSkillSearch] = useState("");
  const [expandedPersonGapIds, setExpandedPersonGapIds] = useState<string[]>([]);
  const [selectedGradeBand, setSelectedGradeBand] = useState<string | null>(null);
  const [selectedFunctionGap, setSelectedFunctionGap] = useState<string | null>(null);
  const [expandedCriticalRoleId, setExpandedCriticalRoleId] = useState<string | null>(null);
  const [expandedGapId, setExpandedGapId] = useState<string | null>(null);

  // Live DB metrics for critical roles (null = not yet loaded / no data)
  const [dbCriticalRoles, setDbCriticalRoles] = useState<number | null>(null);
  const [dbWithoutSuccessor, setDbWithoutSuccessor] = useState<number | null>(null);
  const [dbReadyNowCover, setDbReadyNowCover] = useState<number | null>(null);
  const [dbSuccessorNamed, setDbSuccessorNamed] = useState<number | null>(null);
  const [dbSuccessionPlanCount, setDbSuccessionPlanCount] = useState<number | null>(null);
  const [dbCriticalRolesBasis, setDbCriticalRolesBasis] = useState<string | null>(null);

  // Live Module 03 Assessment & Readiness data from backend API (strictly from Database)
  const [dbPeopleAssessed, setDbPeopleAssessed] = useState<number | null>(null);
  const [dbTotalManpower, setDbTotalManpower] = useState<number | null>(null);
  const [dbAskCompletionPct, setDbAskCompletionPct] = useState<number | null>(null);
  const [dbDial1AskCompletionPct, setDbDial1AskCompletionPct] = useState<number | null>(null);
  const [dbDial2AskCompletionPct, setDbDial2AskCompletionPct] = useState<number | null>(null);
  const [dbDial1Assessed, setDbDial1Assessed] = useState<number | null>(null);
  const [dbDial2Assessed, setDbDial2Assessed] = useState<number | null>(null);
  const [dbCapabilityGaps, setDbCapabilityGaps] = useState<number | null>(null);
  const [dbDial1Gaps, setDbDial1Gaps] = useState<number | null>(null);
  const [dbDial2Gaps, setDbDial2Gaps] = useState<number | null>(null);
  const [dbPeopleWithGaps, setDbPeopleWithGaps] = useState<number | null>(null);
  const [dbGradeBandGaps, setDbGradeBandGaps] = useState<Array<{ band: string; total: number; gapped: number }> | null>(null);
  const [dbFunctionGaps, setDbFunctionGaps] = useState<Array<{ function_name: string; gap_count: number }> | null>(null);
  const [dbEmployeeGaps, setDbEmployeeGaps] = useState<Array<{
    emp_code: string;
    name: string;
    designation: string;
    function_name: string;
    division: string;
    grade_band: string;
    gaps: number;
  }> | null>(null);

  // Live Module 02 Capability & ASK data strictly from Database (null = loading / no data)
  const [dbData, setDbData] = useState<{
    rolesCount: number | null;
    assessedPopulation: number | null;
    skillsCount: number | null;
    functionsCount: number | null;
    departmentsCount: number | null;
    behavioursCount: number | null;
    askMappedRoles: number | null;
    skills: Array<{ skill_code: string; skill_name: string; function?: string; department?: string; definition?: string }> | null;
    roles: Array<{ role_id: string | number; title: string; division_id: number; function?: string; division?: string; description_status?: string; ask_status?: string }> | null;
    behaviours: Array<{ code: string; behaviour: string; definition: string }> | null;
  }>({
    rolesCount: null,
    assessedPopulation: null,
    skillsCount: null,
    functionsCount: null,
    departmentsCount: null,
    behavioursCount: null,
    askMappedRoles: null,
    skills: null,
    roles: null,
    behaviours: null,
  });

  // Overrides & Actions
  const [employmentStatuses, setEmploymentStatuses] = useState<Record<string, string>>({});
  const [actions, setActions] = useState<ActionItem[]>([]);

  // Modals
  const [assignModalOpen, setAssignModalOpen] = useState(false);
  const [assignPrefill, setAssignPrefill] = useState<{ title?: string; owner?: string; context?: string }>({});
  const [actionTitle, setActionTitle] = useState("");
  const [actionOwner, setActionOwner] = useState("");
  const [actionDue, setActionDue] = useState("");
  const [actionNotes, setActionNotes] = useState("");

  const [cmdOpen, setCmdOpen] = useState(false);
  const [cmdSearch, setCmdSearch] = useState("");

  // Raw data references
  const allEmployees = rawData.employees as Employee[];
  const allGaps = rawData.gaps as GapItem[];
  const allCriticalRoles = rawData.criticalRoles as CriticalRole[];
  const allCriticalSlates = rawData.criticalRolesSlates as SuccessionSlate[];
  const allNonCriticalSlates = rawData.nonCriticalRolesSlates as SuccessionSlate[];
  const allSkills = rawData.skills as { skill_code: string; skill_name: string; division_id?: number; function?: string; department?: string; definition?: string }[];
  const allBehaviours = rawData.successBehaviours as { behaviour: string; definition: string }[];
  const allRoles = ((rawData as Record<string, unknown>).roles ?? []) as Array<{ role_id: string | number; title: string; division_id: number; function?: string; division?: string; description_status?: string; ask_status?: string }>;
  const manpower = rawData.manpower as { DIAL1: number; DIAL2: number; COMBINED: number };
  const pendingEmpCodes = rawData.pendingEmpCodes as string[];
  const gapsByEmp = rawData.gapsByEmployee as Record<string, GapItem[]>;

  // Employee Map
  const empMap = useMemo(() => {
    const map = new Map<string, Employee>();
    allEmployees.forEach((e) => map.set(e.emp_code, e));
    return map;
  }, [allEmployees]);

  // Fetch live metrics from the backend API whenever plant or function changes
  useEffect(() => {
    // Reset plant/filter specific metrics so switching plants updates immediately without stale values
    setDbTotalManpower(null);
    setDbAskCompletionPct(null);
    setDbDial1AskCompletionPct(null);
    setDbDial2AskCompletionPct(null);
    setDbPeopleAssessed(null);
    setDbData((prev) => ({
      ...prev,
      rolesCount: null,
      assessedPopulation: null,
      skillsCount: null,
      functionsCount: null,
      departmentsCount: null,
      askMappedRoles: null,
    }));

    const token = sessionStorage.getItem("kddl_access_token");
    if (!token) return;
    const params = new URLSearchParams();
    if (plant === "DIAL1") params.append("division_id", "1");
    if (plant === "DIAL2") params.append("division_id", "2");
    if (selectedFunction !== "All Functions") params.append("function_name", selectedFunction);
    const queryString = params.toString() ? `?${params.toString()}` : "";
    fetch(`http://127.0.0.1:8000/api/v1/executive-review/dashboard${queryString}`, {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then((res) => (res.ok ? res.json() : null))
      .then((data) => {
        if (!data) return;
        if (typeof data.critical_roles === "number") setDbCriticalRoles(data.critical_roles);
        if (typeof data.critical_roles_without_successor === "number")
          setDbWithoutSuccessor(data.critical_roles_without_successor);
        if (typeof data.ready_now_cover === "number")
          setDbReadyNowCover(data.ready_now_cover);
        if (typeof data.successor_named === "number")
          setDbSuccessorNamed(data.successor_named);
        if (typeof data.succession_plan_count === "number")
          setDbSuccessionPlanCount(data.succession_plan_count);
        if (typeof data.criticality_basis === "string")
          setDbCriticalRolesBasis(data.criticality_basis);

        // Set Module 03 & Module 01 live database metrics
        if (typeof data.people_assessed === "number") setDbPeopleAssessed(data.people_assessed);
        if (typeof data.total_manpower === "number") setDbTotalManpower(data.total_manpower);
        if (typeof data.ask_completion_pct === "number") setDbAskCompletionPct(data.ask_completion_pct);
        if (typeof data.dial1_ask_completion_pct === "number") setDbDial1AskCompletionPct(data.dial1_ask_completion_pct);
        if (typeof data.dial2_ask_completion_pct === "number") setDbDial2AskCompletionPct(data.dial2_ask_completion_pct);
        if (typeof data.dial1_assessed === "number") setDbDial1Assessed(data.dial1_assessed);
        if (typeof data.dial2_assessed === "number") setDbDial2Assessed(data.dial2_assessed);
        if (typeof data.reported_gap_items === "number") setDbCapabilityGaps(data.reported_gap_items);
        if (typeof data.dial1_gaps === "number") setDbDial1Gaps(data.dial1_gaps);
        if (typeof data.dial2_gaps === "number") setDbDial2Gaps(data.dial2_gaps);
        if (typeof data.people_with_gaps === "number") setDbPeopleWithGaps(data.people_with_gaps);
        if (Array.isArray(data.gaps_by_grade_band)) setDbGradeBandGaps(data.gaps_by_grade_band);
        if (Array.isArray(data.gaps_by_function)) setDbFunctionGaps(data.gaps_by_function);
        if (Array.isArray(data.employee_gaps)) setDbEmployeeGaps(data.employee_gaps);

        // Set Module 02 live database fields (no hardcoded fallbacks)
        setDbData({
          rolesCount: typeof data.roles_count === "number" ? data.roles_count : null,
          assessedPopulation: typeof data.assessed_population === "number" ? data.assessed_population : null,
          skillsCount: typeof data.skills_count === "number" ? data.skills_count : null,
          functionsCount: typeof data.functions_count === "number" ? data.functions_count : null,
          departmentsCount: typeof data.departments_count === "number" ? data.departments_count : null,
          behavioursCount: typeof data.behaviours_count === "number" ? data.behaviours_count : null,
          askMappedRoles: typeof data.ask_mapped_roles === "number" ? data.ask_mapped_roles : null,
          skills: Array.isArray(data.skills) ? data.skills : null,
          roles: Array.isArray(data.roles) ? data.roles : null,
          behaviours: Array.isArray(data.success_behaviours) ? data.success_behaviours : null,
        });
      })
      .catch(() => {
        // Keep null on network/API failure so cards stay empty rather than displaying hardcoded numbers
      });
  }, [plant, selectedFunction]);

  // Keyboard shortcut for CMD
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        setCmdOpen((prev) => !prev);
      }
      if (e.key === "Escape") {
        setCmdOpen(false);
        setAssignModalOpen(false);
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, []);

  // Filtered employees based on plant, function, level
  const filteredEmployees = useMemo(() => {
    return allEmployees.filter((e) => {
      if (plant === "DIAL1" && !e.division.includes("Dials 1")) return false;
      if (plant === "DIAL2" && !e.division.includes("Dials 2")) return false;
      if (selectedFunction !== "All Functions" && e.function !== selectedFunction) return false;
      if (selectedLevel !== "All Levels" && e.grade_band !== selectedLevel) return false;
      return true;
    });
  }, [allEmployees, plant, selectedFunction, selectedLevel]);

  // Unique lists for dropdowns
  const functionsList = useMemo(() => {
    return Array.from(new Set(allEmployees.map((e) => e.function))).sort();
  }, [allEmployees]);

  const levelsList = useMemo(() => {
    return Array.from(new Set(allEmployees.map((e) => e.grade_band))).sort();
  }, [allEmployees]);

  // Filtered gaps
  const filteredGaps = useMemo(() => {
    const validCodes = new Set(filteredEmployees.map((e) => e.emp_code));
    return allGaps.filter((g) => validCodes.has(g.emp_code) && g.is_gap === "Yes");
  }, [allGaps, filteredEmployees]);

  // Open Assign Action Modal with Prefill
  const openAssignModal = (prefill?: { title?: string; owner?: string; context?: string }) => {
    setAssignPrefill(prefill ?? {});
    setActionTitle(prefill?.title ?? "");
    setActionOwner(prefill?.owner ?? "");
    setActionDue("");
    setActionNotes("");
    setAssignModalOpen(true);
  };

  const handleCreateAction = (e: React.FormEvent) => {
    e.preventDefault();
    if (!actionTitle.trim()) return;
    const newAction: ActionItem = {
      id: `ACT-${Date.now()}`,
      title: actionTitle.trim(),
      owner: actionOwner.trim() || "Unassigned",
      dueDate: actionDue || "Not set",
      context: assignPrefill.context || "Executive Review",
      notes: actionNotes.trim() || undefined,
      status: "Open",
    };
    setActions((prev) => [newAction, ...prev]);
    setAssignModalOpen(false);
  };

  const updateActionStatus = (id: string, status: "Open" | "In Progress" | "Completed") => {
    setActions((prev) => prev.map((a) => (a.id === id ? { ...a, status } : a)));
  };

  // Plant label helper
  const plantLabel = plant === "DIAL1" ? "Dial 1" : plant === "DIAL2" ? "Dial 2" : "Dial 1 + Dial 2 combined";
  const plantSubtitle = plant === "DIAL1" ? "DIAL 1" : plant === "DIAL2" ? "DIAL 2" : "COMBINED";

  // Cross-plant employees filtered by selected function and level (NOT filtered by plant, so plant breakdown is never zeroed out)
  const crossPlantEmployees = useMemo(() => {
    return allEmployees.filter((e) => {
      if (selectedFunction !== "All Functions" && e.function !== selectedFunction) return false;
      if (selectedLevel !== "All Levels" && e.grade_band !== selectedLevel) return false;
      return true;
    });
  }, [allEmployees, selectedFunction, selectedLevel]);

  // Dynamic counts for Module 01 & general metrics strictly reactive to filters (plant, function, level)
  const dial1Assessed = useMemo(
    () => crossPlantEmployees.filter((e) => e.division.includes("Dials 1") && e.is_assessed).length,
    [crossPlantEmployees]
  );
  const dial2Assessed = useMemo(
    () => crossPlantEmployees.filter((e) => e.division.includes("Dials 2") && e.is_assessed).length,
    [crossPlantEmployees]
  );
  const combinedAssessed = dial1Assessed + dial2Assessed;

  // Assessed population under current filters
  const currentAssessed = useMemo(() => {
    return plant === "COMBINED" ? combinedAssessed : plant === "DIAL1" ? dial1Assessed : dial2Assessed;
  }, [plant, combinedAssessed, dial1Assessed, dial2Assessed]);

  const dial1Manpower = useMemo(
    () => crossPlantEmployees.filter((e) => e.division.includes("Dials 1")).length,
    [crossPlantEmployees]
  );
  const dial2Manpower = useMemo(
    () => crossPlantEmployees.filter((e) => e.division.includes("Dials 2")).length,
    [crossPlantEmployees]
  );
  const combinedManpower = dial1Manpower + dial2Manpower;

  const currentManpower = useMemo(() => {
    return plant === "COMBINED" ? combinedManpower : plant === "DIAL1" ? dial1Manpower : dial2Manpower;
  }, [plant, combinedManpower, dial1Manpower, dial2Manpower]);

  const dial1AskPercent = useMemo(
    () => (dial1Manpower > 0 ? Math.round((dial1Assessed / dial1Manpower) * 100) : 0),
    [dial1Assessed, dial1Manpower]
  );
  const dial2AskPercent = useMemo(
    () => (dial2Manpower > 0 ? Math.round((dial2Assessed / dial2Manpower) * 100) : 0),
    [dial2Assessed, dial2Manpower]
  );
  const combinedAskPercent = useMemo(
    () => (combinedManpower > 0 ? Math.round((combinedAssessed / combinedManpower) * 100) : 0),
    [combinedAssessed, combinedManpower]
  );

  // Critical roles metrics (filtered by selected plant)
  const filteredCriticalRoles = useMemo(() => {
    return allCriticalRoles.filter((cr) => {
      if (plant === "DIAL1" && !cr.division.includes("Dials 1")) return false;
      if (plant === "DIAL2" && !cr.division.includes("Dials 2")) return false;
      return true;
    });
  }, [allCriticalRoles, plant]);

  const filteredCriticalSlates = useMemo(() => {
    return allCriticalSlates.filter((cs) => {
      if (plant === "DIAL1" && !cs.division.includes("Dials 1")) return false;
      if (plant === "DIAL2" && !cs.division.includes("Dials 2")) return false;
      return true;
    });
  }, [allCriticalSlates, plant]);

  const criticalRolesCount = filteredCriticalRoles.length;
  const readyNowRoles = filteredCriticalSlates.filter((s) => !!s.ready_now).length;
  const namedSuccessorRoles = filteredCriticalSlates.filter((s) => {
    const hasCandidate = [s.emergency_successor, s.ready_now, s.one_move, s.two_move].some(
      (v) => v && !/^review a hiring/i.test(v)
    );
    return hasCandidate;
  }).length;
  const noSuccessorRoles = Math.max(0, criticalRolesCount - namedSuccessorRoles);

  const dial1Crit = useMemo(() => allCriticalRoles.filter((cr) => cr.division.includes("Dials 1")).length, [allCriticalRoles]);
  const dial2Crit = useMemo(() => allCriticalRoles.filter((cr) => cr.division.includes("Dials 2")).length, [allCriticalRoles]);

  const dial1Gaps = useMemo(() => {
    const d1Codes = new Set(crossPlantEmployees.filter((e) => e.division.includes("Dials 1")).map((e) => e.emp_code));
    return allGaps.filter((g) => d1Codes.has(g.emp_code) && g.is_gap === "Yes").length;
  }, [crossPlantEmployees, allGaps]);

  const dial2Gaps = useMemo(() => {
    const d2Codes = new Set(crossPlantEmployees.filter((e) => e.division.includes("Dials 2")).map((e) => e.emp_code));
    return allGaps.filter((g) => d2Codes.has(g.emp_code) && g.is_gap === "Yes").length;
  }, [crossPlantEmployees, allGaps]);

  // Live Module 02 calculations from database (strictly driven by API or exact DB fallback)
  const fallbackRolesCount = useMemo(() => {
    const filtered = allRoles.filter((r) => {
      if (plant === "DIAL1" && r.division_id !== 1) return false;
      if (plant === "DIAL2" && r.division_id !== 2) return false;
      return true;
    });
    const unique = new Set(filtered.map((r) => r.title?.trim().toLowerCase()).filter(Boolean));
    return unique.size || (plant === "DIAL1" ? 70 : plant === "DIAL2" ? 120 : 183);
  }, [allRoles, plant]);

  const fallbackSkills = useMemo(() => {
    return allSkills.filter((s) => {
      if (plant === "DIAL1" && s.division_id !== 1) return false;
      if (plant === "DIAL2" && s.division_id !== 2) return false;
      return true;
    });
  }, [allSkills, plant]);

  const fallbackFunctionsCount = useMemo(() => {
    const fns = new Set(fallbackSkills.map((s) => s.function).filter(Boolean));
    return fns.size || (plant === "DIAL1" ? 17 : plant === "DIAL2" ? 35 : 52);
  }, [fallbackSkills, plant]);

  const fallbackDepartmentsCount = useMemo(() => {
    const depts = new Set(fallbackSkills.map((s) => s.department).filter(Boolean));
    return depts.size || (plant === "DIAL1" ? 24 : plant === "DIAL2" ? 44 : 68);
  }, [fallbackSkills, plant]);

  const liveRolesCount = dbData.rolesCount;
  const liveAssessedPop = dbData.assessedPopulation;
  const liveSkillsCount = dbData.skillsCount;
  const liveFunctionsCount = dbData.functionsCount;
  const liveDepartmentsCount = dbData.departmentsCount;
  const liveBehavioursCount = dbData.behavioursCount;
  const liveAskMappedCount = dbData.askMappedRoles;

  const displayRolesCount = liveRolesCount ?? fallbackRolesCount;
  const displaySkillsCount = liveSkillsCount ?? (fallbackSkills.length > 0 ? fallbackSkills.length : plant === "DIAL1" ? 100 : plant === "DIAL2" ? 180 : 280);
  const displayFunctionsCount = liveFunctionsCount ?? fallbackFunctionsCount;
  const displayDepartmentsCount = liveDepartmentsCount ?? fallbackDepartmentsCount;
  const displayBehavioursCount = liveBehavioursCount ?? (allBehaviours.length || 5);
  const displayAssessedPop = liveAssessedPop ?? currentAssessed;
  const displayTotalManpower = dbTotalManpower ?? currentManpower;

  const displayAskPercent =
    dbAskCompletionPct !== null
      ? dbAskCompletionPct
      : displayTotalManpower > 0
        ? Math.round((displayAssessedPop / displayTotalManpower) * 100)
        : 0;

  // Module 02 Live Database Skills & Behaviours (with database fallback)
  const activeSkills = useMemo(() => {
    if (dbData.skills && dbData.skills.length > 0) {
      return dbData.skills;
    }
    return fallbackSkills.length > 0 ? fallbackSkills : allSkills;
  }, [dbData.skills, fallbackSkills, allSkills]);

  const activeBehaviours = useMemo(() => {
    if (dbData.behaviours && dbData.behaviours.length > 0) {
      return dbData.behaviours;
    }
    return allBehaviours;
  }, [dbData.behaviours, allBehaviours]);

  const roleDesignations = useMemo(() => {
    const list = filteredEmployees.length > 0 ? filteredEmployees : allEmployees;
    const map = new Map<string, number>();
    for (const emp of list) {
      const des = (emp.designation ?? "").trim();
      if (des) map.set(des, (map.get(des) ?? 0) + 1);
    }
    return Array.from(map.entries())
      .map(([designation, count]) => ({ designation, count }))
      .sort((a, b) => b.count - a.count);
  }, [filteredEmployees, allEmployees]);

  // Pending assessments dynamically matched from filtered employees
  const filteredPendingEmployees = useMemo(() => {
    const pendingSet = new Set(pendingEmpCodes);
    return filteredEmployees.filter((e) => pendingSet.has(e.emp_code));
  }, [filteredEmployees, pendingEmpCodes]);

  const pendingCount = filteredPendingEmployees.length;
  const completedAssessments = Math.max(0, currentAssessed - pendingCount);
  const affectedRoles = useMemo(() => {
    if (filteredPendingEmployees.length === 0) return "None";
    return Array.from(new Set(filteredPendingEmployees.map((e) => e.designation || e.role))).join(" & ");
  }, [filteredPendingEmployees]);

  // Succession levels helper
  const getReadinessLevels = (slate: SuccessionSlate) => [
    { level: "Emergency", value: slate.emergency_successor },
    { level: "Ready now", value: slate.ready_now },
    { level: "1 move away", value: slate.one_move },
    { level: "2 moves away", value: slate.two_move },
  ];

  // Grade band gaps for Module 03 (from real DB API)
  const gradeBandGaps = useMemo(() => {
    if (dbGradeBandGaps && dbGradeBandGaps.length > 0 && selectedFunction === "All Functions" && selectedLevel === "All Levels") {
      return dbGradeBandGaps;
    }
    const bands = ["LM", "M", "E", "S3"];
    return bands
      .map((band) => {
        const inBand = (dbEmployeeGaps && dbEmployeeGaps.length > 0)
          ? dbEmployeeGaps.filter((e) => e.grade_band.startsWith(band.replace("3", "")))
          : filteredEmployees.filter((e) => e.grade_band.startsWith(band.replace("3", "")));
        const gapped = (dbEmployeeGaps && dbEmployeeGaps.length > 0)
          ? inBand.filter((e) => (e as any).gaps > 0)
          : inBand.filter((e) => (gapsByEmp[(e as Employee).emp_code] ?? []).some((g) => g.is_gap === "Yes"));
        return {
          band,
          total: inBand.length,
          gapped: gapped.length,
        };
      })
      .filter((b) => b.total > 0 || (dbGradeBandGaps && dbGradeBandGaps.some((d) => d.band === b.band)));
  }, [dbGradeBandGaps, dbEmployeeGaps, selectedFunction, selectedLevel, filteredEmployees, gapsByEmp]);

  // Function gaps for Module 03 (from real DB API)
  const functionGaps = useMemo(() => {
    if (dbFunctionGaps && dbFunctionGaps.length > 0 && selectedFunction === "All Functions" && selectedLevel === "All Levels") {
      return dbFunctionGaps.map((f) => [f.function_name, f.gap_count] as [string, number]);
    }
    const map = new Map<string, number>();
    if (dbEmployeeGaps && dbEmployeeGaps.length > 0) {
      dbEmployeeGaps.forEach((e) => {
        if (e.gaps > 0) {
          const fn = e.function_name || "Other";
          map.set(fn, (map.get(fn) ?? 0) + e.gaps);
        }
      });
      return Array.from(map.entries()).sort((a, b) => b[1] - a[1]);
    }
    filteredGaps.forEach((g) => {
      const emp = empMap.get(g.emp_code);
      const fn = emp?.function ?? "Other";
      map.set(fn, (map.get(fn) ?? 0) + 1);
    });
    return Array.from(map.entries()).sort((a, b) => b[1] - a[1]);
  }, [dbFunctionGaps, dbEmployeeGaps, selectedFunction, selectedLevel, filteredGaps, empMap]);

  const maxFunctionGaps = functionGaps[0]?.[1] ?? 1;
  const totalGapsCount = useMemo(() => functionGaps.reduce((acc, curr) => acc + curr[1], 0), [functionGaps]);

  // Drilldown people in Module 03 (from real DB records)
  const drilldownPeople = useMemo(() => {
    if (dbEmployeeGaps && dbEmployeeGaps.length > 0) {
      if (selectedGradeBand) {
        return dbEmployeeGaps
          .filter((e) => e.grade_band.startsWith(selectedGradeBand.replace("3", "")))
          .map((e) => ({
            emp_code: e.emp_code,
            name: e.name,
            designation: e.designation,
            function: e.function_name,
            division: e.division,
            gaps: e.gaps,
          }));
      }
      if (selectedFunctionGap) {
        return dbEmployeeGaps
          .filter((e) => e.function_name.trim().toLowerCase() === selectedFunctionGap.trim().toLowerCase())
          .map((e) => ({
            emp_code: e.emp_code,
            name: e.name,
            designation: e.designation,
            function: e.function_name,
            division: e.division,
            gaps: e.gaps,
          }));
      }
      return [];
    }
    if (selectedGradeBand) {
      return filteredEmployees
        .filter((e) => e.grade_band.startsWith(selectedGradeBand.replace("3", "")))
        .map((e) => ({
          emp_code: e.emp_code,
          name: e.name,
          designation: e.designation ?? "—",
          function: e.function,
          division: e.division,
          gaps: (gapsByEmp[e.emp_code] ?? []).filter((g) => g.is_gap === "Yes").length,
        }));
    }
    if (selectedFunctionGap) {
      return filteredEmployees
        .filter((e) => e.function.trim().toLowerCase() === selectedFunctionGap.trim().toLowerCase())
        .map((e) => ({
          emp_code: e.emp_code,
          name: e.name,
          designation: e.designation ?? "—",
          function: e.function,
          division: e.division,
          gaps: (gapsByEmp[e.emp_code] ?? []).filter((g) => g.is_gap === "Yes").length,
        }));
    }
    return [];
  }, [dbEmployeeGaps, filteredEmployees, selectedGradeBand, selectedFunctionGap, gapsByEmp]);

  // Selected person details
  const activePerson = selectedPersonCode ? empMap.get(selectedPersonCode) : null;
  const activePersonGaps = selectedPersonCode ? gapsByEmp[selectedPersonCode] ?? [] : [];
  const activePersonIdentifiedGaps = useMemo(() => activePersonGaps.filter((g) => g.is_gap === "Yes"), [activePersonGaps]);
  const activePersonMetCount = useMemo(() => activePersonGaps.filter((g) => g.is_gap !== "Yes").length, [activePersonGaps]);

  const activePersonSkills = useMemo(
    () => activePersonGaps.filter((g) => g.type === "SKILL" || g.type === "Skill"),
    [activePersonGaps]
  );
  const activePersonBehaviours = useMemo(
    () => activePersonGaps.filter((g) => g.type === "BEHAVIOUR" || g.type === "Success Behaviour"),
    [activePersonGaps]
  );

  const activePersonAvgDesired = useMemo(() => {
    if (!activePersonGaps.length) return 0;
    const sum = activePersonGaps.reduce((acc, g) => acc + (g.desired_level ?? 0), 0);
    return sum / activePersonGaps.length;
  }, [activePersonGaps]);

  const activePersonAvgAssessed = useMemo(() => {
    const assessedItems = activePersonGaps.filter((g) => g.assessed_level !== null && g.assessed_level !== undefined);
    if (!assessedItems.length) return 0;
    const sum = assessedItems.reduce((acc, g) => acc + (g.assessed_level ?? 0), 0);
    return sum / assessedItems.length;
  }, [activePersonGaps]);

  const displayedPersonGaps = useMemo(() => {
    return activePersonGaps.filter((g) => {
      if (personDetailsFilter === "gaps" && g.is_gap !== "Yes") return false;
      if (personDetailsFilter === "met" && g.is_gap === "Yes") return false;
      if (personTypeFilter === "SKILL" && !(g.type === "SKILL" || g.type === "Skill")) return false;
      if (personTypeFilter === "BEHAVIOUR" && !(g.type === "BEHAVIOUR" || g.type === "Success Behaviour")) return false;
      if (personSkillSearch.trim()) {
        const q = personSkillSearch.trim().toLowerCase();
        const nameMatch = g.skill_or_behaviour.toLowerCase().includes(q);
        const defMatch = (g.definition ?? "").toLowerCase().includes(q);
        if (!nameMatch && !defMatch) return false;
      }
      return true;
    });
  }, [activePersonGaps, personDetailsFilter, personTypeFilter, personSkillSearch]);

  const togglePersonExpandedInList = (code: string) => {
    setExpandedPeopleCodes((prev) =>
      prev.includes(code) ? prev.filter((c) => c !== code) : [...prev, code]
    );
  };

  const toggleAllPeopleInList = () => {
    if (expandedPeopleCodes.length > 0) {
      setExpandedPeopleCodes([]);
    } else {
      setExpandedPeopleCodes(filteredEmployees.map((e) => e.emp_code));
    }
  };

  const togglePersonGapExpanded = (id: string) => {
    setExpandedPersonGapIds((prev) =>
      prev.includes(id) ? prev.filter((i) => i !== id) : [...prev, id]
    );
  };

  const toggleAllPersonGaps = (allIds: string[]) => {
    if (expandedPersonGapIds.length === allIds.length) {
      setExpandedPersonGapIds([]);
    } else {
      setExpandedPersonGapIds(allIds);
    }
  };

  const displayedEmployeesInList = useMemo(() => {
    return filteredEmployees.filter((emp) => {
      const q = peopleSearch.trim().toLowerCase();
      if (q) {
        const match =
          emp.name.toLowerCase().includes(q) ||
          emp.emp_code.toLowerCase().includes(q) ||
          emp.function.toLowerCase().includes(q) ||
          (emp.designation ?? "").toLowerCase().includes(q);
        if (!match) return false;
      }

      const empGaps = gapsByEmp[emp.emp_code] ?? [];
      const hasGaps = empGaps.some((g) => g.is_gap === "Yes");
      if (peopleFilterStatus === "assessed" && !emp.is_assessed) return false;
      if (peopleFilterStatus === "with_gaps" && (!emp.is_assessed || !hasGaps)) return false;
      if (peopleFilterStatus === "no_gaps" && (!emp.is_assessed || hasGaps || empGaps.length === 0)) return false;
      // "all" shows all roster manpower within current filter

      return true;
    });
  }, [filteredEmployees, peopleSearch, peopleFilterStatus, gapsByEmp]);


  return (
    <div className="min-h-screen bg-background font-sans text-foreground antialiased selection:bg-brand selection:text-brand-foreground">
      {/* ── Top Bar / Header ── */}
      <header className="exec-header-surface sticky top-0 z-40">
        <div className="mx-auto flex max-w-[1560px] items-center justify-between px-5 py-2.5 lg:px-8">
          {/* Brand */}
          <div className="flex items-center gap-3">
            <button
              onClick={() => {
                setActiveTab("01");
                setSelectedPersonCode(null);
              }}
              className="flex items-center gap-2.5 transition-opacity hover:opacity-90"
            >
              <img
                src="/kddl-logo.png"
                alt="KDDL Limited"
                className="h-8 w-auto rounded bg-white px-1.5 py-0.5 object-contain"
                onError={(e) => {
                  (e.currentTarget as HTMLElement).style.display = "none";
                }}
              />
              <div className="flex flex-col text-left leading-tight">
                <span className="text-[13px] font-bold tracking-tight text-white">KDDL GROUP</span>
                <span className="text-[10px] tracking-wide text-slate-300">
                  Organization &amp; Leadership Intelligence
                </span>
              </div>
            </button>
          </div>

          {/* Right Header Actions */}
          <div className="flex items-center gap-3">
            <div className="hidden text-right text-[11px] leading-tight text-slate-300 lg:block">
              <div className="uppercase tracking-[0.14em] text-slate-400">Last Updated</div>
              <div className="font-semibold text-white">01 Oct 2026</div>
            </div>

            <button
              onClick={() => openAssignModal({ context: "Executive Review" })}
              className="inline-flex items-center gap-1.5 rounded-md bg-[#00878a] px-3 py-1.5 text-[12px] font-semibold text-white shadow transition hover:bg-[#007477]"
            >
              <svg className="size-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                <path d="M12 5v14M5 12h14" />
              </svg>
              <span>Assign Action</span>
            </button>

            <button
              onClick={() => setCmdOpen(true)}
              title="Open Command Palette (Ctrl+K)"
              className="flex size-7 items-center justify-center rounded-full border border-slate-600 text-[10.5px] font-bold tracking-wider text-slate-200 hover:bg-white/10"
            >
              CMD
            </button>

            <span className="hidden text-[11px] text-slate-300 md:inline">{user.email}</span>

            <button
              onClick={onClose}
              className="rounded px-2 py-1 text-[11px] font-medium text-slate-300 hover:bg-white/10 hover:text-white"
            >
              Workspace
            </button>
            <button
              onClick={onSignOut}
              className="rounded px-2 py-1 text-[11px] font-medium text-slate-300 hover:bg-white/10 hover:text-white"
            >
              Sign out
            </button>
          </div>
        </div>

        {/* ── 5 Module Navigation Tabs ── */}
        <nav className="exec-tab-nav">
          <div className="mx-auto max-w-[1560px] px-5 lg:px-8">
            <div className="exec-tab-grid">
              {[
                { id: "01", label: "Executive Review" },
                { id: "02", label: "Capability & ASK" },
                { id: "03", label: "Assessment & Readiness" },
                { id: "04", label: "Critical Roles & Succession" },
                { id: "05", label: "Actions & Governance" },
              ].map((tab) => {
                const isActive = activeTab === tab.id;
                return (
                  <button
                    key={tab.id}
                    onClick={() => {
                      setActiveTab(tab.id as ModuleId);
                      setSelectedPersonCode(null);
                    }}
                    className={`exec-tab-btn ${isActive ? "active" : ""}`}
                  >
                    {isActive && <span className="exec-tab-indicator" />}
                    <span className="exec-tab-badge">{tab.id}</span>
                    <span className="truncate">{tab.label}</span>
                  </button>
                );
              })}
            </div>
          </div>
        </nav>
      </header>

      {/* ── Subbar / Filter Bar ── */}
      <div className="sticky top-[93px] z-30 border-b border-border bg-card/95 backdrop-blur-md">
        <div className="mx-auto flex max-w-[1560px] flex-wrap items-center justify-between gap-3 px-5 py-2.5 lg:px-8">
          {/* Left Group: Company + Plants */}
          <div className="flex flex-wrap items-center gap-2">
            {/* Entity / Company Tabs */}
            <div className="inline-flex rounded-md border border-border bg-secondary/50 p-0.5">
              <button
                onClick={() => setCompany("TARATEC")}
                className={`rounded px-2.5 py-1 text-[11.5px] font-bold tracking-wider transition ${
                  company === "TARATEC"
                    ? "bg-navy text-navy-foreground shadow-sm"
                    : "text-muted-foreground hover:text-foreground"
                }`}
              >
                TARATEC
              </button>
              <button
                onClick={() => setCompany("EIGEN")}
                className={`rounded px-2.5 py-1 text-[11.5px] font-bold tracking-wider transition ${
                  company === "EIGEN"
                    ? "bg-navy text-navy-foreground shadow-sm"
                    : "text-muted-foreground hover:text-foreground"
                }`}
              >
                EIGEN
              </button>
            </div>

            {/* Separator */}
            <span className="h-4 w-px bg-border" />

            {/* Plant Selector */}
            <span className="exec-label hidden font-bold text-muted-foreground sm:inline">PLANT</span>
            <div className="inline-flex rounded-md border border-border bg-secondary/50 p-0.5">
              {[
                { id: "COMBINED", label: "Combined" },
                { id: "DIAL1", label: "Dial 1" },
                { id: "DIAL2", label: "Dial 2" },
              ].map((p) => (
                <button
                  key={p.id}
                  onClick={() => setPlant(p.id as "COMBINED" | "DIAL1" | "DIAL2")}
                  className={`rounded px-2.5 py-1 text-[11.5px] font-semibold transition ${
                    plant === p.id
                      ? "bg-navy text-navy-foreground shadow-sm"
                      : "text-muted-foreground hover:text-foreground"
                  }`}
                >
                  {p.label}
                </button>
              ))}
            </div>
          </div>

          {/* Right Group: Functions & Levels Dropdowns */}
          <div className="flex flex-wrap items-center gap-2">
            <select
              value={selectedFunction}
              onChange={(e) => setSelectedFunction(e.target.value)}
              className="h-8 max-w-[210px] rounded-md border border-border bg-card px-2.5 text-[12px] font-medium text-foreground focus:border-brand focus:outline-none"
            >
              <option value="All Functions">All Functions</option>
              {functionsList.map((fn) => (
                <option key={fn} value={fn}>
                  {fn}
                </option>
              ))}
            </select>

            <select
              value={selectedLevel}
              onChange={(e) => setSelectedLevel(e.target.value)}
              className="h-8 rounded-md border border-border bg-card px-2.5 text-[12px] font-medium text-foreground focus:border-brand focus:outline-none"
            >
              <option value="All Levels">All Levels</option>
              {levelsList.map((lvl) => (
                <option key={lvl} value={lvl}>
                  {lvl}
                </option>
              ))}
            </select>
          </div>
        </div>
      </div>

      {/* ── Main Content Area ── */}
      <main className="mx-auto max-w-[1560px] px-5 py-7 lg:px-8">
        {company === "EIGEN" ? (
          /* EIGEN Empty State */
          <div className="exec-panel flex flex-col items-center justify-center gap-3 px-6 py-24 text-center">
            <span className="exec-label">Eigen</span>
            <h1 className="text-[26px] font-semibold tracking-tight">Engagement just started</h1>
            <p className="max-w-md text-[13.5px] leading-relaxed text-muted-foreground">
              No assessment or succession data has been collected for Eigen yet. Select Taratec to review populated modules.
            </p>
            <button
              onClick={() => setCompany("TARATEC")}
              className="mt-2 rounded-md bg-brand px-4 py-2 text-[12.5px] font-semibold text-brand-foreground hover:bg-brand/90"
            >
              Switch to Taratec
            </button>
          </div>
        ) : activeTab === "people" ? (
          /* ── Drill-down: People Directory ── */
          <div className="space-y-6">
            <div className="relative flex flex-wrap items-end justify-between gap-4 pt-4">
              <span aria-hidden="true" className="exec-hairline absolute left-0 top-0 h-[3px] w-28 rounded-full" />
              <div>
                <p className="exec-label">Drill-down · Taratec</p>
                <h1 className="mt-1 text-[30px] font-semibold leading-[1.1] tracking-[-0.02em]">People Assessed</h1>
                <p className="exec-serif mt-2 text-[17px] italic leading-relaxed text-muted-foreground">
                  “Who has been assessed, and what does each person need?”
                </p>
              </div>
              <button
                onClick={() => setActiveTab("01")}
                className="text-[12.5px] font-semibold text-brand hover:underline"
              >
                ← Back to Executive Review
              </button>
            </div>

            <section className="exec-panel overflow-hidden">
              {/* Header: Title, Counts and Plant Summary */}
              <header className="exec-panel-header relative border-b border-border px-6 py-4 space-y-3.5">
                <span aria-hidden="true" className="exec-hairline absolute left-0 top-0 h-[2px] w-24" />
                
                <div className="flex flex-wrap items-center justify-between gap-4">
                  <div>
                    <div className="flex items-center gap-2.5">
                      <h2 className="text-[17px] font-semibold text-foreground tracking-[-0.01em]">
                        People Assessed ({displayedEmployeesInList.length})
                      </h2>
                      <span className="rounded-full bg-brand/10 border border-brand/20 px-2.5 py-0.5 text-[11px] font-semibold text-brand">
                        Taratec Roster
                      </span>
                    </div>
                    <p className="mt-1 text-[13px] text-muted-foreground">
                      Assessed population within current filter: {currentAssessed} of {currentManpower}. Plant head-count: Dial 1 {dial1Manpower}, Dial 2{" "}
                      {dial2Manpower} (combined {combinedManpower}). Click "All Details" on any person to view their complete desired, assessed &amp; gap scorecard.
                    </p>
                  </div>

                  <div className="flex items-center gap-2 text-[12px]">
                    <div className="rounded border border-border bg-card px-2.5 py-1 text-muted-foreground shadow-xs">
                      Dial 1: <strong className="text-foreground tabular-nums">{dial1Manpower}</strong> (assessed: <strong className="text-foreground tabular-nums">{dial1Assessed}</strong>)
                    </div>
                    <div className="rounded border border-border bg-card px-2.5 py-1 text-muted-foreground shadow-xs">
                      Dial 2: <strong className="text-foreground tabular-nums">{dial2Manpower}</strong> (assessed: <strong className="text-foreground tabular-nums">{dial2Assessed}</strong>)
                    </div>
                    <div className="rounded border border-border bg-card px-2.5 py-1 text-muted-foreground shadow-xs">
                      Combined: <strong className="text-foreground tabular-nums">{combinedManpower}</strong> (assessed: <strong className="text-foreground tabular-nums">{combinedAssessed}</strong>)
                    </div>
                  </div>
                </div>

                {/* Filter and Actions Bar */}
                <div className="flex flex-wrap items-center justify-between gap-3 pt-2 border-t border-border/60">
                  <div className="flex flex-wrap items-center gap-3">
                    <div className="relative">
                      <input
                        type="text"
                        value={peopleSearch}
                        onChange={(e) => setPeopleSearch(e.target.value)}
                        placeholder="Search name, code, function, designation..."
                        className="h-8.5 w-[300px] rounded-md border border-border bg-card pl-8 pr-3 text-[12.5px] placeholder:text-muted-foreground focus:border-brand focus:outline-none"
                      />
                      <svg
                        className="pointer-events-none absolute left-2.5 top-1/2 -translate-y-1/2 size-3.5 text-muted-foreground"
                        viewBox="0 0 24 24"
                        fill="none"
                        stroke="currentColor"
                        strokeWidth="2"
                      >
                        <circle cx="11" cy="11" r="8" />
                        <path d="m21 21-4.3-4.3" />
                      </svg>
                    </div>

                    {/* Filter by Status Pill */}
                    <div className="flex flex-wrap items-center rounded-md border border-border bg-secondary/50 p-0.5 text-[12px] font-medium">
                      <button
                        onClick={() => setPeopleFilterStatus("assessed")}
                        className={`rounded px-3 py-1 transition ${
                          peopleFilterStatus === "assessed"
                            ? "bg-card text-foreground font-semibold shadow-xs"
                            : "text-muted-foreground hover:text-foreground"
                        }`}
                      >
                        All Assessed ({filteredEmployees.filter((e) => e.is_assessed).length})
                      </button>
                      <button
                        onClick={() => setPeopleFilterStatus("with_gaps")}
                        className={`rounded px-3 py-1 transition flex items-center gap-1.5 ${
                          peopleFilterStatus === "with_gaps"
                            ? "bg-rag-amber/20 text-rag-amber font-semibold shadow-xs"
                            : "text-muted-foreground hover:text-foreground"
                        }`}
                      >
                        <span className="size-1.5 rounded-full bg-rag-amber" />
                        <span>With Gaps ({filteredEmployees.filter((e) => e.is_assessed && (gapsByEmp[e.emp_code] ?? []).some((g) => g.is_gap === "Yes")).length})</span>
                      </button>
                      <button
                        onClick={() => setPeopleFilterStatus("no_gaps")}
                        className={`rounded px-3 py-1 transition flex items-center gap-1.5 ${
                          peopleFilterStatus === "no_gaps"
                            ? "bg-rag-green/20 text-rag-green font-semibold shadow-xs"
                            : "text-muted-foreground hover:text-foreground"
                        }`}
                      >
                        <span className="size-1.5 rounded-full bg-rag-green" />
                        <span>All Met ({filteredEmployees.filter((e) => {
                          const emG = gapsByEmp[e.emp_code] ?? [];
                          return e.is_assessed && emG.length > 0 && !emG.some((g) => g.is_gap === "Yes");
                        }).length})</span>
                      </button>
                      <button
                        onClick={() => setPeopleFilterStatus("all")}
                        className={`rounded px-3 py-1 transition flex items-center gap-1.5 ${
                          peopleFilterStatus === "all"
                            ? "bg-secondary text-foreground font-semibold shadow-xs"
                            : "text-muted-foreground hover:text-foreground"
                        }`}
                      >
                        <span className="size-1.5 rounded-full bg-muted-foreground/60" />
                        <span>All Manpower ({filteredEmployees.length})</span>
                      </button>
                    </div>
                  </div>

                  {/* Expand/Collapse All Details Button */}
                  <button
                    onClick={toggleAllPeopleInList}
                    className="inline-flex items-center gap-1.5 rounded-md border border-border bg-card px-3 py-1.5 text-[12px] font-semibold text-foreground transition hover:bg-secondary shadow-xs"
                  >
                    <svg
                      className={`size-3.5 transition-transform ${
                        expandedPeopleCodes.length > 0 ? "rotate-180" : ""
                      }`}
                      viewBox="0 0 24 24"
                      fill="none"
                      stroke="currentColor"
                      strokeWidth="2"
                    >
                      <path d="m6 9 6 6 6-6" />
                    </svg>
                    <span>{expandedPeopleCodes.length > 0 ? "Collapse All Details" : "Expand All Details"}</span>
                  </button>
                </div>
              </header>

              <div className="max-h-[720px] overflow-x-auto overflow-y-auto">
                <table className="w-full table-fixed min-w-[1050px] text-[13px] border-collapse">
                  <colgroup>
                    <col style={{ width: "21%" }} />
                    <col style={{ width: "16%" }} />
                    <col style={{ width: "13%" }} />
                    <col style={{ width: "10%" }} />
                    <col style={{ width: "6%" }} />
                    <col style={{ width: "10%" }} />
                    <col style={{ width: "12%" }} />
                    <col style={{ width: "12%" }} />
                  </colgroup>
                  <thead className="sticky top-0 bg-secondary/95 backdrop-blur-xs z-10 border-b border-border shadow-xs">
                    <tr>
                      <th className="exec-label px-4 py-3 text-left font-semibold text-muted-foreground">Name &amp; Code</th>
                      <th className="exec-label px-3 py-3 text-left font-semibold text-muted-foreground">Designation</th>
                      <th className="exec-label px-3 py-3 text-left font-semibold text-muted-foreground">Function</th>
                      <th className="exec-label px-3 py-3 text-left font-semibold text-muted-foreground">Division</th>
                      <th className="exec-label px-3 py-3 text-center font-semibold text-muted-foreground">Band</th>
                      <th className="exec-label px-3 py-3 text-left font-semibold text-muted-foreground">Status</th>
                      <th className="exec-label px-4 py-3 text-left font-semibold text-muted-foreground">Assessment &amp; Gaps</th>
                      <th className="exec-label px-4 py-3 text-right font-semibold text-muted-foreground">All Details</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border">
                    {displayedEmployeesInList.length === 0 ? (
                      <tr>
                        <td colSpan={8} className="py-12 text-center text-muted-foreground">
                          No employees match the current filter and search criteria.
                        </td>
                      </tr>
                    ) : (
                      displayedEmployeesInList.map((emp) => {
                        const empStatus = employmentStatuses[emp.emp_code] ?? emp.employment_status;
                        const empGaps = gapsByEmp[emp.emp_code] ?? [];
                        const gapCount = empGaps.filter((g) => g.is_gap === "Yes").length;
                        const metCount = empGaps.filter((g) => g.is_gap !== "Yes").length;
                        const isExpanded = expandedPeopleCodes.includes(emp.emp_code);

                        return (
                          <Fragment key={emp.emp_code}>
                            <tr className={`transition hover:bg-secondary/40 ${isExpanded ? "bg-secondary/25" : ""}`}>
                              {/* 1. Name & Code */}
                              <td className="px-4 py-3 align-middle">
                                <div className="flex flex-col items-start leading-tight">
                                  <button
                                    onClick={() => {
                                      setSelectedPersonCode(emp.emp_code);
                                      setActiveTab("person");
                                    }}
                                    className="font-semibold text-foreground underline-offset-4 hover:text-brand hover:underline text-left"
                                  >
                                    {emp.name}
                                  </button>
                                  <span className="font-mono text-[11px] text-muted-foreground mt-0.5">
                                    {emp.emp_code}
                                  </span>
                                </div>
                              </td>

                              {/* 2. Designation */}
                              <td className="px-3 py-3 text-muted-foreground align-middle text-[12.5px]">
                                {emp.designation ?? "—"}
                              </td>

                              {/* 3. Function */}
                              <td className="px-3 py-3 text-muted-foreground align-middle text-[12.5px]">
                                <span className="rounded bg-secondary/80 border border-border/50 px-2 py-0.5 font-medium text-foreground text-[11.5px]">
                                  {emp.function}
                                </span>
                              </td>

                              {/* 4. Division */}
                              <td className="px-3 py-3 text-muted-foreground align-middle text-[12.5px]">
                                {emp.division}
                              </td>

                              {/* 5. Band */}
                              <td className="px-3 py-3 text-center align-middle font-semibold tabular-nums">
                                {emp.grade_band}
                              </td>

                              {/* 6. Status */}
                              <td className="px-3 py-3 align-middle">
                                <span
                                  className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-[11px] font-semibold ${
                                    empStatus === "Active"
                                      ? "border-rag-green/35 bg-rag-green-soft text-rag-green"
                                      : empStatus === "Left" || empStatus === "Retired"
                                      ? "border-rag-grey/30 bg-rag-grey-soft text-rag-grey"
                                      : "border-rag-amber/35 bg-rag-amber-soft text-rag-amber"
                                  }`}
                                >
                                  <span
                                    className={`size-1.5 rounded-full ${
                                      empStatus === "Active"
                                        ? "bg-rag-green"
                                        : empStatus === "Left" || empStatus === "Retired"
                                        ? "bg-rag-grey"
                                        : "bg-rag-amber"
                                    }`}
                                  />
                                  {empStatus}
                                </span>
                              </td>

                              {/* 7. Assessment & Gaps */}
                              <td className="px-4 py-3 align-middle">
                                {empGaps.length > 0 ? (
                                  <div className="flex flex-col items-start gap-1">
                                    {gapCount > 0 ? (
                                      <span className="inline-flex items-center gap-1 rounded-full border border-rag-amber/40 bg-rag-amber-soft px-2.5 py-0.5 text-[11px] font-bold text-rag-amber whitespace-nowrap">
                                        <span className="size-1.5 rounded-full bg-rag-amber" />
                                        {gapCount} Gap{gapCount === 1 ? "" : "s"}
                                      </span>
                                    ) : (
                                      <span className="inline-flex items-center gap-1 rounded-full border border-rag-green/40 bg-rag-green-soft px-2.5 py-0.5 text-[11px] font-bold text-rag-green whitespace-nowrap">
                                        <span className="size-1.5 rounded-full bg-rag-green" />
                                        All Met
                                      </span>
                                    )}
                                    <span className="text-[11px] tabular-nums text-muted-foreground whitespace-nowrap">
                                      {metCount} met / {empGaps.length} total
                                    </span>
                                  </div>
                                ) : (
                                  <span className="inline-flex items-center gap-1 rounded border border-border/60 bg-secondary/50 px-2 py-0.5 text-[11px] font-medium text-muted-foreground whitespace-nowrap">
                                    <span className="size-1 rounded-full bg-muted-foreground/60" />
                                    Not assessed
                                  </span>
                                )}
                              </td>

                              {/* 8. All Details Action */}
                              <td className="px-4 py-3 text-right align-middle">
                                <div className="flex items-center justify-end gap-1.5 whitespace-nowrap">
                                  {empGaps.length > 0 ? (
                                    <button
                                      onClick={() => togglePersonExpandedInList(emp.emp_code)}
                                      className={`inline-flex items-center gap-1 rounded border px-2.5 py-1 text-[11px] font-semibold transition ${
                                        isExpanded
                                          ? "border-brand bg-brand/10 text-brand"
                                          : "border-border bg-card text-foreground hover:bg-secondary"
                                      }`}
                                      title="View inline assessment scorecard"
                                    >
                                      <span>{isExpanded ? "Hide" : "All Details"}</span>
                                      <svg
                                        className={`size-3 transition-transform ${isExpanded ? "rotate-180" : ""}`}
                                        viewBox="0 0 24 24"
                                        fill="none"
                                        stroke="currentColor"
                                        strokeWidth="2"
                                      >
                                        <path d="m6 9 6 6 6-6" />
                                      </svg>
                                    </button>
                                  ) : (
                                    <span className="text-[11px] text-muted-foreground/70 italic mr-1">No data</span>
                                  )}
                                  <button
                                    onClick={() => {
                                      setSelectedPersonCode(emp.emp_code);
                                      setActiveTab("person");
                                    }}
                                    className="inline-flex items-center gap-1 rounded border border-border/80 bg-secondary/40 px-2 py-1 text-[11px] font-semibold text-muted-foreground hover:text-foreground hover:bg-secondary transition whitespace-nowrap"
                                    title="Open individual details review"
                                  >
                                    Details Review →
                                  </button>
                                </div>
                              </td>
                            </tr>

                            {/* Inline Expandable Assessment Details Panel */}
                            {isExpanded && (
                              <tr className="bg-secondary/20 border-b border-border">
                                <td colSpan={8} className="p-0">
                                  <div className="px-6 py-4 space-y-3.5 bg-card/60">
                                    <div className="flex flex-wrap items-center justify-between gap-3 border-b border-border/60 pb-2.5">
                                      <div className="flex items-center gap-2">
                                        <span className="font-semibold text-[13.5px] text-foreground">
                                          {emp.name} — Full Assessment Scorecard
                                        </span>
                                        <span className="font-mono text-[11.5px] text-muted-foreground">
                                          ({emp.emp_code})
                                        </span>
                                      </div>
                                      <div className="flex items-center gap-3 text-[12px]">
                                        <span className="text-muted-foreground">
                                          Total Assessed: <strong className="text-foreground">{empGaps.length}</strong>
                                        </span>
                                        <span className="text-rag-amber font-semibold">
                                          Gaps: {gapCount}
                                        </span>
                                        <span className="text-rag-green font-semibold">
                                          Met: {metCount}
                                        </span>
                                        <button
                                          onClick={() => {
                                            setSelectedPersonCode(emp.emp_code);
                                            setActiveTab("person");
                                          }}
                                          className="text-brand font-semibold hover:underline ml-2"
                                        >
                                          Open Full Details Review & Action Plan →
                                        </button>
                                      </div>
                                    </div>

                                    <div className="overflow-x-auto rounded border border-border/80 bg-background/50">
                                      <table className="w-full text-[12px]">
                                        <thead>
                                          <tr className="bg-secondary/70 text-muted-foreground">
                                            <th className="px-3 py-1.5 text-left font-semibold">Skill / Behaviour</th>
                                            <th className="px-3 py-1.5 text-left font-semibold">Type</th>
                                            <th className="px-3 py-1.5 text-center font-semibold">Desired</th>
                                            <th className="px-3 py-1.5 text-center font-semibold">Assessed</th>
                                            <th className="px-3 py-1.5 text-center font-semibold">Gap</th>
                                            <th className="px-3 py-1.5 text-left font-semibold">Status</th>
                                            <th className="px-3 py-1.5 text-left font-semibold">Training Need</th>
                                          </tr>
                                        </thead>
                                        <tbody className="divide-y divide-border/60">
                                          {empGaps.map((it) => (
                                            <tr key={it.gap_id} className="hover:bg-secondary/30">
                                              <td className="px-3 py-1.5 font-medium text-foreground">
                                                {it.skill_or_behaviour}
                                              </td>
                                              <td className="px-3 py-1.5 text-muted-foreground text-[11px]">
                                                <span className="rounded bg-secondary px-1.5 py-0.5 font-medium">
                                                  {it.type}
                                                </span>
                                              </td>
                                              <td className="px-3 py-1.5 text-center tabular-nums font-semibold">
                                                Level {it.desired_level ?? "—"}
                                              </td>
                                              <td className="px-3 py-1.5 text-center tabular-nums text-muted-foreground">
                                                Level {it.assessed_level ?? "Pending"}
                                              </td>
                                              <td className="px-3 py-1.5 text-center tabular-nums font-bold">
                                                {it.gap !== null && it.gap !== undefined ? (
                                                  it.gap < 0 ? (
                                                    <span className="text-rag-amber font-semibold">{it.gap} Gap</span>
                                                  ) : it.gap === 0 ? (
                                                    <span className="text-rag-green font-semibold">0 (Met)</span>
                                                  ) : (
                                                    <span className="text-sky-500 font-semibold">+{it.gap} (Exceeds)</span>
                                                  )
                                                ) : (
                                                  "—"
                                                )}
                                              </td>
                                              <td className="px-3 py-1.5">
                                                {it.is_gap === "Yes" ? (
                                                  <span className="inline-flex items-center gap-1 rounded bg-rag-amber-soft px-1.5 py-0.5 text-[10.5px] font-semibold text-rag-amber">
                                                    <span className="size-1 rounded-full bg-rag-amber" />
                                                    Identified
                                                  </span>
                                                ) : (
                                                  <span className="inline-flex items-center gap-1 rounded bg-rag-green-soft px-1.5 py-0.5 text-[10.5px] font-semibold text-rag-green">
                                                    <span className="size-1 rounded-full bg-rag-green" />
                                                    Met
                                                  </span>
                                                )}
                                              </td>
                                              <td className="px-3 py-1.5 text-muted-foreground text-[11.5px] truncate max-w-[280px]">
                                                {it.training_need}
                                              </td>
                                            </tr>
                                          ))}
                                        </tbody>
                                      </table>
                                    </div>
                                  </div>
                                </td>
                              </tr>
                            )}
                          </Fragment>
                        );
                      })
                    )}
                  </tbody>
                </table>
              </div>
            </section>
          </div>
        ) : activeTab === "person" && activePerson ? (
          /* ── Drill-down: Individual Details Review ── */
          <div className="space-y-6">
            <button
              onClick={() => setActiveTab("people")}
              className="inline-flex items-center gap-1.5 text-[12.5px] font-semibold text-muted-foreground hover:text-brand"
            >
              <svg className="size-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="m12 19-7-7 7-7M19 12H5" />
              </svg>
              <span>Back to people</span>
            </button>

            <div className="relative flex flex-wrap items-end justify-between gap-4 pt-2">
              <span aria-hidden="true" className="exec-hairline absolute left-0 top-0 h-[3px] w-28 rounded-full" />
              <div>
                <p className="exec-label">Individual Details Review · {activePerson.division}</p>
                <h1 className="mt-1 text-[30px] font-semibold leading-[1.1] tracking-[-0.02em]">
                  {activePerson.name}
                </h1>
              </div>
              <div className="flex items-center gap-2">
                <span className="exec-label">Employment status</span>
                <select
                  value={employmentStatuses[activePerson.emp_code] ?? activePerson.employment_status}
                  onChange={(e) =>
                    setEmploymentStatuses((prev) => ({ ...prev, [activePerson.emp_code]: e.target.value }))
                  }
                  className="h-8 rounded-md border border-border bg-card px-2 text-[12.5px] font-medium text-foreground focus:border-brand focus:outline-none"
                >
                  {["Active", "Left", "On contract", "On retainer", "Retired"].map((st) => (
                    <option key={st} value={st}>
                      {st}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            <div className="grid gap-4 lg:grid-cols-3">
              {/* Details Review Card */}
              <section className="exec-panel overflow-hidden lg:col-span-2">
                <header className="exec-panel-header border-b border-border px-5 py-4">
                  <h2 className="text-[15.5px] font-semibold">Details Review</h2>
                </header>
                <dl className="grid gap-x-8 gap-y-2.5 px-5 py-4 sm:grid-cols-2">
                  {[
                    ["Employee code", activePerson.emp_code],
                    ["Division", activePerson.division],
                    ["Function", activePerson.function],
                    ["Department", activePerson.department],
                    ["Role", activePerson.role ?? "—"],
                    ["Grade", activePerson.grade ?? "—"],
                    ["Grade band", activePerson.grade_band],
                    ["Designation", activePerson.designation ?? "—"],
                    ["Reports to", activePerson.manager_name ?? "—"],
                    ["Person type", activePerson.person_type],
                    ["Assessment status", activePerson.assessment_status],
                  ].map(([label, val]) => (
                    <div key={label} className="flex items-baseline gap-2 text-[13px]">
                      <dt className="shrink-0 text-muted-foreground">{label}</dt>
                      <span aria-hidden="true" className="min-w-3 flex-1 border-b border-dotted border-border" />
                      <dd className="shrink-0 font-semibold">{val}</dd>
                    </div>
                  ))}
                </dl>
              </section>

              {/* Succession Links Card */}
              <section className="exec-panel overflow-hidden">
                <header className="exec-panel-header border-b border-border px-5 py-4">
                  <h2 className="text-[15.5px] font-semibold">Succession links</h2>
                </header>
                <div className="space-y-3 px-5 py-4 text-[13px]">
                  {allCriticalRoles.filter((cr) => cr.incumbent_emp_code === activePerson.emp_code).map((cr) => (
                    <div key={cr.role_id} className="space-y-1 rounded-md border border-rag-amber/35 bg-rag-amber-soft/40 p-3">
                      <span className="inline-flex items-center gap-1 text-[11px] font-semibold text-rag-amber">
                        <span className="size-1.5 rounded-full bg-rag-amber" />
                        Critical role incumbent
                      </span>
                      <p className="font-semibold text-foreground">{cr.role_title}</p>
                      <p className="text-[12px] text-muted-foreground">{cr.criticality_basis}</p>
                    </div>
                  ))}

                  {allCriticalSlates
                    .filter((s) =>
                      [s.emergency_successor, s.ready_now, s.one_move, s.two_move].some(
                        (v) => v && v.includes(activePerson.name)
                      )
                    )
                    .map((s) => (
                      <div key={s.slate_id} className="space-y-1 rounded-md border border-rag-green/35 bg-rag-green-soft/40 p-3">
                        <span className="inline-flex items-center gap-1 text-[11px] font-semibold text-rag-green">
                          <span className="size-1.5 rounded-full bg-rag-green" />
                          Named successor
                        </span>
                        <p className="font-semibold text-foreground">{s.role_title}</p>
                        <p className="text-[12px] text-muted-foreground">Incumbent: {s.incumbent ?? "—"}</p>
                      </div>
                    ))}

                  <button
                    onClick={() => setActiveTab("04")}
                    className="inline-block text-[12.5px] font-semibold text-brand underline-offset-4 hover:underline"
                  >
                    Open the succession register →
                  </button>
                </div>
              </section>
            </div>

            {/* Competency Assessment & All Details Analysis */}
            <section className="exec-panel overflow-hidden space-y-0">
              <header className="exec-panel-header flex flex-wrap items-center justify-between gap-4 border-b border-border px-5 py-4">
                <div>
                  <div className="flex items-center gap-2">
                    <h2 className="text-[16px] font-semibold text-foreground">
                      Competency Assessment &amp; Gap Analysis
                    </h2>
                    <span className="rounded bg-brand/10 border border-brand/20 px-2 py-0.5 text-[11px] font-semibold text-brand">
                      All Details
                    </span>
                  </div>
                  <p className="mt-0.5 text-[13px] text-muted-foreground">
                    {activePersonIdentifiedGaps.length} identified gap{activePersonIdentifiedGaps.length === 1 ? "" : "s"} · {activePersonMetCount} competencies meeting desired level · {activePersonGaps.length} total assessed skills and behaviours.
                  </p>
                </div>

                <div className="flex items-center gap-2">
                  <button
                    onClick={() => toggleAllPersonGaps(displayedPersonGaps.map((g) => g.gap_id))}
                    className="inline-flex items-center gap-1.5 rounded-md border border-border bg-card px-2.5 py-1.5 text-[12px] font-semibold text-foreground transition hover:bg-secondary"
                  >
                    <svg
                      className={`size-3.5 transition-transform ${
                        expandedPersonGapIds.length > 0 ? "rotate-180" : ""
                      }`}
                      viewBox="0 0 24 24"
                      fill="none"
                      stroke="currentColor"
                      strokeWidth="2"
                    >
                      <path d="m6 9 6 6 6-6" />
                    </svg>
                    <span>
                      {expandedPersonGapIds.length === displayedPersonGaps.length && displayedPersonGaps.length > 0
                        ? "Collapse All"
                        : "Expand All Details"}
                    </span>
                  </button>
                </div>
              </header>

              {/* 5 KPI Metric Cards for Individual */}
              <div
                className="p-5 border-b border-border/80 bg-secondary/20"
                style={{
                  display: "grid",
                  gridTemplateColumns: "repeat(auto-fit, minmax(170px, 1fr))",
                  gap: "12px",
                }}
              >
                {/* Total Assessed */}
                <div className="exec-panel exec-kpi p-4 flex flex-col justify-between gap-2.5">
                  <div className="flex items-center justify-between gap-2">
                    <span className="exec-label">Total Assessed</span>
                    <span className="size-2 rounded-full bg-slate-400 shrink-0" />
                  </div>
                  <div className="exec-number text-[30px] leading-none">
                    {activePersonGaps.length}
                  </div>
                  <div className="text-[11.5px] text-muted-foreground">
                    {activePersonSkills.length} skills · {activePersonBehaviours.length} behaviours
                  </div>
                </div>

                {/* Gaps Identified */}
                <div className="exec-panel exec-kpi p-4 flex flex-col justify-between gap-2.5 border-rag-amber/35 bg-rag-amber-soft/20">
                  <div className="flex items-center justify-between gap-2">
                    <span className="exec-label text-rag-amber">Identified Gaps</span>
                    <span className="size-2 rounded-full bg-rag-amber shrink-0" />
                  </div>
                  <div className="exec-number text-[30px] leading-none text-rag-amber">
                    {activePersonIdentifiedGaps.length}
                  </div>
                  <div className="text-[11.5px] text-muted-foreground">
                    Requiring training &amp; dev
                  </div>
                </div>

                {/* Requirements Met */}
                <div className="exec-panel exec-kpi p-4 flex flex-col justify-between gap-2.5 border-rag-green/35 bg-rag-green-soft/20">
                  <div className="flex items-center justify-between gap-2">
                    <span className="exec-label text-rag-green">Requirements Met</span>
                    <span className="size-2 rounded-full bg-rag-green shrink-0" />
                  </div>
                  <div className="exec-number text-[30px] leading-none text-rag-green">
                    {activePersonMetCount}
                  </div>
                  <div className="text-[11.5px] text-muted-foreground">
                    At or above target level
                  </div>
                </div>

                {/* Alignment Score */}
                <div className="exec-panel exec-kpi p-4 flex flex-col justify-between gap-2.5">
                  <div className="flex items-center justify-between gap-2">
                    <span className="exec-label">Role Alignment</span>
                    <span className="size-2 rounded-full bg-brand shrink-0" />
                  </div>
                  <div className="exec-number text-[30px] leading-none">
                    {activePersonGaps.length > 0
                      ? Math.round((activePersonMetCount / activePersonGaps.length) * 100)
                      : 0}%
                  </div>
                  <div className="text-[11.5px] text-muted-foreground">
                    Competency coverage
                  </div>
                </div>

                {/* Avg Desired vs Assessed */}
                <div className="exec-panel exec-kpi p-4 flex flex-col justify-between gap-2.5">
                  <div className="flex items-center justify-between gap-2">
                    <span className="exec-label">Avg Proficiency</span>
                    <span className="size-2 rounded-full bg-sky-500 shrink-0" />
                  </div>
                  <div className="exec-number text-[30px] leading-none flex items-baseline gap-1.5">
                    <span>{activePersonAvgAssessed.toFixed(1)}</span>
                    <span className="text-[13.5px] font-normal text-muted-foreground">
                      / {activePersonAvgDesired.toFixed(1)} target
                    </span>
                  </div>
                  <div className="text-[11.5px] text-muted-foreground">
                    Assessed vs Target Level
                  </div>
                </div>
              </div>

              {/* Controls Bar: All Details vs Gaps Only vs Met */}
              <div className="flex flex-wrap items-center justify-between gap-3 px-5 py-3 border-b border-border bg-secondary/40">
                {/* Details Filter Segmented Tabs */}
                <div className="flex flex-wrap items-center gap-2">
                  <span className="exec-label mr-1">View Options:</span>
                  <div className="flex items-center rounded-md border border-border bg-card p-0.5 text-[12px] font-medium">
                    <button
                      onClick={() => setPersonDetailsFilter("all")}
                      className={`rounded px-3 py-1 transition ${
                        personDetailsFilter === "all"
                          ? "bg-brand text-brand-foreground font-semibold shadow-xs"
                          : "text-muted-foreground hover:text-foreground"
                      }`}
                    >
                      All Details ({activePersonGaps.length})
                    </button>
                    <button
                      onClick={() => setPersonDetailsFilter("gaps")}
                      className={`rounded px-3 py-1 transition ${
                        personDetailsFilter === "gaps"
                          ? "bg-rag-amber/25 text-rag-amber font-semibold shadow-xs"
                          : "text-muted-foreground hover:text-foreground"
                      }`}
                    >
                      Identified Gaps ({activePersonIdentifiedGaps.length})
                    </button>
                    <button
                      onClick={() => setPersonDetailsFilter("met")}
                      className={`rounded px-3 py-1 transition ${
                        personDetailsFilter === "met"
                          ? "bg-rag-green/25 text-rag-green font-semibold shadow-xs"
                          : "text-muted-foreground hover:text-foreground"
                      }`}
                    >
                      Requirements Met ({activePersonMetCount})
                    </button>
                  </div>

                  {/* Type Filter */}
                  <select
                    value={personTypeFilter}
                    onChange={(e) => setPersonTypeFilter(e.target.value as any)}
                    className="h-8 rounded-md border border-border bg-card px-2.5 text-[12px] font-medium text-foreground focus:border-brand focus:outline-none"
                  >
                    <option value="all">All Competency Types</option>
                    <option value="SKILL">Functional Skills ({activePersonSkills.length})</option>
                    <option value="BEHAVIOUR">Success Behaviours ({activePersonBehaviours.length})</option>
                  </select>
                </div>

                {/* Competency Search */}
                <div className="relative">
                  <input
                    type="text"
                    value={personSkillSearch}
                    onChange={(e) => setPersonSkillSearch(e.target.value)}
                    placeholder="Search competency or definition..."
                    className="h-8 w-[250px] rounded-md border border-border bg-card pl-8 pr-3 text-[12px] placeholder:text-muted-foreground focus:border-brand focus:outline-none"
                  />
                  <svg
                    className="pointer-events-none absolute left-2.5 top-1/2 -translate-y-1/2 size-3.5 text-muted-foreground"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="2"
                  >
                    <circle cx="11" cy="11" r="8" />
                    <path d="m21 21-4.3-4.3" />
                  </svg>
                </div>
              </div>

              {/* Assessment Details Table */}
              <div className="overflow-x-auto">
                <table className="w-full table-fixed min-w-[980px] text-[13px] border-collapse">
                  <colgroup>
                    <col style={{ width: "28%" }} />
                    <col style={{ width: "14%" }} />
                    <col style={{ width: "10%" }} />
                    <col style={{ width: "10%" }} />
                    <col style={{ width: "11%" }} />
                    <col style={{ width: "11%" }} />
                    <col style={{ width: "11%" }} />
                    <col style={{ width: "5%" }} />
                  </colgroup>
                  <thead>
                    <tr className="bg-secondary/70">
                      <th className="exec-label px-5 py-3 text-left">Skill / Behaviour</th>
                      <th className="exec-label px-3 py-3 text-left">Type</th>
                      <th className="exec-label px-3 py-3 text-center">Desired</th>
                      <th className="exec-label px-3 py-3 text-center">Self Rating</th>
                      <th className="exec-label px-3 py-3 text-center">Assessed</th>
                      <th className="exec-label px-3 py-3 text-center">Gap</th>
                      <th className="exec-label px-4 py-3 text-left">Training Status</th>
                      <th className="exec-label px-4 py-3 text-right">Details</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border">
                    {displayedPersonGaps.length === 0 ? (
                      <tr>
                        <td colSpan={8} className="py-12 text-center text-muted-foreground">
                          No competency records match the current filter selection.
                        </td>
                      </tr>
                    ) : (
                      displayedPersonGaps.map((g) => {
                        const isExpanded = expandedPersonGapIds.includes(g.gap_id);
                        const def =
                          g.definition ||
                          (g.type === "Success Behaviour" || g.type === "BEHAVIOUR"
                            ? allBehaviours.find((b) => b.behaviour === g.skill_or_behaviour)?.definition
                            : allSkills.find((s) => s.skill_name === g.skill_or_behaviour)?.definition);

                        const isGap = (g.gap ?? 0) < 0;
                        const isMet = (g.gap ?? 0) === 0;
                        const isExceeds = (g.gap ?? 0) > 0;

                        return (
                          <Fragment key={g.gap_id}>
                            <tr
                              onClick={() => togglePersonGapExpanded(g.gap_id)}
                              className={`cursor-pointer transition hover:bg-secondary/40 ${
                                isExpanded ? "bg-secondary/50" : ""
                              }`}
                            >
                              {/* 1. Skill / Behaviour Name */}
                              <td className="px-5 py-3 align-middle font-medium">
                                <div className="flex items-center gap-2">
                                  <span
                                    className={`size-2 rounded-full shrink-0 ${
                                      isGap ? "bg-rag-amber" : isMet ? "bg-rag-green" : "bg-sky-400"
                                    }`}
                                  />
                                  <span className="truncate">{g.skill_or_behaviour}</span>
                                </div>
                              </td>

                              {/* 2. Type */}
                              <td className="px-3 py-3 align-middle text-muted-foreground">
                                <span className="rounded bg-secondary px-2 py-0.5 text-[11px] font-medium">
                                  {g.type === "SKILL" || g.type === "Skill"
                                    ? "Functional Skill"
                                    : "Success Behaviour"}
                                </span>
                              </td>

                              {/* 3. Desired */}
                              <td className="px-3 py-3 text-center align-middle">
                                <span className="inline-flex items-center justify-center rounded border border-border bg-card px-2 py-0.5 text-[12px] font-semibold tabular-nums text-foreground">
                                  Level {g.desired_level ?? "—"}
                                </span>
                              </td>

                              {/* 4. Self Rating */}
                              <td className="px-3 py-3 text-center align-middle tabular-nums text-[12.5px] text-muted-foreground">
                                {g.self_level !== null && g.self_level !== undefined ? (
                                  <span className="font-medium text-foreground">
                                    Level {g.self_level}
                                  </span>
                                ) : (
                                  "—"
                                )}
                              </td>

                              {/* 5. Assessed (Manager) */}
                              <td className="px-3 py-3 text-center align-middle">
                                <span
                                  className={`inline-flex items-center justify-center rounded px-2 py-0.5 text-[12px] font-bold tabular-nums ${
                                    isGap
                                      ? "bg-rag-amber/15 text-rag-amber"
                                      : "bg-rag-green/15 text-rag-green"
                                  }`}
                                >
                                  Level {g.assessed_level ?? "Pending"}
                                </span>
                              </td>

                              {/* 6. Gap */}
                              <td className="px-3 py-3 text-center align-middle">
                                {isGap ? (
                                  <span className="inline-flex items-center gap-1 rounded-full border border-rag-amber/40 bg-rag-amber-soft px-2.5 py-0.5 text-[11.5px] font-bold text-rag-amber tabular-nums">
                                    <span className="size-1.5 rounded-full bg-rag-amber" />
                                    {g.gap} Gap
                                  </span>
                                ) : isMet ? (
                                  <span className="inline-flex items-center gap-1 rounded-full border border-rag-green/40 bg-rag-green-soft px-2.5 py-0.5 text-[11.5px] font-bold text-rag-green tabular-nums">
                                    <span className="size-1.5 rounded-full bg-rag-green" />
                                    0 (Met)
                                  </span>
                                ) : isExceeds ? (
                                  <span className="inline-flex items-center gap-1 rounded-full border border-sky-500/40 bg-sky-500/10 px-2.5 py-0.5 text-[11.5px] font-bold text-sky-400 tabular-nums">
                                    +{g.gap} Exceeds
                                  </span>
                                ) : (
                                  <span className="text-muted-foreground">—</span>
                                )}
                              </td>

                              {/* 7. Training Status */}
                              <td className="px-4 py-3 align-middle text-left">
                                {isGap ? (
                                  <span className="inline-flex items-center gap-1 text-[11.5px] font-semibold text-rag-amber whitespace-nowrap">
                                    <span className="size-1.5 rounded-full bg-rag-amber" />
                                    IDENTIFIED
                                  </span>
                                ) : (
                                  <span className="inline-flex items-center gap-1 text-[11.5px] font-semibold text-rag-green whitespace-nowrap">
                                    <span className="size-1.5 rounded-full bg-rag-green" />
                                    MET / PROFICIENT
                                  </span>
                                )}
                              </td>

                              {/* 8. Expand Chevron */}
                              <td className="px-4 py-3 text-right align-middle">
                                <svg
                                  className={`size-4 text-muted-foreground transition-transform ml-auto ${
                                    isExpanded ? "rotate-180" : ""
                                  }`}
                                  viewBox="0 0 24 24"
                                  fill="none"
                                  stroke="currentColor"
                                  strokeWidth="2"
                                >
                                  <path d="m6 9 6 6 6-6" />
                                </svg>
                              </td>
                            </tr>

                            {/* Expanded Row: All Details, Definition & Visual Progression */}
                            {isExpanded && (
                              <tr className="border-b border-border bg-secondary/25">
                                <td colSpan={8} className="p-0">
                                  <div className="px-6 py-4 space-y-4 animate-in fade-in-0 duration-200">
                                    {/* Definition Callout */}
                                    <div className="rounded-md border border-border/70 bg-card/70 p-4 space-y-1.5">
                                      <div className="flex items-center justify-between text-[11px] uppercase tracking-wider text-muted-foreground font-semibold">
                                        <span>Competency Definition</span>
                                        <span className="font-mono text-[10.5px]">ID: {g.gap_id}</span>
                                      </div>
                                      <p className="text-[13px] leading-relaxed text-foreground/90">
                                        {def ?? "No specific definition recorded in dictionary for this item."}
                                      </p>
                                    </div>


                                    {/* Training Priority & Action Row */}
                                    <div className="flex flex-wrap items-center justify-between gap-3 pt-1">
                                      <div className="flex items-center gap-2 text-[12.5px]">
                                        <span className="text-muted-foreground font-semibold">Training Need:</span>
                                        <span className="font-medium text-foreground">{g.training_need}</span>
                                      </div>

                                      {isGap && (
                                        <button
                                          onClick={() =>
                                            openAssignModal({
                                              title: `Development Plan: ${g.skill_or_behaviour} for ${activePerson.name}`,
                                              owner: activePerson.manager_name || activePerson.name,
                                              context: `Gap in ${g.skill_or_behaviour} (Target: Level ${g.desired_level}, Assessed: Level ${g.assessed_level})`,
                                            })
                                          }
                                          className="inline-flex items-center gap-1.5 rounded-md bg-[#00878a] px-3 py-1.5 text-[11.5px] font-semibold text-white shadow-xs transition hover:bg-[#007477]"
                                        >
                                          <svg
                                            className="size-3"
                                            viewBox="0 0 24 24"
                                            fill="none"
                                            stroke="currentColor"
                                            strokeWidth="2.5"
                                          >
                                            <path d="M12 5v14M5 12h14" />
                                          </svg>
                                          <span>Assign Action for this Gap</span>
                                        </button>
                                      )}
                                    </div>
                                  </div>
                                </td>
                              </tr>
                            )}
                          </Fragment>
                        );
                      })
                    )}
                  </tbody>
                </table>
              </div>
            </section>
          </div>
        ) : activeTab === "01" ? (
          /* ── MODULE 01: Executive Review ── */
          <div className="space-y-6">
            <div className="relative flex flex-wrap items-end justify-between gap-4 pt-4">
              <span aria-hidden="true" className="exec-hairline absolute left-0 top-0 h-[3px] w-28 rounded-full" />
              <div>
                <p className="exec-label">MODULE 01 · TARATEC · {plantSubtitle}</p>
                <h1 className="mt-1 text-[30px] font-semibold leading-[1.1] tracking-[-0.02em]">Executive Review</h1>
                <p className="exec-serif mt-2 text-[17px] italic leading-relaxed text-muted-foreground">
                  “Is the organisation ready to deliver its agenda?”
                </p>
              </div>
            </div>

            {/* 5 KPI Metric Cards */}
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5">
              {/* 1. People Assessed */}
              <div
                onClick={() => setActiveTab("people")}
                className="group exec-panel exec-kpi relative flex cursor-pointer flex-col justify-between gap-4 overflow-hidden pl-5 pr-4 py-4 transition-all duration-200 hover:-translate-y-1 hover:border-border-strong hover:shadow-lift"
              >
                <span className="absolute inset-y-0 left-0 w-[3px] bg-rag-green transition-all duration-200 group-hover:w-[5px]" />
                <span className="pointer-events-none absolute -right-10 -top-12 size-32 rounded-full bg-rag-green opacity-[0.10] blur-2xl transition-opacity duration-200 group-hover:opacity-[0.18]" />
                <div className="relative flex items-start justify-between gap-2">
                  <span className="exec-label leading-snug">People Assessed</span>
                  <span className="size-2.5 rounded-full bg-rag-green mt-0.5 shrink-0" />
                </div>
                <div className="relative flex items-baseline gap-2">
                  <span className="exec-number text-[38px] leading-none">{currentAssessed}</span>
                </div>
                <dl className="relative space-y-1.5 border-t border-border/70 pt-2.5">
                  <div className="flex items-baseline gap-2 text-[12.5px]">
                    <dt className="text-muted-foreground">Dial 1</dt>
                    <span className="min-w-3 flex-1 border-b border-dotted border-border" />
                    <dd className="font-semibold tabular-nums">{dial1Assessed}</dd>
                  </div>
                  <div className="flex items-baseline gap-2 text-[12.5px]">
                    <dt className="text-muted-foreground">Dial 2</dt>
                    <span className="min-w-3 flex-1 border-b border-dotted border-border" />
                    <dd className="font-semibold tabular-nums">{dial2Assessed}</dd>
                  </div>
                </dl>
              </div>

              {/* 2. Total Manpower */}
              <div
                onClick={() => setActiveTab("people")}
                className="group exec-panel exec-kpi relative flex cursor-pointer flex-col justify-between gap-4 overflow-hidden pl-5 pr-4 py-4 transition-all duration-200 hover:-translate-y-1 hover:border-border-strong hover:shadow-lift"
              >
                <span className="absolute inset-y-0 left-0 w-[3px] bg-rag-green transition-all duration-200 group-hover:w-[5px]" />
                <span className="pointer-events-none absolute -right-10 -top-12 size-32 rounded-full bg-rag-green opacity-[0.10] blur-2xl transition-opacity duration-200 group-hover:opacity-[0.18]" />
                <div className="relative flex items-start justify-between gap-2">
                  <span className="exec-label leading-snug">Total Manpower</span>
                  <span className="size-2.5 rounded-full bg-rag-green mt-0.5 shrink-0" />
                </div>
                <div className="relative flex items-baseline gap-2">
                  <span className="exec-number text-[38px] leading-none">{currentManpower}</span>
                </div>
                <dl className="relative space-y-1.5 border-t border-border/70 pt-2.5">
                  <div className="flex items-baseline gap-2 text-[12.5px]">
                    <dt className="text-muted-foreground">{plant === "COMBINED" ? "Dial 1" : plant === "DIAL1" ? "Dial 2" : "Dial 1"}</dt>
                    <span className="min-w-3 flex-1 border-b border-dotted border-border" />
                    <dd className="font-semibold tabular-nums">
                      {plant === "COMBINED" ? dial1Manpower : plant === "DIAL1" ? dial2Manpower : dial1Manpower}
                    </dd>
                  </div>
                  <div className="flex items-baseline gap-2 text-[12.5px]">
                    <dt className="text-muted-foreground">{plant === "COMBINED" ? "Dial 2" : "Combined"}</dt>
                    <span className="min-w-3 flex-1 border-b border-dotted border-border" />
                    <dd className="font-semibold tabular-nums">
                      {plant === "COMBINED" ? dial2Manpower : combinedManpower}
                    </dd>
                  </div>
                </dl>
              </div>

              {/* 3. Critical Roles */}
              <div
                onClick={() => setActiveTab("04")}
                className="group exec-panel exec-kpi relative flex cursor-pointer flex-col justify-between gap-4 overflow-hidden pl-5 pr-4 py-4 transition-all duration-200 hover:-translate-y-1 hover:border-border-strong hover:shadow-lift"
              >
                <span
                  className={`absolute inset-y-0 left-0 w-[3px] ${
                    dbCriticalRoles !== null && dbCriticalRoles > 0 ? "bg-rag-amber" : "bg-border"
                  } transition-all duration-200 group-hover:w-[5px]`}
                />
                {dbCriticalRoles !== null && dbCriticalRoles > 0 && (
                  <span className="pointer-events-none absolute -right-10 -top-12 size-32 rounded-full bg-rag-amber opacity-[0.10] blur-2xl transition-opacity duration-200 group-hover:opacity-[0.18]" />
                )}
                <div className="relative flex items-start justify-between gap-2">
                  <span className="exec-label leading-snug">Critical Roles</span>
                  <span
                    className={`size-2.5 rounded-full ${
                      dbCriticalRoles !== null && dbCriticalRoles > 0 ? "bg-rag-amber" : "bg-muted-foreground/30"
                    } mt-0.5 shrink-0`}
                  />
                </div>
                <div className="relative flex items-baseline gap-2">
                  <span className="exec-number text-[38px] leading-none">
                    —
                  </span>
                </div>
                <dl className="relative space-y-1.5 border-t border-border/70 pt-2.5">
                  <div className="flex items-baseline gap-2 text-[12.5px]">
                    <dt className="text-muted-foreground">Succession plan</dt>
                  </div>
                  <div className="flex items-baseline gap-2 text-[12.5px]">
                    <dt className="text-muted-foreground">Basis</dt>
                  </div>
                </dl>
              </div>

              {/* 4. Critical Roles Without a Successor */}
              <div
                onClick={() => setActiveTab("04")}
                className={`group exec-panel exec-kpi ${
                  dbWithoutSuccessor !== null && dbCriticalRoles !== null && dbCriticalRoles > 0
                    ? "exec-kpi-emphasis border-rag-red/40"
                    : ""
                } relative flex cursor-pointer flex-col justify-between gap-4 overflow-hidden pl-5 pr-4 py-4 transition-all duration-200 hover:-translate-y-1 hover:border-border-strong hover:shadow-lift`}
              >
                <span
                  className={`absolute inset-y-0 left-0 w-[3px] ${
                    dbWithoutSuccessor !== null && dbCriticalRoles !== null && dbCriticalRoles > 0
                      ? "bg-rag-red"
                      : "bg-border"
                  } transition-all duration-200 group-hover:w-[5px]`}
                />
                {dbWithoutSuccessor !== null && dbCriticalRoles !== null && dbCriticalRoles > 0 && (
                  <span className="pointer-events-none absolute -right-10 -top-12 size-32 rounded-full bg-rag-red opacity-[0.10] blur-2xl transition-opacity duration-200 group-hover:opacity-[0.18]" />
                )}
                <div className="relative flex items-start justify-between gap-2">
                  <span className="exec-label leading-snug">Critical Roles Without a Successor</span>
                  <span
                    className={`size-2.5 rounded-full ${
                      dbWithoutSuccessor !== null && dbCriticalRoles !== null && dbCriticalRoles > 0
                        ? "bg-rag-red"
                        : "bg-muted-foreground/30"
                    } mt-0.5 shrink-0`}
                  />
                </div>
                <div className="relative flex items-baseline gap-2">
                  <span className="exec-number text-[38px] leading-none text-foreground">
                    —
                  </span>
                </div>
                <dl className="relative space-y-1.5 border-t border-border/70 pt-2.5">
                  <div className="flex items-baseline gap-2 text-[12.5px]">
                    <dt className="text-muted-foreground">Ready-now cover</dt>
                  </div>
                  <div className="flex items-baseline gap-2 text-[12.5px]">
                    <dt className="text-muted-foreground">Successor named</dt>
                  </div>
                </dl>
              </div>

              {/* 5. Assessment Coverage */}
              <div
                onClick={() => setActiveTab("03")}
                className="group exec-panel exec-kpi relative flex cursor-pointer flex-col justify-between gap-4 overflow-hidden pl-5 pr-4 py-4 transition-all duration-200 hover:-translate-y-1 hover:border-border-strong hover:shadow-lift"
              >
                <span className="absolute inset-y-0 left-0 w-[3px] bg-rag-amber transition-all duration-200 group-hover:w-[5px]" />
                <span className="pointer-events-none absolute -right-10 -top-12 size-32 rounded-full bg-rag-amber opacity-[0.10] blur-2xl transition-opacity duration-200 group-hover:opacity-[0.18]" />
                <div className="relative flex items-start justify-between gap-2">
                  <span className="exec-label leading-snug">Assessment Coverage</span>
                  <span className="size-2.5 rounded-full bg-rag-amber mt-0.5 shrink-0" />
                </div>
                <div className="relative flex items-baseline gap-2">
                  <span className="exec-number text-[38px] leading-none">
                    {completedAssessments} of {currentAssessed}
                  </span>
                </div>
                <dl className="relative space-y-1.5 border-t border-border/70 pt-2.5">
                  <div className="flex items-baseline gap-2 text-[12.5px]">
                    <dt className="text-muted-foreground">Manager assessments pending</dt>
                    <span className="min-w-3 flex-1 border-b border-dotted border-border" />
                    <dd className="font-semibold tabular-nums">{pendingCount}</dd>
                  </div>
                  <div className="flex items-baseline gap-2 text-[12.5px]">
                    <dt className="text-muted-foreground">Roles affected</dt>
                    <span className="min-w-3 flex-1 border-b border-dotted border-border" />
                    <dd className="font-semibold text-foreground">{affectedRoles}</dd>
                  </div>
                </dl>
              </div>
            </div>

            {/* Outcomes & Actions Section */}
            <section className="exec-panel overflow-hidden">
              <header className="exec-panel-header relative flex flex-wrap items-start justify-between gap-3 border-b border-border px-5 py-4">
                <span aria-hidden="true" className="exec-hairline absolute left-0 top-0 h-[2px] w-24" />
                <div>
                  <h2 className="text-[15.5px] font-semibold tracking-[-0.01em]">
                    Outcomes and the actions they call for
                  </h2>
                  <p className="mt-0.5 text-[13px] text-muted-foreground">
                    Where the assessment leaves the organisation, and what is waiting for a decision.
                  </p>
                </div>
              </header>

              <div className="space-y-3 px-5 py-5 text-[13.5px] leading-relaxed">
                <p>
                  {currentAssessed} people were ASK-assessed across {plant === "COMBINED" ? "both plants" : plantLabel}. {completedAssessments} assessments are complete and {pendingCount} manager assessment{pendingCount > 1 ? "s remain" : " remains"} outstanding ({affectedRoles}). {(dbCriticalRoles !== null ? dbCriticalRoles : criticalRolesCount) > 0 ? `Of the succession plan, ${dbCriticalRoles !== null ? dbCriticalRoles : criticalRolesCount} roles are designated critical: ${dbReadyNowCover !== null ? dbReadyNowCover : readyNowRoles} ${(dbReadyNowCover !== null ? dbReadyNowCover : readyNowRoles) === 1 ? "has" : "have"} a genuine ready-now successor and ${dbWithoutSuccessor !== null ? dbWithoutSuccessor : noSuccessorRoles} have no successor named at all.` : "No critical roles or succession slates are currently defined in the database."}
                </p>
              </div>

              {/* Chairman */}
              <div className="relative flex gap-3 border-t border-border bg-secondary/60 px-5 py-4">
                <span aria-hidden="true" className="absolute inset-y-0 left-0 w-[3px] bg-brand/70" />
                <svg className="mt-0.5 size-4 shrink-0 text-brand" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M11.017 2.814a1 1 0 0 1 1.966 0l1.051 5.558a2 2 0 0 0 1.594 1.594l5.558 1.051a1 1 0 0 1 0 1.966l-5.558 1.051a2 2 0 0 0-1.594 1.594l-1.051 5.558a1 1 0 0 1-1.966 0l-1.051-5.558a2 2 0 0 0-1.594-1.594l-5.558-1.051a1 1 0 0 1 0-1.966l5.558-1.051a2 2 0 0 0 1.594-1.594zM20 2v4M22 4h-4" />
                  <circle cx="4" cy="20" r="2" />
                </svg>
                <div className="space-y-1">
                  <p className="exec-label">Insight</p>
                  <p className="text-[13.5px] leading-relaxed text-foreground">
                    {criticalRolesCount > 0
                      ? `Capability is measurable and improving, but role cover is the exposure: across ${criticalRolesCount} critical roles, continuity must be safeguarded with designated succession depth.`
                      : "Workforce assessment data is recorded in the database, but critical leadership roles have not yet been defined. Defining critical roles will establish continuity cover and risk visibility."}
                  </p>
                </div>
              </div>
            </section>
          </div>
        ) : activeTab === "02" ? (
          /* ── MODULE 02: Capability & ASK ── */
          <div className="space-y-6">
            <div className="relative flex flex-wrap items-end justify-between gap-4 pt-4">
              <span aria-hidden="true" className="exec-hairline absolute left-0 top-0 h-[3px] w-28 rounded-full" />
              <div>
                <p className="exec-label">Module 02 · Taratec</p>
                <h1 className="mt-1 text-[30px] font-semibold leading-[1.1] tracking-[-0.02em]">Capability &amp; ASK</h1>
                <p className="exec-serif mt-2 text-[17px] italic leading-relaxed text-muted-foreground">
                  “Do we have the capabilities required by the future organisation?”
                </p>
              </div>
            </div>

            {/* Info Banner */}
            <div className="exec-panel flex items-start gap-2.5 px-4 py-3 text-[13px] leading-relaxed text-muted-foreground">
              <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="lucide lucide-info mt-0.5 size-4 shrink-0 text-brand" aria-hidden="true">
                <circle cx="12" cy="12" r="10" />
                <path d="M12 16v-4" />
                <path d="M12 8h.01" />
              </svg>
              <span>ASK = Attitude / Success Behaviours + Skills + Knowledge. Two dimensions are assessed: Success Behaviours and Functional Skills. There is no separate Knowledge score.</span>
            </div>

            {/* 4 KPI Cards */}
            <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
              <div className="exec-panel exec-kpi relative flex flex-col justify-between gap-4 overflow-hidden pl-5 pr-4 py-4">
                <span className="absolute inset-y-0 left-0 w-[3px] bg-rag-green" />
                <div className="relative flex items-start justify-between gap-2">
                  <span className="exec-label leading-snug">Roles Identified</span>
                  <span className="size-2.5 rounded-full bg-rag-green mt-0.5" />
                </div>
                <div className="exec-number text-[38px] leading-none">
                  {displayRolesCount}
                </div>
                <dl className="space-y-1.5 border-t border-border/70 pt-2.5">
                  <div className="flex items-baseline gap-2 text-[12.5px]">
                    <dt className="shrink-0 text-muted-foreground">Source</dt>
                    <span className="min-w-3 flex-1 border-b border-dotted border-border" />
                    <dd className="shrink-0 font-semibold tabular-nums">Role register</dd>
                  </div>
                  <div className="flex items-baseline gap-2 text-[12.5px]">
                    <dt className="shrink-0 text-muted-foreground">Assessed population</dt>
                    <span className="min-w-3 flex-1 border-b border-dotted border-border" />
                    <dd className="shrink-0 font-semibold tabular-nums">
                      {displayAssessedPop} people
                    </dd>
                  </div>
                </dl>
              </div>

              <div className="exec-panel exec-kpi relative flex flex-col justify-between gap-4 overflow-hidden pl-5 pr-4 py-4">
                <span className="absolute inset-y-0 left-0 w-[3px] bg-rag-green" />
                <div className="relative flex items-start justify-between gap-2">
                  <span className="exec-label leading-snug">Functional Skills</span>
                  <span className="size-2.5 rounded-full bg-rag-green mt-0.5" />
                </div>
                <div className="exec-number text-[38px] leading-none">{displaySkillsCount}</div>
                <dl className="space-y-1.5 border-t border-border/70 pt-2.5">
                  <div className="flex items-baseline gap-2 text-[12.5px]">
                    <dt className="shrink-0 text-muted-foreground">Functions</dt>
                    <span className="min-w-3 flex-1 border-b border-dotted border-border" />
                    <dd className="shrink-0 font-semibold tabular-nums">{displayFunctionsCount}</dd>
                  </div>
                  <div className="flex items-baseline gap-2 text-[12.5px]">
                    <dt className="shrink-0 text-muted-foreground">Departments</dt>
                    <span className="min-w-3 flex-1 border-b border-dotted border-border" />
                    <dd className="shrink-0 font-semibold tabular-nums">{displayDepartmentsCount}</dd>
                  </div>
                </dl>
              </div>

              <div className="exec-panel exec-kpi relative flex flex-col justify-between gap-4 overflow-hidden pl-5 pr-4 py-4">
                <span className="absolute inset-y-0 left-0 w-[3px] bg-rag-green" />
                <div className="relative flex items-start justify-between gap-2">
                  <span className="exec-label leading-snug">Success Behaviours</span>
                  <span className="size-2.5 rounded-full bg-rag-green mt-0.5" />
                </div>
                <div className="exec-number text-[38px] leading-none">{displayBehavioursCount}</div>
                <dl className="space-y-1.5 border-t border-border/70 pt-2.5">
                  <div className="flex items-baseline gap-2 text-[12.5px]">
                    <dt className="shrink-0 text-muted-foreground">Applies to</dt>
                    <span className="min-w-3 flex-1 border-b border-dotted border-border" />
                    <dd className="shrink-0 font-semibold tabular-nums">Every assessed role</dd>
                  </div>
                  <div className="flex items-baseline gap-2 text-[12.5px]">
                    <dt className="shrink-0 text-muted-foreground">Dimension</dt>
                    <span className="min-w-3 flex-1 border-b border-dotted border-border" />
                    <dd className="shrink-0 font-semibold tabular-nums">Attitude / behaviour</dd>
                  </div>
                </dl>
              </div>

              <div
                onClick={() => setActiveTab("03")}
                className="exec-panel exec-kpi relative flex cursor-pointer flex-col justify-between gap-4 overflow-hidden pl-5 pr-4 py-4"
              >
                <span className="absolute inset-y-0 left-0 w-[3px] bg-rag-green" />
                <div className="relative flex items-start justify-between gap-2">
                  <span className="exec-label leading-snug">ASK Framework Completed</span>
                  <span className="size-2.5 rounded-full bg-rag-green mt-0.5" />
                </div>
                <div className="exec-number text-[38px] leading-none">
                  {displayAskPercent}%
                </div>
                <dl className="space-y-1.5 border-t border-border/70 pt-2.5">
                  <div className="flex items-baseline gap-2 text-[12.5px]">
                    <dt className="shrink-0 text-muted-foreground">People assessed</dt>
                    <span className="min-w-3 flex-1 border-b border-dotted border-border" />
                    <dd className="shrink-0 font-semibold tabular-nums">
                      {displayAssessedPop}
                    </dd>
                  </div>
                  <div className="flex items-baseline gap-2 text-[12.5px]">
                    <dt className="shrink-0 text-muted-foreground">Total people</dt>
                    <span className="min-w-3 flex-1 border-b border-dotted border-border" />
                    <dd className="shrink-0 font-semibold tabular-nums">
                      {displayTotalManpower}
                    </dd>
                  </div>
                  {plant === "COMBINED" ? (
                    <>
                      <div className="flex items-baseline gap-2 text-[12.5px]">
                        <dt className="shrink-0 text-muted-foreground">Dial 1</dt>
                        <span className="min-w-3 flex-1 border-b border-dotted border-border" />
                        <dd className="shrink-0 font-semibold tabular-nums">
                          {dbDial1AskCompletionPct ?? dial1AskPercent}% ({dbDial1Assessed ?? dial1Assessed}/{dial1Manpower})
                        </dd>
                      </div>
                      <div className="flex items-baseline gap-2 text-[12.5px]">
                        <dt className="shrink-0 text-muted-foreground">Dial 2</dt>
                        <span className="min-w-3 flex-1 border-b border-dotted border-border" />
                        <dd className="shrink-0 font-semibold tabular-nums">
                          {dbDial2AskCompletionPct ?? dial2AskPercent}% ({dbDial2Assessed ?? dial2Assessed}/{dial2Manpower})
                        </dd>
                      </div>
                    </>
                  ) : (
                    <div className="flex items-baseline gap-2 text-[12.5px]">
                      <dt className="shrink-0 text-muted-foreground">Combined (148)</dt>
                      <span className="min-w-3 flex-1 border-b border-dotted border-border" />
                      <dd className="shrink-0 font-semibold tabular-nums">
                        {combinedAskPercent}% ({combinedAssessed}/{combinedManpower})
                      </dd>
                    </div>
                  )}
                </dl>
              </div>
            </div>

            {/* Success Behaviours Panel */}
            <section className="exec-panel overflow-hidden">
              <header className="exec-panel-header relative flex flex-wrap items-start justify-between gap-3 border-b border-border px-5 py-4">
                <span aria-hidden="true" className="exec-hairline absolute left-0 top-0 h-[2px] w-24" />
                <div>
                  <h2 className="flex flex-wrap items-center gap-2 text-[15.5px] font-semibold tracking-[-0.01em]">Success behaviours</h2>
                  <p className="mt-0.5 text-[13px] text-muted-foreground">
                    {displayBehavioursCount} behaviours assessed for every person in the framework.
                  </p>
                </div>
              </header>
              <ul className="divide-y divide-border">
                {activeBehaviours.map((b) => (
                  <li key={b.behaviour} className="px-5 py-3.5">
                    <p className="text-[14px] font-semibold text-foreground">{b.behaviour}</p>
                    <p className="mt-1 text-[13px] leading-relaxed text-muted-foreground">{b.definition}</p>
                  </li>
                ))}
              </ul>
            </section>

            {/* Functional Skill Dictionary */}
            <section className="exec-panel overflow-hidden">
              <header className="exec-panel-header relative flex flex-wrap items-start justify-between gap-3 border-b border-border px-5 py-4">
                <span aria-hidden="true" className="exec-hairline absolute left-0 top-0 h-[2px] w-24" />
                <div>
                  <h2 className="flex flex-wrap items-center gap-2 text-[15.5px] font-semibold tracking-[-0.01em]">Functional skill dictionary</h2>
                  <p className="mt-0.5 text-[13px] text-muted-foreground">
                    {activeSkills.length} skills across {displayFunctionsCount} functions and {displayDepartmentsCount} departments.
                  </p>
                </div>
                <input
                  type="text"
                  value={skillSearch}
                  onChange={(e) => setSkillSearch(e.target.value)}
                  placeholder="Search skill, function or department"
                  className="h-8 w-[280px] rounded-md border border-input bg-transparent px-3 text-[12.5px] placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
                />
              </header>
              <div className="max-h-[520px] overflow-y-auto">
                <table className="w-full text-[13px]">
                  <thead className="sticky top-0 bg-secondary">
                    <tr>
                      <th className="exec-label px-4 py-2.5 text-left">Skill</th>
                      <th className="exec-label px-4 py-2.5 text-left">Function</th>
                      <th className="exec-label px-4 py-2.5 text-left">Department</th>
                      <th className="exec-label px-4 py-2.5 text-left">Definition</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border">
                    {activeSkills
                      .filter((s) => {
                        const q = skillSearch.trim().toLowerCase();
                        if (!q) return true;
                        return (
                          s.skill_name.toLowerCase().includes(q) ||
                          (s.function ?? "").toLowerCase().includes(q) ||
                          (s.department ?? "").toLowerCase().includes(q)
                        );
                      })
                      .map((s) => (
                        <tr key={s.skill_code} className="hover:bg-secondary/40">
                          <td className="px-4 py-2.5 font-medium text-foreground">{s.skill_name}</td>
                          <td className="px-4 py-2.5 text-muted-foreground">{s.function ?? "—"}</td>
                          <td className="px-4 py-2.5 text-muted-foreground">{s.department ?? "—"}</td>
                          <td className="px-4 py-2.5 text-[12.5px] text-muted-foreground">{s.definition ?? "—"}</td>
                        </tr>
                      ))}
                  </tbody>
                </table>
              </div>
            </section>

            {/* Role Register */}
            <section className="exec-panel overflow-hidden">
              <header className="exec-panel-header relative flex flex-wrap items-start justify-between gap-3 border-b border-border px-5 py-4">
                <span aria-hidden="true" className="exec-hairline absolute left-0 top-0 h-[2px] w-24" />
                <div>
                  <h2 className="flex flex-wrap items-center gap-2 text-[15.5px] font-semibold tracking-[-0.01em]">Role register</h2>
                  <p className="mt-0.5 text-[13px] text-muted-foreground">
                    {displayRolesCount} roles identified in the framework. Designations held by the assessed population:
                  </p>
                </div>
              </header>
              <div className="grid gap-x-6 gap-y-1 px-5 py-4 sm:grid-cols-2 lg:grid-cols-3">
                {roleDesignations.map((item) => (
                  <div key={item.designation} className="flex items-baseline gap-2 text-[13px]">
                    <span className="shrink-0">{item.designation}</span>
                    <span aria-hidden="true" className="min-w-3 flex-1 border-b border-dotted border-border" />
                    <span className="shrink-0 font-semibold tabular-nums">{item.count}</span>
                  </div>
                ))}
              </div>
            </section>
          </div>
        ) : activeTab === "03" ? (
          /* ── MODULE 03: Assessment & Readiness ── */
          <div className="space-y-6">
            <div className="relative flex flex-wrap items-end justify-between gap-4 pt-4">
              <span aria-hidden="true" className="exec-hairline absolute left-0 top-0 h-[3px] w-28 rounded-full" />
              <div>
                <p className="exec-label">Module 03 · Taratec</p>
                <h1 className="mt-1 text-[30px] font-semibold leading-[1.1] tracking-[-0.02em]">Assessment &amp; Readiness</h1>
                <p className="exec-serif mt-2 text-[17px] italic leading-relaxed text-muted-foreground">
                  “Where are we strong, where are we exposed, and what must be fixed first?”
                </p>
              </div>
            </div>

            {/* 4 KPI Cards */}
            <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
              <div
                onClick={() => setActiveTab("people")}
                className="exec-panel exec-kpi relative flex cursor-pointer flex-col justify-between gap-4 overflow-hidden pl-5 pr-4 py-4"
              >
                <span className="absolute inset-y-0 left-0 w-[3px] bg-rag-green" />
                <div className="relative flex items-start justify-between gap-2">
                  <span className="exec-label">People Assessed</span>
                  <span className="size-2.5 rounded-full bg-rag-green mt-0.5" />
                </div>
                <div className="exec-number text-[38px] leading-none">
                  {selectedFunction === "All Functions" && selectedLevel === "All Levels"
                    ? (dbPeopleAssessed ?? currentAssessed)
                    : currentAssessed}
                </div>
                <dl className="space-y-1.5 border-t border-border/70 pt-2.5">
                  <div className="flex items-baseline gap-2 text-[12.5px]">
                    <dt className="text-muted-foreground">Dial 1</dt>
                    <span className="min-w-3 flex-1 border-b border-dotted border-border" />
                    <dd className="font-semibold tabular-nums">
                      {selectedFunction === "All Functions" && selectedLevel === "All Levels"
                        ? (dbDial1Assessed ?? dial1Assessed)
                        : dial1Assessed}
                    </dd>
                  </div>
                  <div className="flex items-baseline gap-2 text-[12.5px]">
                    <dt className="text-muted-foreground">Dial 2</dt>
                    <span className="min-w-3 flex-1 border-b border-dotted border-border" />
                    <dd className="font-semibold tabular-nums">
                      {selectedFunction === "All Functions" && selectedLevel === "All Levels"
                        ? (dbDial2Assessed ?? dial2Assessed)
                        : dial2Assessed}
                    </dd>
                  </div>
                </dl>
              </div>

              <div className="exec-panel exec-kpi relative flex flex-col justify-between gap-4 overflow-hidden pl-5 pr-4 py-4">
                <span className="absolute inset-y-0 left-0 w-[3px] bg-rag-amber" />
                <div className="relative flex items-start justify-between gap-2">
                  <span className="exec-label">Capability Gaps</span>
                  <span className="size-2.5 rounded-full bg-rag-amber mt-0.5" />
                </div>
                <div className="exec-number text-[38px] leading-none">
                  {selectedFunction === "All Functions" && selectedLevel === "All Levels"
                    ? (dbCapabilityGaps ?? filteredGaps.length)
                    : filteredGaps.length}
                </div>
                <dl className="space-y-1.5 border-t border-border/70 pt-2.5">
                  <div className="flex items-baseline gap-2 text-[12.5px]">
                    <dt className="text-muted-foreground">Dial 1</dt>
                    <span className="min-w-3 flex-1 border-b border-dotted border-border" />
                    <dd className="font-semibold tabular-nums">
                      {selectedFunction === "All Functions" && selectedLevel === "All Levels"
                        ? ((dbCapabilityGaps ?? filteredGaps.length) > 0 ? (dbDial1Gaps ?? dial1Gaps) : "—")
                        : (filteredGaps.length > 0 ? dial1Gaps : "—")}
                    </dd>
                  </div>
                  <div className="flex items-baseline gap-2 text-[12.5px]">
                    <dt className="text-muted-foreground">Dial 2</dt>
                    <span className="min-w-3 flex-1 border-b border-dotted border-border" />
                    <dd className="font-semibold tabular-nums">
                      {selectedFunction === "All Functions" && selectedLevel === "All Levels"
                        ? ((dbCapabilityGaps ?? filteredGaps.length) > 0 ? (dbDial2Gaps ?? dial2Gaps) : "—")
                        : (filteredGaps.length > 0 ? dial2Gaps : "—")}
                    </dd>
                  </div>
                </dl>
              </div>

              <div
                onClick={() => setActiveTab("people")}
                className="exec-panel exec-kpi relative flex cursor-pointer flex-col justify-between gap-4 overflow-hidden pl-5 pr-4 py-4"
              >
                <span className="absolute inset-y-0 left-0 w-[3px] bg-rag-amber" />
                <div className="relative flex items-start justify-between gap-2">
                  <span className="exec-label">People with a Gap</span>
                  <span className="size-2.5 rounded-full bg-rag-amber mt-0.5" />
                </div>
                <div className="exec-number text-[38px] leading-none">
                  {selectedFunction === "All Functions" && selectedLevel === "All Levels" && dbPeopleWithGaps !== null
                    ? dbPeopleWithGaps
                    : filteredEmployees.filter((e) => (gapsByEmp[e.emp_code] ?? []).some((g) => g.is_gap === "Yes")).length}{" "}
                  <span className="text-[20px] font-normal text-muted-foreground">
                    of {selectedFunction === "All Functions" && selectedLevel === "All Levels" ? (dbPeopleAssessed ?? currentAssessed) : currentAssessed}
                  </span>
                </div>
                <dl className="space-y-1.5 border-t border-border/70 pt-2.5">
                  <div className="flex items-baseline gap-2 text-[12.5px]">
                    <dt className="text-muted-foreground">No gap identified</dt>
                    <span className="min-w-3 flex-1 border-b border-dotted border-border" />
                    <dd className="font-semibold tabular-nums">
                      {Math.max(
                        0,
                        (selectedFunction === "All Functions" && selectedLevel === "All Levels" ? (dbPeopleAssessed ?? currentAssessed) : currentAssessed) -
                          (selectedFunction === "All Functions" && selectedLevel === "All Levels" && dbPeopleWithGaps !== null
                            ? dbPeopleWithGaps
                            : filteredEmployees.filter((e) => (gapsByEmp[e.emp_code] ?? []).some((g) => g.is_gap === "Yes")).length)
                      )}
                    </dd>
                  </div>
                  <div className="flex items-baseline gap-2 text-[12.5px]">
                    <dt className="text-muted-foreground">Basis</dt>
                    <span className="min-w-3 flex-1 border-b border-dotted border-border" />
                    <dd className="font-semibold text-foreground">Database records</dd>
                  </div>
                </dl>
              </div>

              <div className="exec-panel exec-kpi exec-kpi-emphasis relative flex flex-col justify-between gap-4 overflow-hidden border-rag-red/40 pl-5 pr-4 py-4">
                <span className="absolute inset-y-0 left-0 w-[3px] bg-rag-red" />
                <div className="relative flex items-start justify-between gap-2">
                  <span className="exec-label">Assessments Pending</span>
                  <span className="size-2.5 rounded-full bg-rag-red mt-0.5" />
                </div>
                <div className="exec-number text-[38px] leading-none text-rag-red">
                  {pendingCount} {pendingCount === 1 ? "person" : "people"}
                </div>
                <dl className="space-y-1.5 border-t border-border/70 pt-2.5">
                  {filteredPendingEmployees.length > 0 ? (
                    filteredPendingEmployees.map((emp) => (
                      <div key={emp.emp_code} className="flex items-baseline gap-1.5 text-[11.5px]">
                        <dt className="text-muted-foreground whitespace-nowrap">{emp.name}</dt>
                        <span className="min-w-2 flex-1 border-b border-dotted border-border" />
                        <dd className="font-semibold whitespace-nowrap">
                          {emp.designation || emp.role} ({emp.division.includes("1") ? "Dial 1" : "Dial 2"})
                        </dd>
                      </div>
                    ))
                  ) : (
                    <div className="flex items-baseline gap-2 text-[12.5px]">
                      <dt className="text-muted-foreground">None</dt>
                      <span className="min-w-3 flex-1 border-b border-dotted border-border" />
                      <dd className="font-semibold text-muted-foreground">No pending assessments</dd>
                    </div>
                  )}
                </dl>
              </div>
            </div>

            {/* 2-column: Gaps by Grade Band & Gaps by Function */}
            <div className="grid gap-4 lg:grid-cols-2">
              {/* Gaps by Grade Band */}
              <section className="exec-panel overflow-hidden">
                <header className="exec-panel-header border-b border-border px-5 py-4">
                  <h2 className="text-[15.5px] font-semibold">Gaps by grade band</h2>
                  <p className="mt-0.5 text-[13px] text-muted-foreground">
                    People with a gap out of people assessed. Select a band to see the individuals.
                  </p>
                </header>
                <table className="w-full text-[13px]">
                  <thead>
                    <tr className="bg-secondary/60">
                      <th className="exec-label px-4 py-2.5 text-left">Band</th>
                      <th className="exec-label px-4 py-2.5 text-right">With a gap</th>
                      <th className="exec-label px-4 py-2.5 text-right">Assessed</th>
                      <th className="exec-label w-[34%] px-4 py-2.5 text-left">Share</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border">
                    {gradeBandGaps.map((b) => {
                      const isFullGap = b.total > 0 && b.gapped === b.total;
                      const sharePct = b.total > 0 ? (b.gapped / b.total) * 100 : 0;
                      return (
                        <tr
                          key={b.band}
                          onClick={() => {
                            setSelectedFunctionGap(null);
                            setSelectedGradeBand(selectedGradeBand === b.band ? null : b.band);
                          }}
                          className={`cursor-pointer transition hover:bg-secondary/50 ${
                            selectedGradeBand === b.band ? "bg-secondary font-semibold" : ""
                          }`}
                        >
                          <td className="px-4 py-2.5 font-semibold text-foreground">{b.band}</td>
                          <td className="px-4 py-2.5 text-right tabular-nums text-foreground">{b.gapped}</td>
                          <td className="px-4 py-2.5 text-right tabular-nums text-muted-foreground">{b.total}</td>
                          <td className="px-4 py-3">
                            <div className="h-1.5 w-full overflow-hidden rounded-full bg-[#f0f3f6]">
                              <div
                                className="h-full rounded-full transition-all duration-300"
                                style={{
                                  width: `${sharePct}%`,
                                  backgroundColor: isFullGap ? "#a96b1e" : "#147164",
                                }}
                              />
                            </div>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </section>

              {/* Gaps by Function */}
              <section className="exec-panel overflow-hidden">
                <header className="exec-panel-header border-b border-border px-5 py-4">
                  <h2 className="text-[15.5px] font-semibold">Gaps by function</h2>
                  <p className="mt-0.5 text-[13px] text-muted-foreground">
                    {totalGapsCount} gaps across {functionGaps.length} functions. Select a function to see the individuals.
                  </p>
                </header>
                <div className="max-h-[360px] overflow-y-auto">
                  <table className="w-full text-[13px]">
                    <tbody className="divide-y divide-border">
                      {functionGaps.map(([fn, count]) => (
                        <tr
                          key={fn}
                          onClick={() => {
                            setSelectedGradeBand(null);
                            setSelectedFunctionGap(selectedFunctionGap === fn ? null : fn);
                          }}
                          className={`cursor-pointer transition hover:bg-secondary/50 ${
                            selectedFunctionGap === fn ? "bg-secondary font-semibold" : ""
                          }`}
                        >
                          <td className="px-4 py-2.5 font-medium text-foreground">{fn}</td>
                          <td className="w-[45%] px-4 py-3">
                            <div className="h-1.5 w-full overflow-hidden rounded-full bg-[#f0f3f6]">
                              <div
                                className="h-full rounded-full transition-all duration-300"
                                style={{
                                  width: `${maxFunctionGaps > 0 ? (count / maxFunctionGaps) * 100 : 0}%`,
                                  backgroundColor: "#a96b1e",
                                }}
                              />
                            </div>
                          </td>
                          <td className="px-4 py-2.5 text-right font-semibold tabular-nums text-foreground">
                            {count}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </section>
            </div>

            {/* Drilldown People Table */}
            {drilldownPeople.length > 0 && (
              <section className="exec-panel overflow-hidden">
                <header className="exec-panel-header border-b border-border px-5 py-4">
                  <h2 className="text-[15.5px] font-semibold">
                    {selectedGradeBand ? `Grade band ${selectedGradeBand}` : `${selectedFunctionGap}`}
                  </h2>
                  <p className="mt-0.5 text-[13px] text-muted-foreground">
                    Select a person to open their details review and training needs.
                  </p>
                </header>
                <div className="overflow-x-auto">
                  <table className="w-full table-fixed min-w-[760px] text-[13px] border-collapse">
                    <colgroup>
                      <col style={{ width: "24%" }} />
                      <col style={{ width: "20%" }} />
                      <col style={{ width: "18%" }} />
                      <col style={{ width: "14%" }} />
                      <col style={{ width: "10%" }} />
                      <col style={{ width: "14%" }} />
                    </colgroup>
                    <thead>
                      <tr className="bg-secondary/60">
                        <th className="exec-label px-4 py-2.5 text-left">Name</th>
                        <th className="exec-label px-4 py-2.5 text-left">Designation</th>
                        <th className="exec-label px-4 py-2.5 text-left">Function</th>
                        <th className="exec-label px-4 py-2.5 text-left">Division</th>
                        <th className="exec-label px-4 py-2.5 text-center">Gaps</th>
                        <th className="exec-label px-4 py-2.5 text-right">Action</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-border">
                      {drilldownPeople.map((emp) => (
                        <tr key={emp.emp_code} className="hover:bg-secondary/40 transition">
                          <td className="px-4 py-2.5 align-middle">
                            <button
                              onClick={() => {
                                setSelectedPersonCode(emp.emp_code);
                                setActiveTab("person");
                              }}
                              className="font-semibold text-foreground underline-offset-4 hover:text-brand hover:underline text-left block truncate"
                            >
                              {emp.name}
                            </button>
                            <span className="font-mono text-[11px] text-muted-foreground">
                              {emp.emp_code}
                            </span>
                          </td>
                          <td className="px-4 py-2.5 text-muted-foreground align-middle text-[12.5px] truncate">
                            {emp.designation ?? "—"}
                          </td>
                          <td className="px-4 py-2.5 text-muted-foreground align-middle text-[12.5px]">
                            {emp.function}
                          </td>
                          <td className="px-4 py-2.5 text-muted-foreground align-middle text-[12.5px]">
                            {emp.division}
                          </td>
                          <td className="px-4 py-2.5 text-center align-middle">
                            <span className="inline-flex items-center gap-1 rounded-full border border-rag-amber/40 bg-rag-amber-soft px-2.5 py-0.5 text-[11px] font-bold text-rag-amber">
                              {emp.gaps} Gap{emp.gaps === 1 ? "" : "s"}
                            </span>
                          </td>
                          <td className="px-4 py-2.5 text-right align-middle">
                            <button
                              onClick={() => {
                                setSelectedPersonCode(emp.emp_code);
                                setActiveTab("person");
                              }}
                              className="inline-flex items-center gap-1 rounded border border-border/80 bg-secondary/50 px-2 py-1 text-[11px] font-semibold text-muted-foreground hover:text-foreground hover:bg-secondary transition whitespace-nowrap"
                            >
                              Details Review →
                            </button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </section>
            )}

            {/* How to read these numbers */}
            <section className="exec-panel overflow-hidden">
              <header className="exec-panel-header border-b border-border px-5 py-4">
                <h2 className="text-[15.5px] font-semibold">How to read these numbers</h2>
              </header>
              <div className="space-y-3 px-5 py-4 text-[13.5px] leading-relaxed text-muted-foreground">
                <p>
                  Manager ratings were reviewed on a conservative basis (each reduced one level, gaps recomputed). Gap counts are deliberately conservative.
                </p>
              </div>
              <div className="relative flex gap-3 border-t border-border bg-[#eef6f5] dark:bg-secondary/60 px-5 py-4">
                <span aria-hidden="true" className="absolute inset-y-0 left-0 w-[3px] bg-[#147164]" />
                <svg className="mt-0.5 size-4 shrink-0 text-[#147164]" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M11.017 2.814a1 1 0 0 1 1.966 0l1.051 5.558a2 2 0 0 0 1.594 1.594l5.558 1.051a1 1 0 0 1 0 1.966l-5.558 1.051a2 2 0 0 0-1.594 1.594l-1.051 5.558a1 1 0 0 1-1.966 0l-1.051-5.558a2 2 0 0 0-1.594-1.594l-5.558-1.051a1 1 0 0 1 0-1.966l5.558-1.051a2 2 0 0 0 1.594-1.594zM20 2v4M22 4h-4" />
                  <circle cx="4" cy="20" r="2" />
                </svg>
                <div>
                  <p className="exec-label text-[#147164] font-bold">INSIGHT</p>
                  <p className="mt-1 text-[13.5px] leading-relaxed text-foreground">
                    {functionGaps.slice(0, 4).map((f) => f[0]).join(", ")} carry the bulk of the gaps. Sequencing training by those four functions addresses the majority of the identified need before anything else.
                  </p>
                </div>
              </div>
            </section>
          </div>
        ) : activeTab === "04" ? (
          /* ── MODULE 04: Critical Roles & Succession ── */
          <div className="space-y-6">
            <div className="relative flex flex-wrap items-end justify-between gap-4 pt-4">
              <span aria-hidden="true" className="exec-hairline absolute left-0 top-0 h-[3px] w-28 rounded-full" />
              <div>
                <p className="exec-label">Module 04 · Taratec</p>
                <h1 className="mt-1 text-[30px] font-semibold leading-[1.1] tracking-[-0.02em]">Critical Roles &amp; Succession</h1>
                <p className="exec-serif mt-2 text-[17px] italic leading-relaxed text-muted-foreground">
                  “If a key leader left tomorrow, are we covered?”
                </p>
              </div>
            </div>

            {/* 4 KPI Cards */}
            <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
              <div className="exec-panel exec-kpi relative flex flex-col justify-between gap-4 overflow-hidden pl-5 pr-4 py-4">
                <span className="absolute inset-y-0 left-0 w-[3px] bg-rag-amber" />
                <div className="relative flex items-start justify-between gap-2">
                  <span className="exec-label">Critical Roles</span>
                  <span className="size-2.5 rounded-full bg-rag-amber mt-0.5" />
                </div>
                <div className="exec-number text-[38px] leading-none">{criticalRolesCount > 0 ? criticalRolesCount : "—"}</div>
                <dl className="space-y-1.5 border-t border-border/70 pt-2.5">
                  <div className="flex items-baseline gap-2 text-[12.5px]">
                    <dt className="text-muted-foreground">Dial 1</dt>
                    <span className="min-w-3 flex-1 border-b border-dotted border-border" />
                    <dd className="font-semibold tabular-nums">{criticalRolesCount > 0 ? dial1Crit : "—"}</dd>
                  </div>
                  <div className="flex items-baseline gap-2 text-[12.5px]">
                    <dt className="text-muted-foreground">Dial 2</dt>
                    <span className="min-w-3 flex-1 border-b border-dotted border-border" />
                    <dd className="font-semibold tabular-nums">{criticalRolesCount > 0 ? dial2Crit : "—"}</dd>
                  </div>
                </dl>
              </div>

              <div className="exec-panel exec-kpi relative flex flex-col justify-between gap-4 overflow-hidden pl-5 pr-4 py-4">
                <span className="absolute inset-y-0 left-0 w-[3px] bg-rag-amber" />
                <div className="relative flex items-start justify-between gap-2">
                  <span className="exec-label">Successor Named</span>
                  <span className="size-2.5 rounded-full bg-rag-amber mt-0.5" />
                </div>
                <div className="exec-number text-[38px] leading-none">
                  {criticalRolesCount > 0 ? (
                    <>
                      {namedSuccessorRoles} <span className="text-[20px] font-normal text-muted-foreground">of {criticalRolesCount}</span>
                    </>
                  ) : (
                    "—"
                  )}
                </div>
                <dl className="space-y-1.5 border-t border-border/70 pt-2.5">
                  <div className="flex items-baseline gap-2 text-[12.5px]">
                    <dt className="text-muted-foreground">Share of critical roles</dt>
                    <span className="min-w-3 flex-1 border-b border-dotted border-border" />
                    <dd className="font-semibold tabular-nums">{criticalRolesCount > 0 ? `${Math.round((namedSuccessorRoles / criticalRolesCount) * 100)}%` : "—"}</dd>
                  </div>
                  <div className="flex items-baseline gap-2 text-[12.5px]">
                    <dt className="text-muted-foreground">Succession plan</dt>
                    <span className="min-w-3 flex-1 border-b border-dotted border-border" />
                    <dd className="font-semibold tabular-nums">{filteredCriticalSlates.length > 0 ? `${filteredCriticalSlates.length} roles` : "—"}</dd>
                  </div>
                </dl>
              </div>

              <div className="exec-panel exec-kpi exec-kpi-emphasis relative flex flex-col justify-between gap-4 overflow-hidden border-rag-red/40 pl-5 pr-4 py-4">
                <span className="absolute inset-y-0 left-0 w-[3px] bg-rag-red" />
                <div className="relative flex items-start justify-between gap-2">
                  <span className="exec-label">Ready-Now Cover</span>
                  <span className="size-2.5 rounded-full bg-rag-red mt-0.5" />
                </div>
                <div className="exec-number text-[38px] leading-none text-rag-red">
                  {criticalRolesCount > 0 ? (
                    <>
                      {readyNowRoles} <span className="text-[20px] font-normal text-muted-foreground">of {criticalRolesCount}</span>
                    </>
                  ) : (
                    "—"
                  )}
                </div>
                <dl className="space-y-1.5 border-t border-border/70 pt-2.5">
                  <div className="flex items-baseline gap-2 text-[12.5px]">
                    <dt className="text-muted-foreground">Ready now</dt>
                    <span className="min-w-3 flex-1 border-b border-dotted border-border" />
                    <dd className="font-semibold tabular-nums">{criticalRolesCount > 0 ? `${Math.round((readyNowRoles / criticalRolesCount) * 100)}%` : "—"}</dd>
                  </div>
                  <div className="flex items-baseline gap-2 text-[12.5px]">
                    <dt className="text-muted-foreground">Everything else</dt>
                    <span className="min-w-3 flex-1 border-b border-dotted border-border" />
                    <dd className="font-semibold">{criticalRolesCount > 0 ? "1 move or longer" : "—"}</dd>
                  </div>
                </dl>
              </div>

              <div className="exec-panel exec-kpi relative flex flex-col justify-between gap-4 overflow-hidden pl-5 pr-4 py-4">
                <span className="absolute inset-y-0 left-0 w-[3px] bg-rag-red" />
                <div className="relative flex items-start justify-between gap-2">
                  <span className="exec-label">No Successor</span>
                  <span className="size-2.5 rounded-full bg-rag-red mt-0.5" />
                </div>
                <div className="exec-number text-[38px] leading-none text-rag-red">
                  {criticalRolesCount > 0 ? (
                    <>
                      {noSuccessorRoles} <span className="text-[20px] font-normal text-muted-foreground">of {criticalRolesCount}</span>
                    </>
                  ) : (
                    "—"
                  )}
                </div>
                <dl className="space-y-1.5 border-t border-border/70 pt-2.5">
                  <div className="flex items-baseline gap-2 text-[12.5px]">
                    <dt className="text-muted-foreground">Cover route</dt>
                    <span className="min-w-3 flex-1 border-b border-dotted border-border" />
                    <dd className="font-semibold">{criticalRolesCount > 0 ? "Hiring stream" : "—"}</dd>
                  </div>
                  <div className="flex items-baseline gap-2 text-[12.5px]">
                    <dt className="text-muted-foreground">Owner</dt>
                    <span className="min-w-3 flex-1 border-b border-dotted border-border" />
                    <dd className="font-semibold text-foreground">{criticalRolesCount > 0 ? "Business Head" : "—"}</dd>
                  </div>
                </dl>
              </div>
            </div>

            {criticalRolesCount > 0 && (
              <p className="text-[13px] leading-relaxed text-muted-foreground">
                {criticalRolesCount} roles are classified critical inside succession planning. All succession ratios above use the {criticalRolesCount} critical-role base.
              </p>
            )}

            {/* Critical Role Register */}
            <section className="exec-panel overflow-hidden">
              <header className="exec-panel-header border-b border-border px-5 py-4">
                <h2 className="text-[15.5px] font-semibold">Critical role register</h2>
                <p className="mt-0.5 text-[13px] text-muted-foreground">
                  {criticalRolesCount > 0 ? `${criticalRolesCount} roles. Select a role to see its readiness levels and named successors.` : "No critical roles defined in database yet."}
                </p>
              </header>
              <div className="overflow-x-auto">
                <table className="w-full table-fixed min-w-[850px] text-[13px] border-collapse">
                  <colgroup>
                    <col style={{ width: "28%" }} />
                    <col style={{ width: "22%" }} />
                    <col style={{ width: "16%" }} />
                    <col style={{ width: "12%" }} />
                    <col style={{ width: "16%" }} />
                    <col style={{ width: "6%" }} />
                  </colgroup>
                  <thead>
                    <tr className="bg-secondary/60">
                      <th className="exec-label px-4 py-2.5 text-left">Role</th>
                      <th className="exec-label px-4 py-2.5 text-left">Incumbent</th>
                      <th className="exec-label px-4 py-2.5 text-left">Division</th>
                      <th className="exec-label px-4 py-2.5 text-left">Grade</th>
                      <th className="exec-label px-4 py-2.5 text-left">Cover</th>
                      <th className="px-4 py-2.5" />
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border">
                    {filteredCriticalRoles.length === 0 ? (
                      <tr>
                        <td colSpan={6} className="px-5 py-8 text-center text-[13px] text-muted-foreground">
                          No critical roles defined in the database. When critical roles are defined with status &apos;VALIDATED&apos;, they will appear here automatically.
                        </td>
                      </tr>
                    ) : (
                      filteredCriticalRoles.map((cr) => {
                        const slate = allCriticalSlates.find(
                          (s) => s.role_title === cr.role_title || (cr.incumbent_emp_code && s.incumbent_emp_code === cr.incumbent_emp_code)
                        );
                        const isExpanded = expandedCriticalRoleId === cr.role_id;
                        const hasReadyNow = !!slate?.ready_now;
                        const hasNamed =
                          slate &&
                          [slate.emergency_successor, slate.ready_now, slate.one_move, slate.two_move].some(
                            (v) => v && !/^review a hiring/i.test(v)
                          );
                        const coverStatus = hasReadyNow
                          ? { rag: "green", label: "Ready now" }
                          : hasNamed
                          ? { rag: "amber", label: "Successor named" }
                          : { rag: "red", label: "No successor" };

                        return (
                          <Fragment key={cr.role_id}>
                            <tr
                              onClick={() => setExpandedCriticalRoleId(isExpanded ? null : cr.role_id)}
                              className={`cursor-pointer transition hover:bg-secondary/40 ${
                                isExpanded ? "bg-secondary/60" : ""
                              }`}
                            >
                              <td className="px-4 py-3 font-medium text-foreground align-middle truncate" title={cr.role_title}>
                                {cr.role_title}
                              </td>
                              <td className="px-4 py-3 align-middle">
                                {cr.incumbent_emp_code ? (
                                  <button
                                    onClick={(e) => {
                                      e.stopPropagation();
                                      setSelectedPersonCode(cr.incumbent_emp_code!);
                                      setActiveTab("person");
                                    }}
                                    className="font-semibold text-foreground underline-offset-4 hover:text-brand hover:underline truncate max-w-full block text-left"
                                  >
                                    {cr.incumbent}
                                  </button>
                                ) : (
                                  <span className="text-muted-foreground">{cr.incumbent ?? "Vacant"}</span>
                                )}
                              </td>
                              <td className="px-4 py-3 text-muted-foreground align-middle">
                                {cr.division}
                              </td>
                              <td className="px-4 py-3 text-muted-foreground align-middle">
                                {cr.grade ?? "—"}
                              </td>
                              <td className="px-4 py-3 align-middle">
                                <span
                                  className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-[11px] font-semibold whitespace-nowrap ${
                                    coverStatus.rag === "green"
                                      ? "border-rag-green/35 bg-rag-green-soft text-rag-green"
                                      : coverStatus.rag === "amber"
                                      ? "border-rag-amber/35 bg-rag-amber-soft text-rag-amber"
                                      : "border-rag-red/35 bg-rag-red-soft text-rag-red"
                                  }`}
                                >
                                  <span
                                    className={`size-1.5 rounded-full ${
                                      coverStatus.rag === "green"
                                        ? "bg-rag-green"
                                        : coverStatus.rag === "amber"
                                        ? "bg-rag-amber"
                                        : "bg-rag-red"
                                    }`}
                                  />
                                  {coverStatus.label}
                                </span>
                              </td>
                              <td className="px-4 py-3 text-right align-middle">
                                <svg
                                  className={`size-4 text-muted-foreground transition-transform ml-auto ${
                                    isExpanded ? "rotate-180" : ""
                                  }`}
                                  viewBox="0 0 24 24"
                                  fill="none"
                                  stroke="currentColor"
                                  strokeWidth="2"
                                >
                                  <path d="m6 9 6 6 6-6" />
                                </svg>
                              </td>
                            </tr>

                            {/* Accordion Detail */}
                            {isExpanded && slate && (
                              <tr className="border-t border-border bg-secondary/40">
                                <td colSpan={6} className="p-4">
                                  <div className="space-y-3">
                                    {cr.criticality_basis && (
                                      <p className="text-[13px] leading-relaxed text-muted-foreground">
                                        <span className="exec-label">Why critical</span> · {cr.criticality_basis}
                                      </p>
                                    )}
                                    <div className="grid gap-2 sm:grid-cols-2 xl:grid-cols-4">
                                      {getReadinessLevels(slate).map((lvl) => {
                                        const matchedEmp = allEmployees.find((e) => lvl.value?.includes(e.name));
                                        const isHiring = lvl.value && /^review a hiring/i.test(lvl.value);

                                        return (
                                          <div key={lvl.level} className="exec-panel bg-card px-3.5 py-3">
                                            <p className="exec-label">{lvl.level}</p>
                                            <p className="mt-1.5 text-[13.5px] font-semibold leading-snug">
                                              {matchedEmp ? (
                                                <button
                                                  onClick={(e) => {
                                                    e.stopPropagation();
                                                    setSelectedPersonCode(matchedEmp.emp_code);
                                                    setActiveTab("person");
                                                  }}
                                                  className="text-foreground underline-offset-4 hover:text-brand hover:underline"
                                                >
                                                  {lvl.value}
                                                </button>
                                              ) : (
                                                <span
                                                  className={
                                                    !lvl.value
                                                      ? "text-muted-foreground"
                                                      : isHiring
                                                      ? "text-rag-amber"
                                                      : "text-foreground"
                                                  }
                                                >
                                                  {lvl.value ?? "To be identified"}
                                                </span>
                                              )}
                                            </p>
                                          </div>
                                        );
                                      })}
                                    </div>

                                    {slate.remarks && (
                                      <p className="text-[13px] leading-relaxed text-muted-foreground">{slate.remarks}</p>
                                    )}

                                    <button
                                      onClick={() =>
                                        openAssignModal({
                                          title: `Confirm succession cover for ${cr.role_title}`,
                                          context: `Critical role — ${cr.role_title}`,
                                        })
                                      }
                                      className="text-[12.5px] font-semibold text-brand underline-offset-4 hover:underline"
                                    >
                                      Assign an action on this role →
                                    </button>
                                  </div>
                                </td>
                              </tr>
                            )}
                          </Fragment>
                        );
                      })
                    )}
                  </tbody>
                </table>
              </div>

              <div className="relative flex gap-3 border-t border-border bg-secondary/60 px-5 py-4">
                <span aria-hidden="true" className="absolute inset-y-0 left-0 w-[3px] bg-brand/70" />
                <svg className="mt-0.5 size-4 shrink-0 text-brand" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M11.017 2.814a1 1 0 0 1 1.966 0l1.051 5.558a2 2 0 0 0 1.594 1.594l5.558 1.051a1 1 0 0 1 0 1.966l-5.558 1.051a2 2 0 0 0-1.594 1.594l-1.051 5.558a1 1 0 0 1-1.966 0l-1.051-5.558a2 2 0 0 0-1.594-1.594l-5.558-1.051a1 1 0 0 1 0-1.966l5.558-1.051a2 2 0 0 0 1.594-1.594zM20 2v4M22 4h-4" />
                  <circle cx="4" cy="20" r="2" />
                </svg>
                <div className="space-y-1">
                  <p className="exec-label">Insight</p>
                  <p className="text-[13.5px] leading-relaxed text-foreground">
                    {criticalRolesCount > 0
                      ? `With ${readyNowRoles} ready-now successor across ${criticalRolesCount} critical roles, the plan currently protects continuity through recruitment rather than internal readiness. The ${noSuccessorRoles} roles with no successor named are the ones to close first.`
                      : "No critical roles are currently active in the database. Defining critical roles will populate readiness levels, talent pipelines, and succession coverage."}
                  </p>
                </div>
              </div>
            </section>

            {/* Non-Critical Roles in Succession Plan */}
            <section className="exec-panel overflow-hidden">
              <header className="exec-panel-header border-b border-border px-5 py-4">
                <h2 className="text-[15.5px] font-semibold">In the succession plan, not classified critical</h2>
                <p className="mt-0.5 text-[13px] text-muted-foreground">
                  {allNonCriticalSlates.length > 0 ? `${allNonCriticalSlates.length} roles in the succession plan.` : "No non-critical succession roles defined in database."}
                </p>
              </header>
              <table className="w-full text-[13px]">
                <thead>
                  <tr className="bg-secondary/60">
                    <th className="exec-label px-4 py-2.5 text-left">Incumbent</th>
                    <th className="exec-label px-4 py-2.5 text-left">Role</th>
                    <th className="exec-label px-4 py-2.5 text-left">Division</th>
                    <th className="exec-label px-4 py-2.5 text-left">Successor status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border">
                  {allNonCriticalSlates.length === 0 ? (
                    <tr>
                      <td colSpan={4} className="px-5 py-8 text-center text-[13px] text-muted-foreground">
                        No non-critical succession roles defined in the database.
                      </td>
                    </tr>
                  ) : (
                    allNonCriticalSlates.map((s) => (
                      <tr key={s.slate_id} className="hover:bg-secondary/40">
                        <td className="px-4 py-2.5 font-medium">
                          {s.incumbent_emp_code ? (
                            <button
                              onClick={() => {
                                setSelectedPersonCode(s.incumbent_emp_code!);
                                setActiveTab("person");
                              }}
                              className="font-semibold text-foreground underline-offset-4 hover:text-brand hover:underline"
                            >
                              {s.incumbent}
                            </button>
                          ) : (
                            s.incumbent ?? "—"
                          )}
                        </td>
                        <td className="px-4 py-2.5 text-muted-foreground">{s.role_title}</td>
                        <td className="px-4 py-2.5 text-muted-foreground">{s.division}</td>
                        <td className="px-4 py-2.5 text-muted-foreground">{s.successor_status ?? "—"}</td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </section>
          </div>
        ) : (
          /* ── MODULE 05: Actions & Governance ── */
          <div className="space-y-6">
            <div className="relative flex flex-wrap items-end justify-between gap-4 pt-4">
              <span aria-hidden="true" className="exec-hairline absolute left-0 top-0 h-[3px] w-28 rounded-full" />
              <div>
                <p className="exec-label">Module 05 · Taratec</p>
                <h1 className="mt-1 text-[30px] font-semibold leading-[1.1] tracking-[-0.02em]">Actions &amp; Governance</h1>
                <p className="exec-serif mt-2 text-[17px] italic leading-relaxed text-muted-foreground">
                  “What needs my decision, and can I track it?”
                </p>
              </div>
              <button
                onClick={() => openAssignModal({ context: "Actions & Governance" })}
                className="inline-flex items-center gap-1.5 rounded-md bg-brand px-3.5 py-2 text-[12.5px] font-semibold text-brand-foreground shadow hover:bg-brand/90"
              >
                <svg className="size-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                  <path d="M12 5v14M5 12h14" />
                </svg>
                <span>Assign Action</span>
              </button>
            </div>

            {/* 4 KPI Cards */}
            <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
              <div className="exec-panel exec-kpi exec-kpi-emphasis relative flex flex-col justify-between gap-4 overflow-hidden border-rag-red/40 pl-5 pr-4 py-4">
                <span className="absolute inset-y-0 left-0 w-[3px] bg-rag-red" />
                <div className="relative flex items-start justify-between gap-2">
                  <span className="exec-label">Most Urgent</span>
                  <span className="size-2.5 rounded-full bg-rag-red mt-0.5" />
                </div>
                <div className="exec-number text-[38px] leading-none text-rag-red">{criticalRolesCount > 0 ? "1 role" : "—"}</div>
                <dl className="space-y-1.5 border-t border-border/70 pt-2.5">
                  <div className="flex items-baseline gap-2 text-[12.5px]">
                    <dt className="text-muted-foreground">Role</dt>
                    <span className="min-w-3 flex-1 border-b border-dotted border-border" />
                    <dd className="font-semibold">{criticalRolesCount > 0 ? "HOD Assembly, Dial 1" : "—"}</dd>
                  </div>
                  <div className="flex items-baseline gap-2 text-[12.5px]">
                    <dt className="text-muted-foreground">Retires</dt>
                    <span className="min-w-3 flex-1 border-b border-dotted border-border" />
                    <dd className="font-semibold text-foreground">{criticalRolesCount > 0 ? "June 2026" : "—"}</dd>
                  </div>
                </dl>
              </div>

              <div className="exec-panel exec-kpi relative flex flex-col justify-between gap-4 overflow-hidden pl-5 pr-4 py-4">
                <span className="absolute inset-y-0 left-0 w-[3px] bg-rag-amber" />
                <div className="relative flex items-start justify-between gap-2">
                  <span className="exec-label">Decisions Pending</span>
                  <span className="size-2.5 rounded-full bg-rag-amber mt-0.5" />
                </div>
                <div className="exec-number text-[38px] leading-none">{pendingCount > 0 ? `${pendingCount} people` : "—"}</div>
                <dl className="space-y-1.5 border-t border-border/70 pt-2.5">
                  {pendingEmpCodes.slice(0, 2).map((code) => {
                    const emp = empMap.get(code);
                    return (
                      <div key={code} className="flex items-baseline gap-2 text-[12.5px]">
                        <dt className="text-muted-foreground">{emp?.name ?? code}</dt>
                        <span className="min-w-3 flex-1 border-b border-dotted border-border" />
                        <dd className="font-semibold">{emp?.designation ?? "Pending assessment"}</dd>
                      </div>
                    );
                  })}
                  {pendingEmpCodes.length === 0 && (
                    <div className="text-[12.5px] text-muted-foreground">No decisions pending</div>
                  )}
                </dl>
              </div>

              <div className="exec-panel exec-kpi relative flex flex-col justify-between gap-4 overflow-hidden pl-5 pr-4 py-4">
                <span className="absolute inset-y-0 left-0 w-[3px] bg-rag-red" />
                <div className="relative flex items-start justify-between gap-2">
                  <span className="exec-label">Successors To Confirm</span>
                  <span className="size-2.5 rounded-full bg-rag-red mt-0.5" />
                </div>
                <div className="exec-number text-[38px] leading-none text-rag-red">{criticalRolesCount > 0 ? noSuccessorRoles : "—"}</div>
                <dl className="space-y-1.5 border-t border-border/70 pt-2.5">
                  <div className="flex items-baseline gap-2 text-[12.5px]">
                    <dt className="text-muted-foreground">Base</dt>
                    <span className="min-w-3 flex-1 border-b border-dotted border-border" />
                    <dd className="font-semibold tabular-nums">{criticalRolesCount > 0 ? `${criticalRolesCount} critical roles` : "—"}</dd>
                  </div>
                  <div className="flex items-baseline gap-2 text-[12.5px]">
                    <dt className="text-muted-foreground">Route</dt>
                    <span className="min-w-3 flex-1 border-b border-dotted border-border" />
                    <dd className="font-semibold">{criticalRolesCount > 0 ? "Hiring stream" : "—"}</dd>
                  </div>
                </dl>
              </div>

              <div className="exec-panel exec-kpi relative flex flex-col justify-between gap-4 overflow-hidden pl-5 pr-4 py-4">
                <span className="absolute inset-y-0 left-0 w-[3px] bg-rag-green" />
                <div className="relative flex items-start justify-between gap-2">
                  <span className="exec-label">Tracked Actions</span>
                  <span className="size-2.5 rounded-full bg-rag-green mt-0.5" />
                </div>
                <div className="exec-number text-[38px] leading-none">{actions.length}</div>
                <dl className="space-y-1.5 border-t border-border/70 pt-2.5">
                  <div className="flex items-baseline gap-2 text-[12.5px]">
                    <dt className="text-muted-foreground">Open</dt>
                    <span className="min-w-3 flex-1 border-b border-dotted border-border" />
                    <dd className="font-semibold tabular-nums">
                      {actions.filter((a) => a.status !== "Completed").length}
                    </dd>
                  </div>
                  <div className="flex items-baseline gap-2 text-[12.5px]">
                    <dt className="text-muted-foreground">Completed</dt>
                    <span className="min-w-3 flex-1 border-b border-dotted border-border" />
                    <dd className="font-semibold tabular-nums">
                      {actions.filter((a) => a.status === "Completed").length}
                    </dd>
                  </div>
                </dl>
              </div>
            </div>

            {/* Most Urgent Section */}
            <section className="exec-panel overflow-hidden">
              <header className="exec-panel-header border-b border-border px-5 py-4">
                <h2 className="text-[15.5px] font-semibold">Most urgent</h2>
              </header>
              {criticalRolesCount > 0 ? (
                <div className="flex items-start gap-3 border-l-4 border-rag-red bg-rag-red-soft/60 px-5 py-4">
                  <svg className="mt-0.5 size-5 shrink-0 text-rag-red" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3M12 9v4M12 17h.01" />
                  </svg>
                  <div className="space-y-2">
                    <p className="text-[15px] font-semibold text-foreground">
                      HOD Assembly, Dial 1 (Kapoor Singh) retires June 2026 with no successor.
                    </p>
                    <p className="text-[13.5px] leading-relaxed text-muted-foreground">
                      There is no named successor at any readiness level. Emergency recruitment must be launched now to allow a handover period before retirement.
                    </p>
                    <button
                      onClick={() =>
                        openAssignModal({
                          title: "Launch emergency recruitment — HOD Assembly, Dial 1",
                          context: "Kapoor Singh retires June 2026, no successor",
                        })
                      }
                      className="text-[12.5px] font-semibold text-brand underline-offset-4 hover:underline"
                    >
                      Assign this action →
                    </button>
                  </div>
                </div>
              ) : (
                <div className="px-5 py-8 text-center text-[13px] text-muted-foreground">
                  No critical roles or retirement risks identified in the database.
                </div>
              )}
            </section>

            {/* Decisions Pending */}
            <section className="exec-panel overflow-hidden">
              <header className="exec-panel-header border-b border-border px-5 py-4">
                <h2 className="text-[15.5px] font-semibold">Decisions pending</h2>
                <p className="mt-0.5 text-[13px] text-muted-foreground">
                  Waiting on a decision or a sign-off before the register can be closed.
                </p>
              </header>
              <ul className="divide-y divide-border">
                {pendingEmpCodes.map((code) => {
                  const emp = empMap.get(code);
                  return (
                    <li key={code} className="flex flex-wrap items-center gap-3 px-5 py-3.5">
                      <span className="inline-flex items-center gap-1.5 rounded-full border border-rag-amber/35 bg-rag-amber-soft px-2.5 py-0.5 text-[11px] font-semibold text-rag-amber">
                        <span className="size-1.5 rounded-full bg-rag-amber" />
                        Manager assessment outstanding
                      </span>
                      <button
                        onClick={() => {
                          setSelectedPersonCode(code);
                          setActiveTab("person");
                        }}
                        className="text-[14px] font-semibold text-foreground underline-offset-4 hover:text-brand hover:underline"
                      >
                        {emp?.name ?? code}
                      </button>
                      <span className="text-[13px] text-muted-foreground">
                        {emp?.designation} · {emp?.function} · final classification sign-off with Mr B Sateesh
                      </span>
                      <button
                        onClick={() =>
                          openAssignModal({
                            title: `Complete manager assessment — ${emp?.name ?? code}`,
                            owner: emp?.manager_name ?? "Mr B Sateesh",
                            context: "CSM role · sign-off with Mr B Sateesh",
                          })
                        }
                        className="ml-auto text-[12.5px] font-semibold text-brand underline-offset-4 hover:underline"
                      >
                        Assign
                      </button>
                    </li>
                  );
                })}
              </ul>
            </section>

            {/* Confirm Successors for Uncovered Roles */}
            <section className="exec-panel overflow-hidden">
              <header className="exec-panel-header border-b border-border px-5 py-4">
                <h2 className="text-[15.5px] font-semibold">
                  Confirm successors for the {noSuccessorRoles} uncovered critical roles
                </h2>
                <p className="mt-0.5 text-[13px] text-muted-foreground">
                  No successor is named at any readiness level for these roles.
                </p>
              </header>
              <table className="w-full text-[13px]">
                <thead>
                  <tr className="bg-secondary/60">
                    <th className="exec-label px-4 py-2.5 text-left">Role</th>
                    <th className="exec-label px-4 py-2.5 text-left">Incumbent</th>
                    <th className="exec-label px-4 py-2.5 text-left">Division</th>
                    <th className="px-4 py-2.5" />
                  </tr>
                </thead>
                <tbody className="divide-y divide-border">
                  {allCriticalSlates
                    .filter(
                      (s) =>
                        ![s.emergency_successor, s.ready_now, s.one_move, s.two_move].some(
                          (v) => v && !/^review a hiring/i.test(v)
                        )
                    )
                    .map((slate) => (
                      <tr key={slate.slate_id} className="hover:bg-secondary/40">
                        <td className="px-4 py-2.5 font-medium text-foreground">{slate.role_title}</td>
                        <td className="px-4 py-2.5">
                          {slate.incumbent_emp_code ? (
                            <button
                              onClick={() => {
                                setSelectedPersonCode(slate.incumbent_emp_code!);
                                setActiveTab("person");
                              }}
                              className="font-semibold text-foreground underline-offset-4 hover:text-brand hover:underline"
                            >
                              {slate.incumbent}
                            </button>
                          ) : (
                            <span className="text-muted-foreground">{slate.incumbent ?? "—"}</span>
                          )}
                        </td>
                        <td className="px-4 py-2.5 text-muted-foreground">{slate.division}</td>
                        <td className="px-4 py-2.5 text-right">
                          <button
                            onClick={() =>
                              openAssignModal({
                                title: `Confirm a successor for ${slate.role_title}`,
                                context: `Uncovered critical role · ${slate.division}`,
                              })
                            }
                            className="text-[12.5px] font-semibold text-brand underline-offset-4 hover:underline"
                          >
                            Assign
                          </button>
                        </td>
                      </tr>
                    ))}
                </tbody>
              </table>
            </section>

            {/* Action Log Table */}
            <section className="exec-panel overflow-hidden">
              <header className="exec-panel-header border-b border-border px-5 py-4">
                <h2 className="text-[15.5px] font-semibold">Action log</h2>
                <p className="mt-0.5 text-[13px] text-muted-foreground">
                  Every assigned action is tracked here with an owner, a due date and a status.
                </p>
              </header>
              {actions.length === 0 ? (
                <div className="px-5 py-10 text-center text-[13.5px] text-muted-foreground">
                  <p>No actions assigned yet. Use “Assign Action” to create a tracked item.</p>
                </div>
              ) : (
                <table className="w-full text-[13px]">
                  <thead>
                    <tr className="bg-secondary/60">
                      <th className="exec-label px-4 py-2.5 text-left">Action</th>
                      <th className="exec-label px-4 py-2.5 text-left">Owner</th>
                      <th className="exec-label px-4 py-2.5 text-left">Due</th>
                      <th className="exec-label px-4 py-2.5 text-left">Context</th>
                      <th className="exec-label px-4 py-2.5 text-left">Status</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border">
                    {actions.map((act) => (
                      <tr key={act.id} className="hover:bg-secondary/40">
                        <td className="px-4 py-2.5 font-medium text-foreground">
                          {act.title}
                          {act.notes && (
                            <span className="block text-[12px] font-normal text-muted-foreground">{act.notes}</span>
                          )}
                        </td>
                        <td className="px-4 py-2.5 text-muted-foreground">{act.owner}</td>
                        <td className="px-4 py-2.5 text-muted-foreground">{act.dueDate}</td>
                        <td className="px-4 py-2.5 text-muted-foreground">{act.context}</td>
                        <td className="px-4 py-2.5">
                          <select
                            value={act.status}
                            onChange={(e) =>
                              updateActionStatus(act.id, e.target.value as "Open" | "In Progress" | "Completed")
                            }
                            className="h-7 rounded border border-border bg-card px-2 text-[12px] font-semibold text-foreground focus:border-brand focus:outline-none"
                          >
                            <option value="Open">Open</option>
                            <option value="In Progress">In Progress</option>
                            <option value="Completed">Completed</option>
                          </select>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </section>
          </div>
        )}
      </main>

      {/* ── Footer ── */}
      <footer className="mx-auto max-w-[1560px] px-5 pb-10 lg:px-8">
        <p className="border-t border-border pt-4 text-[11.5px] text-muted-foreground">
          KDDL Limited — Chairman / MD Organization &amp; Leadership Intelligence. Figures are sourced from the Taratec ASK assessment and leadership decision records; manager ratings were reviewed on a conservative basis.
        </p>
      </footer>

      {/* ── Modal: Assign Action Dialog ── */}
      {assignModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
          <div className="exec-panel w-full max-w-[520px] overflow-hidden bg-card p-6 shadow-2xl">
            <div className="flex items-start justify-between">
              <div>
                <h3 className="text-[17px] font-bold text-foreground">Assign an action</h3>
                <p className="mt-1 text-[13px] text-muted-foreground">
                  Creates a tracked item in the action log with an owner, a due date and a status.
                </p>
              </div>
              <button
                onClick={() => setAssignModalOpen(false)}
                className="text-muted-foreground hover:text-foreground"
              >
                ✕
              </button>
            </div>

            <form onSubmit={handleCreateAction} className="mt-5 space-y-4">
              <div className="space-y-1">
                <label className="exec-label text-foreground" htmlFor="act-title">
                  Action
                </label>
                <input
                  id="act-title"
                  type="text"
                  required
                  value={actionTitle}
                  onChange={(e) => setActionTitle(e.target.value)}
                  placeholder="What must happen?"
                  className="w-full rounded-md border border-border bg-card px-3 py-2 text-[13px] focus:border-brand focus:outline-none"
                />
              </div>

              <div className="grid gap-3 sm:grid-cols-2">
                <div className="space-y-1">
                  <label className="exec-label text-foreground" htmlFor="act-owner">
                    Owner
                  </label>
                  <input
                    id="act-owner"
                    type="text"
                    value={actionOwner}
                    onChange={(e) => setActionOwner(e.target.value)}
                    placeholder="Who owns it?"
                    className="w-full rounded-md border border-border bg-card px-3 py-2 text-[13px] focus:border-brand focus:outline-none"
                  />
                </div>

                <div className="space-y-1">
                  <label className="exec-label text-foreground" htmlFor="act-due">
                    Due date
                  </label>
                  <input
                    id="act-due"
                    type="date"
                    value={actionDue}
                    onChange={(e) => setActionDue(e.target.value)}
                    className="w-full rounded-md border border-border bg-card px-3 py-2 text-[13px] focus:border-brand focus:outline-none"
                  />
                </div>
              </div>

              <div className="space-y-1">
                <label className="exec-label text-foreground" htmlFor="act-notes">
                  Notes
                </label>
                <textarea
                  id="act-notes"
                  rows={3}
                  value={actionNotes}
                  onChange={(e) => setActionNotes(e.target.value)}
                  placeholder="Additional context or background"
                  className="w-full rounded-md border border-border bg-card px-3 py-2 text-[13px] focus:border-brand focus:outline-none"
                />
              </div>

              <div className="flex justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setAssignModalOpen(false)}
                  className="rounded-md border border-border px-4 py-2 text-[12.5px] font-semibold text-muted-foreground hover:bg-secondary"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="rounded-md bg-brand px-4 py-2 text-[12.5px] font-semibold text-brand-foreground hover:bg-brand/90"
                >
                  Create Action
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ── Modal: CMD Command Palette ── */}
      {cmdOpen && (
        <div
          onClick={() => setCmdOpen(false)}
          className="fixed inset-0 z-50 flex items-start justify-center bg-black/60 backdrop-blur-sm p-4 pt-20"
        >
          <div
            onClick={(e) => e.stopPropagation()}
            className="exec-panel w-full max-w-[600px] overflow-hidden bg-card shadow-2xl"
          >
            <div className="flex items-center border-b border-border px-4 py-3">
              <svg className="size-4 text-muted-foreground mr-2.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <circle cx="11" cy="11" r="8" />
                <path d="m21 21-4.3-4.3" />
              </svg>
              <input
                type="text"
                autoFocus
                value={cmdSearch}
                onChange={(e) => setCmdSearch(e.target.value)}
                placeholder="Type a command or search people, roles, functions..."
                className="w-full bg-transparent text-[14px] outline-none placeholder:text-muted-foreground"
              />
              <kbd className="rounded border border-border bg-secondary px-1.5 py-0.5 text-[10px] font-semibold text-muted-foreground">
                ESC
              </kbd>
            </div>

            <div className="max-h-[360px] overflow-y-auto p-2">
              {/* Modules Group */}
              <div className="px-3 py-1.5 exec-label text-muted-foreground">Modules</div>
              {[
                { id: "01", label: "01 Executive Review" },
                { id: "02", label: "02 Capability & ASK" },
                { id: "03", label: "03 Assessment & Readiness" },
                { id: "04", label: "04 Critical Roles & Succession" },
                { id: "05", label: "05 Actions & Governance" },
                { id: "people", label: "People Assessed Directory" },
              ]
                .filter((m) => !cmdSearch.trim() || m.label.toLowerCase().includes(cmdSearch.toLowerCase()))
                .map((m) => (
                  <button
                    key={m.id}
                    onClick={() => {
                      setActiveTab(m.id as ModuleId);
                      setSelectedPersonCode(null);
                      setCmdOpen(false);
                    }}
                    className="flex w-full items-center justify-between rounded-md px-3 py-2 text-left text-[13px] font-medium text-foreground hover:bg-secondary"
                  >
                    <span>{m.label}</span>
                    <span className="text-[11px] text-muted-foreground">Jump →</span>
                  </button>
                ))}

              {/* People Search Results */}
              {cmdSearch.trim() && (
                <>
                  <div className="mt-2 border-t border-border px-3 py-1.5 exec-label text-muted-foreground">
                    People
                  </div>
                  {allEmployees
                    .filter(
                      (e) =>
                        e.name.toLowerCase().includes(cmdSearch.toLowerCase()) ||
                        e.emp_code.toLowerCase().includes(cmdSearch.toLowerCase()) ||
                        e.function.toLowerCase().includes(cmdSearch.toLowerCase())
                    )
                    .slice(0, 5)
                    .map((emp) => (
                      <button
                        key={emp.emp_code}
                        onClick={() => {
                          setSelectedPersonCode(emp.emp_code);
                          setActiveTab("person");
                          setCmdOpen(false);
                        }}
                        className="flex w-full items-center justify-between rounded-md px-3 py-2 text-left text-[13px] text-foreground hover:bg-secondary"
                      >
                        <div>
                          <span className="font-semibold">{emp.name}</span>
                          <span className="ml-2 font-mono text-[11px] text-muted-foreground">{emp.emp_code}</span>
                          <span className="ml-2 text-[12px] text-muted-foreground">· {emp.function}</span>
                        </div>
                        <span className="text-[11px] text-brand">Details Review →</span>
                      </button>
                    ))}
                </>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
