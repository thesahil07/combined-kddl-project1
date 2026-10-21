import { FormEvent, useState } from "react";

type RoleContext = {
  role_title: string | null;
  function_name: string;
  department_name: string | null;
  grade_band_code: string;
};

export type RoleDefinitionValues = Record<string, string | number | null>;

type TemplateField = { name: string; label: string; illustration: string; optional?: boolean; type?: "number" | "text" };

const fields: TemplateField[] = [
  { name: "people_count", label: "No. of people in this role", illustration: "Example: 1 incumbent in the selected division.", type: "number" },
  { name: "role_definition", label: "Role definition", illustration: "A concise statement of the role's purpose, scope, and accountable outcomes." },
  { name: "key_responsibilities", label: "Key responsibilities in the role", illustration: "For example: strategic leadership; quality assurance and control; stakeholder interface; continuous improvement; risk and compliance." },
  { name: "kpis", label: "Key performance indicators (KPI) for the role", illustration: "For example: defect rate, first-pass yield, audit outcomes, CAPA closure, customer complaint resolution." },
  { name: "education_certifications", label: "Education / degree / diploma or certifications required", illustration: "For example: relevant engineering or science degree; quality-management and audit certifications." },
  { name: "minimum_relevant_experience", label: "Minimum relevant experience required", illustration: "State the relevant functional or leadership experience range required for the role." },
  { name: "knowledge_required", label: "Knowledge required to perform the role", illustration: "For example: QMS standards, product requirements, process-excellence tools, compliance frameworks, data systems." },
  { name: "skills_required", label: "Skills required to perform the role", illustration: "For example: quality systems expertise, analysis, problem solving, leadership, stakeholder influence, change management." },
  { name: "attitudes_behaviours", label: "Attitude / behaviours required to perform the role", illustration: "For example: commitment to excellence, integrity, ownership, customer focus, collaboration, composure, learning agility." },
  { name: "equipment_process_refs", label: "Equipment or process references", illustration: "Add relevant machinery, SOP, ISO, 5S, TPM, or other process references where applicable.", optional: true },
];

export function RoleDefinitionTemplate({ role, values, isReadOnly, onSubmit, onClose }: { role: RoleContext; values: RoleDefinitionValues; isReadOnly: boolean; onSubmit: (event: FormEvent<HTMLFormElement>, action: "draft" | "submit") => void; onClose: () => void }) {
  const [missingFields, setMissingFields] = useState<string[]>([]);

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    const submitter = (event.nativeEvent as SubmitEvent).submitter as HTMLButtonElement | null;
    const action = (submitter?.value === "submit") ? "submit" : "draft";
    if (action === "submit") {
      const formData = new FormData(event.currentTarget);
      const missing = fields.filter(field => !field.optional && !String(formData.get(field.name) ?? "").trim()).map(field => field.label);
      if (missing.length) {
        event.preventDefault();
        setMissingFields(missing);
        return;
      }
    }
    setMissingFields([]);
    onSubmit(event, action);
  }

  return <div className="dialog-backdrop"><section className="role-dialog"><p className="eyebrow">ROLE DESCRIPTION TEMPLATE</p><h2>{role.role_title}</h2><p>{isReadOnly ? "This role definition has been submitted and is now read-only." : "Use the Illustration column as a guide; complete the Data Entry column for this role."}</p><div className="role-metadata"><span><b>Function</b>{role.function_name}</span><span><b>Department</b>{role.department_name ?? "Not assigned"}</span><span><b>Role</b>{role.role_title}</span><span><b>Grade</b>{role.grade_band_code}</span></div><form onSubmit={handleSubmit}>{missingFields.length > 0 && <div className="form-error" role="alert"><b>Complete all mandatory fields before submitting:</b><ul>{missingFields.map(field => <li key={field}>{field}</li>)}</ul></div>}<div className="template-head"><span>Role description section</span><span>Illustration</span><span>Data entry</span></div>{fields.map(field => <div className={`template-row ${missingFields.includes(field.label) ? "field-missing" : ""}`} key={field.name}><label>{field.label}{field.optional ? " (optional)" : ""}</label><p>{field.illustration}</p>{field.type === "number" ? <input name={field.name} type="number" min="0" defaultValue={values[field.name] ?? ""} disabled={isReadOnly} /> : <textarea name={field.name} defaultValue={String(values[field.name] ?? "")} disabled={isReadOnly} />}</div>)}<div className="template-actions"><button className="secondary" type="button" onClick={onClose}>Close</button><button className="secondary" type="submit" value="draft" formNoValidate disabled={isReadOnly}>Save draft</button><button className="primary" type="submit" value="submit" disabled={isReadOnly}>Submit</button></div></form></section></div>;
}
