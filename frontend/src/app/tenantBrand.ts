export type TenantBrand = {
  tenantName: string;
  logoUrl: string;
  colors?: Partial<Record<"primary" | "accent" | "aqua" | "surface", string>>;
};

// Planet Ganges brand palette is the platform default. Tenant onboarding may
// safely override only its logo and core color tokens through this object.
export const defaultBrand: Required<TenantBrand> = {
  tenantName: "Planet Ganges",
  logoUrl: "",
  colors: { primary: "#1A1F2B", accent: "#F9A23B", aqua: "#00A8A8", surface: "#F9F9F9" },
};

export const activeTenantBrand: TenantBrand = {
  tenantName: "KDDL Dials",
  logoUrl: "/kddl-logo.png",
};

export function applyTenantBrand(tenant: TenantBrand = activeTenantBrand) {
  const colors = { ...defaultBrand.colors, ...tenant.colors };
  const root = document.documentElement;
  root.style.setProperty("--brand-primary", colors.primary ?? "#1A1F2B");
  root.style.setProperty("--brand-accent", colors.accent ?? "#F9A23B");
  root.style.setProperty("--brand-aqua", colors.aqua ?? "#00A8A8");
  root.style.setProperty("--brand-surface", colors.surface ?? "#F9F9F9");
}
