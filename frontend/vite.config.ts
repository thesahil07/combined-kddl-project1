import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

const browserSecurityHeaders = {
  "Content-Security-Policy": "base-uri 'self'; object-src 'none'; frame-ancestors 'none'",
  "Permissions-Policy": "camera=(), geolocation=(), microphone=(), payment=(), usb=()",
  "Referrer-Policy": "strict-origin-when-cross-origin",
  "X-Content-Type-Options": "nosniff",
  "X-Frame-Options": "DENY",
};

export default defineConfig({
  plugins: [react()],
  server: { headers: browserSecurityHeaders },
  preview: { headers: browserSecurityHeaders },
});
