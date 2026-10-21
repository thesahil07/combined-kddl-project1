import { FormEvent, useEffect, useState } from "react";

import { activeTenantBrand } from "./tenantBrand";
import "./signIn.css";
import { CurrentUser, Workspace } from "./workspace";

const apiUrl = "http://127.0.0.1:8000/api/v1";

export function App() {
  const [isOpen, setIsOpen] = useState(false);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [message, setMessage] = useState("");
  const [currentUser, setCurrentUser] = useState<CurrentUser | null>(null);

  async function loadCurrentUser(token: string) {
    const response = await fetch(`${apiUrl}/me`, { headers: { Authorization: `Bearer ${token}` } });
    if (!response.ok) throw new Error("Session is no longer valid.");
    setCurrentUser((await response.json()) as CurrentUser);
  }

  useEffect(() => {
    const token = sessionStorage.getItem("kddl_access_token");
    if (token) loadCurrentUser(token).catch(() => sessionStorage.removeItem("kddl_access_token"));
  }, []);

  async function signIn(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setMessage("Signing in...");
    try {
      const response = await fetch(`${apiUrl}/auth/login`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ email, password }) });
      if (!response.ok) { setMessage(response.status === 503 ? "Sign-in service is temporarily unavailable." : "Invalid credentials."); return; }
      const result = (await response.json()) as { access_token: string };
      sessionStorage.setItem("kddl_access_token", result.access_token);
      await loadCurrentUser(result.access_token);
      setIsOpen(false);
      setPassword("");
    } catch { setMessage("Unable to reach the sign-in service."); }
  }

  if (currentUser) return <Workspace user={currentUser} onSignOut={() => { sessionStorage.removeItem("kddl_access_token"); setCurrentUser(null); }} />;

  return <main className="shell">
    <nav><div className="brand"><img src={activeTenantBrand.logoUrl} alt={activeTenantBrand.tenantName} /><span>Talent Transformation</span></div><span className="nav-note">POWERED BY PLANET GANGES</span></nav>
    <section className="hero"><p className="eyebrow">KDDL TALENT TRANSFORMATION PLATFORM</p><h1>Make talent decisions<br /><em>clearer, together.</em></h1><p className="intro">A secure workspace for capability assessment, critical-role visibility, and succession planning across KDDL Dials.</p><div className="actions"><button onClick={() => { setMessage(""); setIsOpen(true); }}>Sign in to platform</button><a href="#foundation">Explore platform foundation</a></div><figure className="hero-visual"><img src="/manufacturing-talent-hero.png" alt="KDDL manufacturing professionals reviewing precision work" /><figcaption>Precision, people, and progress.</figcaption></figure></section>
    <section id="foundation" className="foundation"><div className="foundation-copy"><p className="eyebrow">FOUNDATION</p><h2>Built for a trusted talent process.</h2><p>Role-based access, tenant isolation, and auditable workflows provide the backbone for every capability decision.</p></div><div className="cards"><article><b>01</b><h3>Role clarity</h3><p>Structured role descriptions and ASK framework alignment.</p></article><article><b>02</b><h3>Capability insight</h3><p>Assessment signals made ready for meaningful conversations.</p></article><article><b>03</b><h3>Succession readiness</h3><p>Critical-role visibility for deliberate workforce planning.</p></article></div></section>
    <footer><span>KDDL Dials Talent Transformation Platform</span><span>Internal workspace / {new Date().getFullYear()}</span></footer>
    {isOpen && <div className="dialog-backdrop"><section className="dialog" role="dialog" aria-modal="true" aria-labelledby="sign-in-title"><button className="close" aria-label="Close sign in" onClick={() => setIsOpen(false)}>Close</button><p className="eyebrow">SECURE ACCESS</p><h2 id="sign-in-title">Sign in to the platform</h2><p>Use your KDDL platform credentials to continue.</p><form onSubmit={signIn}><label>Email<input type="email" value={email} onChange={(event) => setEmail(event.target.value)} required /></label><label>Password<input type="password" value={password} onChange={(event) => setPassword(event.target.value)} required /></label><button type="submit">Sign in</button></form>{message && <div className="login-message" role="status">{message}</div>}</section></div>}
  </main>;
}
