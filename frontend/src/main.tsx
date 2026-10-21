import { StrictMode } from "react";
import { createRoot } from "react-dom/client";

import { App } from "./app/App";
import { applyTenantBrand } from "./app/tenantBrand";
import "./index.css";

applyTenantBrand();
createRoot(document.getElementById("root")!).render(
  <StrictMode><App /></StrictMode>,
);
