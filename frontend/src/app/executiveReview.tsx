import { useEffect, useState } from "react";

import { activeTenantBrand } from "./tenantBrand";
import type { CurrentUser } from "./workspace";

const apiUrl = "http://127.0.0.1:8000/api/v1";

type Dashboard = { entity: { entity_id: number; name: string; code: string } | null; divisions: { division_id: number; name: string; code: string }[]; active_cycle: { name: string; period_start: string; period_end: string } | null; people_assessed: number; total_manpower: number; manager_assessments_pending: number; critical_roles: number; critical_roles_without_successor: number; reported_gap_items: number };

export function ExecutiveReviewWorkspace({ user, onSignOut, onClose }: { user: CurrentUser; onSignOut: () => void; onClose: () => void }) {
  const [dashboard, setDashboard] = useState<Dashboard | null>(null);
  const [divisionId, setDivisionId] = useState("");
  const [error, setError] = useState("");
  const token = sessionStorage.getItem("kddl_access_token") ?? "";
  useEffect(() => {
    const query = divisionId ? `?division_id=${divisionId}` : "";
    fetch(`${apiUrl}/executive-review/dashboard${query}`, { headers: { Authorization: `Bearer ${token}` } })
      .then((response) => response.ok ? response.json() : Promise.reject(new Error("Unable to load Executive Review.")))
      .then((data: Dashboard) => { setDashboard(data); setError(""); })
      .catch((loadError: Error) => setError(loadError.message));
  }, [divisionId, token]);
  const cycle = dashboard?.active_cycle;
  return <main className="manager-shell executive-review">
    <header className="manager-header"><div className="manager-brand"><img src={activeTenantBrand.logoUrl} alt="KDDL" /><span>Executive Review</span></div><div><span className="manager-user">{user.email}</span><button onClick={onClose}>Back to workspace</button><button onClick={onSignOut}>Sign out</button></div></header>
    <section className="executive-hero"><div><p className="eyebrow">MODULE 01 · {dashboard?.entity?.name?.toUpperCase() ?? "KDDL DIALS"}</p><h1>Executive<br /><em>Review</em></h1><p>Is the organisation ready to deliver its agenda?</p></div><label>Division<select value={divisionId} onChange={(event) => setDivisionId(event.target.value)}><option value="">{dashboard?.entity?.name ?? "Combined"}</option>{dashboard?.divisions.map((division) => <option value={division.division_id} key={division.division_id}>{division.name}</option>)}</select></label></section>
    <section className="manager-content executive-content">{cycle && <p className="cycle-line">{cycle.name} · {cycle.period_start} to {cycle.period_end}</p>}{error && <p className="form-error">{error}</p>}{!dashboard ? <p className="workspace-loading">Loading Executive Review…</p> : <><div className="metric-grid executive-metrics"><article><b>{dashboard.people_assessed}</b><span>People assessed</span></article><article><b>{dashboard.total_manpower}</b><span>Total manpower</span></article><article><b>{dashboard.critical_roles}</b><span>Critical roles</span></article><article><b>{dashboard.critical_roles_without_successor}</b><span>Critical roles without a successor</span></article></div><section className="executive-outcomes"><p className="eyebrow">OUTCOMES AND THE ACTIONS THEY CALL FOR</p><h2>Where the assessment leaves the organisation.</h2><p>{dashboard.people_assessed} employees have completed at least one current-cycle assessment. {dashboard.manager_assessments_pending} manager assessments remain pending. {dashboard.critical_roles} critical roles are validated, with {dashboard.critical_roles_without_successor} still without a named successor.</p><div><b>EXECUTIVE INSIGHT</b><p>{dashboard.reported_gap_items} capability gap items have been reported. Prioritise manager completion and successor coverage before using gap data for workforce decisions.</p></div></section></>}</section>
  </main>;
}
